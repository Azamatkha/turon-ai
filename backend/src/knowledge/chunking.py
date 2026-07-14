"""Small text chunker.

Splits on blank lines (paragraphs). Over-long paragraphs are broken down on
sentence boundaries, then line boundaries, and only as a last resort on word
boundaries — never mid-word. The resulting pieces are then packed into chunks
between `min_chars` and `max_chars`: a short piece (e.g. a lone heading or a
one-line leftover) is merged into its neighbour instead of becoming its own
tiny chunk.
"""

import re

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def _split_sentences(paragraph: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_RE.split(paragraph) if s.strip()]


def _split_by_words(text: str, max_chars: int) -> list[str]:
    """Oxirgi chora: so'zlarni chegara qilib bo'lamiz (hech qachon so'z ichidan
    kesmaymiz)."""
    words = text.split(" ")
    chunks: list[str] = []
    current = ""
    for word in words:
        if current and len(current) + 1 + len(word) > max_chars:
            chunks.append(current)
            current = ""
        current = f"{current} {word}" if current else word
    if current:
        chunks.append(current)
    return chunks


def _pack_units(units: list[str], max_chars: int, joiner: str) -> list[str]:
    chunks: list[str] = []
    current = ""
    for unit in units:
        if current and len(current) + len(joiner) + len(unit) > max_chars:
            chunks.append(current)
            current = ""
        if len(unit) <= max_chars:
            current = f"{current}{joiner}{unit}" if current else unit
        else:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(_split_by_words(unit, max_chars))
    if current:
        chunks.append(current)
    return chunks


def _explode_paragraph(para: str, max_chars: int) -> list[str]:
    """Bitta paragraf max_chars'dan uzun bo'lsa — uni kichikroq bo'laklarga
    ajratadi: avval gaplarga, keyin qatorlarga, oxirida so'zlarga."""
    sentences = _split_sentences(para)
    if len(sentences) > 1:
        return _pack_units(sentences, max_chars, " ")

    # Nuqta topilmadi (masalan jadvaldan kelgan matn) — gap o'rtasidan xom
    # kesib tashlamaslik uchun avval qator chegaralaridan (\n) foydalanamiz,
    # faqat shundan keyin so'z chegarasiga o'tamiz.
    lines = [ln for ln in para.split("\n") if ln.strip()]
    if len(lines) > 1:
        return _pack_units(lines, max_chars, "\n")

    return _split_by_words(para, max_chars)


def chunk_text(text: str, max_chars: int = 800, min_chars: int = 200) -> list[str]:
    text = text.strip()
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    # 1) Butun matnni "bo'lak nomzodlari"ga tekislaymiz — max_chars'dan uzun
    #    paragraflar avvaldan kichikroq bo'laklarga ajratib qo'yiladi.
    units: list[str] = []
    for para in paragraphs:
        if len(para) <= max_chars:
            units.append(para)
        else:
            units.extend(_explode_paragraph(para, max_chars))

    # 2) Bo'laklarni ketma-ket paketlaymiz: sarlavha yoki bir jumlalik qoldiq
    #    kabi kichik bo'lakni (< min_chars) navbatdagisiga qo'shib yuboramiz,
    #    hatto shu bilan max_chars biroz oshsa ham — ko'plab mayda-chuyda
    #    bo'laklarga bo'linib ketishidan ko'ra shu ma'qul.
    chunks: list[str] = []
    current = ""
    for unit in units:
        if not current:
            current = unit
            continue
        candidate = f"{current}\n\n{unit}"
        if len(candidate) <= max_chars or len(current) < min_chars:
            current = candidate
        else:
            chunks.append(current)
            current = unit
    if current:
        # Oxirgi qoldiq juda kichik bo'lsa — oldingi bo'lakka qo'shib yuboramiz
        if chunks and len(current) < min_chars:
            chunks[-1] = f"{chunks[-1]}\n\n{current}"
        else:
            chunks.append(current)

    return chunks
