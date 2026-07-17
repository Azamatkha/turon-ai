import styles from "./MessageContent.module.css";

// HTML belgilarni xavfsizlaymiz (model matnidan teg kirmasligi uchun)
function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function encHref(u: string): string {
  return u.replace(/"/g, "%22");
}

// Bir qatordagi inline markdown: **qalin**, [matn](url) va yalang'och url -> link
function inline(s: string): string {
  let out = s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

  // Linklarni vaqtincha null-belgi bilan "stash" qilamiz — matndagi raqamlar
  // (masalan "50 000") bilan chalkashmasligi uchun.
  const links: string[] = [];
  const stash = (html: string): string => {
    links.push(html);
    return "\x00" + (links.length - 1) + "\x00";
  };
  const anchor = (url: string, text: string): string =>
    `<a href="${encHref(url)}" target="_blank" rel="noopener noreferrer">${text}</a>`;

  // 1) Markdown havola: [matn](url)
  out = out.replace(
    /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
    (_m, text: string, url: string) => stash(anchor(url, text))
  );

  // 2) Yalang'och url (markdown havolalar allaqachon stash'da — tegilmaydi)
  out = out.replace(
    /(https?:\/\/[^\s<]+[^\s<.,:;!?)\]}"'])/g,
    (u: string) => stash(anchor(u, u))
  );

  // 3) Stash'dagi linklarni qaytaramiz
  return out.replace(/\x00(\d+)\x00/g, (_m, i: string) => links[Number(i)]);
}

// Jadval qatorini kataklarga bo'ladi: "| a | b |" -> ["a", "b"]
function splitTableRow(line: string): string[] {
  return line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());
}

const isTableRow = (l: string): boolean => /^\s*\|.*\|\s*$/.test(l);
// Ajratgich qator: faqat |, :, -, bo'sh joy va kamida bitta "-"
const isTableSep = (l: string): boolean =>
  /^\s*\|?[\s:|-]+\|?\s*$/.test(l) && l.includes("-");

function renderTable(header: string[], rows: string[][]): string {
  const th = header.map((c) => `<th>${inline(c)}</th>`).join("");
  const trs = rows
    .map((r) => {
      let cells = "";
      for (let k = 0; k < header.length; k++) cells += `<td>${inline(r[k] ?? "")}</td>`;
      return `<tr>${cells}</tr>`;
    })
    .join("");
  return `<div class="${styles.tableWrap}"><table class="${styles.table}"><thead><tr>${th}</tr></thead><tbody>${trs}</tbody></table></div>`;
}

// Yengil markdown -> HTML: paragraf, ro'yxatlar, qalin, link, JADVAL
function renderMarkdown(text: string): string {
  const lines = escapeHtml(text).split(/\r?\n/);
  const out: string[] = [];
  let inList = false;
  const closeList = () => {
    if (inList) {
      out.push("</ul>");
      inList = false;
    }
  };

  let i = 0;
  while (i < lines.length) {
    const line = lines[i].trimEnd();

    // Jadval: joriy qator + keyingisi ajratgich bo'lsa
    if (isTableRow(line) && i + 1 < lines.length && isTableSep(lines[i + 1])) {
      closeList();
      const header = splitTableRow(line);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && isTableRow(lines[i].trimEnd())) {
        rows.push(splitTableRow(lines[i].trimEnd()));
        i++;
      }
      out.push(renderTable(header, rows));
      continue;
    }

    // Markdown sarlavha ("## Matn") — model ba'zan chiqarib qoladi, xom "###"
    // bo'lib ko'rinmasligi uchun qalin sarlavha qilib beramiz.
    const heading = line.match(/^\s*#{1,6}\s+(.*)$/);
    if (heading) {
      closeList();
      out.push(`<div class="${styles.heading}">${inline(heading[1])}</div>`);
      i++;
      continue;
    }

    const bullet = line.match(/^\s*[*-]\s+(.*)$/);
    if (bullet) {
      if (!inList) {
        out.push("<ul>");
        inList = true;
      }
      out.push(`<li>${inline(bullet[1])}</li>`);
    } else {
      closeList();
      if (line.trim() !== "") out.push(`<p>${inline(line)}</p>`);
    }
    i++;
  }
  closeList();
  return out.join("");
}

// Markdown belgilarini olib tashlab, ekranda ko'ringan ko'rinishga mos toza matn qaytaradi
// (nusxalash tugmasi shuni ishlatadi — xom "**", "[matn](url)" emas).
function stripInline(s: string): string {
  let out = s.replace(/\*\*(.+?)\*\*/g, "$1");
  out = out.replace(
    /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
    (_m, text: string, url: string) => (text === url ? url : `${text} (${url})`)
  );
  return out;
}

export function toPlainText(text: string): string {
  const lines = text.split(/\r?\n/);
  const out: string[] = [];
  for (const raw of lines) {
    const line = raw.trimEnd();
    const bullet = line.match(/^\s*[*-]\s+(.*)$/);
    out.push(bullet ? `• ${stripInline(bullet[1])}` : stripInline(line));
  }
  return out.join("\n");
}

export default function MessageContent({ text }: { text: string }) {
  return (
    <div
      className={styles.content}
      dangerouslySetInnerHTML={{ __html: renderMarkdown(text) }}
    />
  );
}
