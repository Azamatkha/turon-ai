"""Suhbatni Word (.docx) faylga eksport qilish — tashqi kutubxonasiz.

DOCX — ZIP ichidagi bir nechta XML fayl. Bizga kerak bo'lgani juda oddiy
(sarlavha, paragraf, qalin matn, ro'yxat, jadval), shuning uchun
python-docx kabi yangi bog'liqlik qo'shmadik (bank proksisi orqali paket
o'rnatish ham qiyin). Word lotin, kirill va rus matnini o'zi to'g'ri
ko'rsatadi — PDF'dagi kabi shrift muammosi yo'q.

Bot javoblaridagi markdown'ning asosiy qismi o'giriladi: `#` sarlavhalar,
`-`/`*`/`1.` ro'yxatlar, `**qalin**`, `[matn](havola)` va `|` jadvallar.
"""

import io
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime
from xml.sax.saxutils import escape

_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
</Types>"""

_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>"""

_DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

# Bitta shrift (Calibri) va bir nechta paragraf uslubi
_STYLES = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="{_W_NS}">
<w:docDefaults>
<w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri" w:eastAsia="Calibri"/><w:sz w:val="22"/><w:lang w:val="uz-Latn-UZ"/></w:rPr></w:rPrDefault>
<w:pPrDefault><w:pPr><w:spacing w:after="80" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault>
</w:docDefaults>
<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/></w:style>
<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:pPr><w:spacing w:after="60"/></w:pPr><w:rPr><w:b/><w:color w:val="193070"/><w:sz w:val="36"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Meta"><w:name w:val="Meta"/><w:pPr><w:spacing w:after="240"/></w:pPr><w:rPr><w:color w:val="64748B"/><w:sz w:val="18"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Speaker"><w:name w:val="Speaker"/><w:pPr><w:keepNext/><w:spacing w:before="240" w:after="60"/><w:pBdr><w:top w:val="single" w:sz="4" w:space="6" w:color="E2E8F0"/></w:pBdr></w:pPr><w:rPr><w:b/><w:color w:val="4059BE"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="Heading"><w:name w:val="Heading"/><w:pPr><w:keepNext/><w:spacing w:before="120" w:after="40"/></w:pPr><w:rPr><w:b/><w:sz w:val="24"/></w:rPr></w:style>
<w:style w:type="paragraph" w:styleId="ListItem"><w:name w:val="ListItem"/><w:pPr><w:spacing w:after="40"/><w:ind w:left="360" w:hanging="240"/></w:pPr></w:style>
</w:styles>"""


@dataclass
class ExportMessage:
    role: str  # "user" | "assistant"
    content: str
    created_at: datetime | None


_BOLD = re.compile(r"\*\*(.+?)\*\*|__(.+?)__")
_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_BULLET = re.compile(r"^\s*[-*•]\s+(.*)$")
_NUMBERED = re.compile(r"^\s*(\d+[.)])\s+(.*)$")
_TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")
# XML 1.0 da taqiqlangan boshqaruv belgilari — Word faylni ochmay qo'yadi
_BAD_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _runs(text: str, bold: bool = False) -> str:
    """Matnni w:r bo'laklariga: **qalin** qismlar alohida run bo'ladi."""
    text = _LINK.sub(lambda m: f"{m.group(1)} ({m.group(2)})", _BAD_XML.sub("", text))
    out: list[str] = []
    pos = 0
    for m in _BOLD.finditer(text):
        if m.start() > pos:
            out.append(_run(text[pos : m.start()], bold))
        out.append(_run(m.group(1) or m.group(2) or "", True))
        pos = m.end()
    if pos < len(text):
        out.append(_run(text[pos:], bold))
    return "".join(out)


def _run(text: str, bold: bool) -> str:
    if not text:
        return ""
    rpr = "<w:rPr><w:b/></w:rPr>" if bold else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>'


def _para(inner: str, style: str | None = None) -> str:
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return f"<w:p>{ppr}{inner}</w:p>"


def _table(rows: list[list[str]]) -> str:
    cols = max(len(r) for r in rows)
    width = 9000 // max(cols, 1)
    border = '<w:{0} w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
    borders = "".join(border.format(b) for b in ("top", "left", "bottom", "right", "insideH", "insideV"))
    grid = "".join(f'<w:gridCol w:w="{width}"/>' for _ in range(cols))
    body = []
    for i, row in enumerate(rows):
        cells = []
        for c in range(cols):
            text = row[c] if c < len(row) else ""
            shade = '<w:shd w:val="clear" w:color="auto" w:fill="F1F5F9"/>' if i == 0 else ""
            cells.append(
                f'<w:tc><w:tcPr><w:tcW w:w="{width}" w:type="dxa"/>{shade}</w:tcPr>'
                f"{_para(_runs(text, bold=i == 0))}</w:tc>"
            )
        body.append(f"<w:tr>{''.join(cells)}</w:tr>")
    return (
        f'<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/><w:tblBorders>{borders}</w:tblBorders></w:tblPr>'
        f"<w:tblGrid>{grid}</w:tblGrid>{''.join(body)}</w:tbl>"
        + _para("")  # jadvaldan keyin bo'sh qator (Word jadvallarni yopishtirib yubormasin)
    )


def _split_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def markdown_to_body(text: str) -> str:
    """Bot javobidagi markdown'ni WordprocessingML paragraflariga o'giradi."""
    out: list[str] = []
    lines = text.replace("\r\n", "\n").split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        # Jadval: "|" bilan boshlanuvchi ketma-ket qatorlar (ajratuvchi qator tashlanadi)
        if line.lstrip().startswith("|"):
            rows: list[list[str]] = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                if not _TABLE_SEP.match(lines[i]):
                    rows.append(_split_row(lines[i]))
                i += 1
            if rows:
                out.append(_table(rows))
            continue
        i += 1
        if not line.strip():
            continue
        if m := _HEADING.match(line):
            out.append(_para(_runs(m.group(2).strip("# ")), "Heading"))
        elif m := _BULLET.match(line):
            out.append(_para(_run("•\t", False) + _runs(m.group(1)), "ListItem"))
        elif m := _NUMBERED.match(line):
            out.append(_para(_run(f"{m.group(1)}\t", False) + _runs(m.group(2)), "ListItem"))
        elif line.strip() in ("---", "***", "___"):
            continue
        else:
            out.append(_para(_runs(line)))
    return "".join(out)


def _fmt(dt: datetime | None) -> str:
    return dt.strftime("%d.%m.%Y %H:%M") if dt else ""


def build_chat_docx(
    title: str,
    messages: list[ExportMessage],
    *,
    user_label: str,
    bot_label: str,
    meta_line: str,
) -> bytes:
    """Suhbatdan .docx fayl (bayt) yasaydi."""
    body = [_para(_runs(title), "Title"), _para(_runs(meta_line), "Meta")]
    for m in messages:
        who = user_label if m.role == "user" else bot_label
        when = _fmt(m.created_at)
        body.append(_para(_run(who, True) + (_run(f"  ·  {when}", False) if when else ""), "Speaker"))
        body.append(markdown_to_body(m.content) or _para(""))
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{_W_NS}"><w:body>{"".join(body)}'
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134" w:header="567" w:footer="567" w:gutter="0"/>'
        "</w:sectPr></w:body></w:document>"
    )
    core = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
        'xmlns:dc="http://purl.org/dc/elements/1.1/">'
        f"<dc:title>{escape(_BAD_XML.sub('', title))}</dc:title><dc:creator>Turon AI</dc:creator>"
        "</cp:coreProperties>"
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("word/_rels/document.xml.rels", _DOC_RELS)
        z.writestr("word/document.xml", document)
        z.writestr("word/styles.xml", _STYLES)
        z.writestr("docProps/core.xml", core)
    return buf.getvalue()
