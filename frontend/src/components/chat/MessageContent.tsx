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

// Yengil markdown -> HTML: paragraf, "* " / "- " ro'yxatlar, qalin, link
function renderMarkdown(text: string): string {
  const lines = escapeHtml(text).split(/\r?\n/);
  const out: string[] = [];
  let inList = false;

  for (const raw of lines) {
    const line = raw.trimEnd();
    const bullet = line.match(/^\s*[*-]\s+(.*)$/);
    if (bullet) {
      if (!inList) {
        out.push("<ul>");
        inList = true;
      }
      out.push(`<li>${inline(bullet[1])}</li>`);
    } else {
      if (inList) {
        out.push("</ul>");
        inList = false;
      }
      if (line.trim() !== "") out.push(`<p>${inline(line)}</p>`);
    }
  }
  if (inList) out.push("</ul>");
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
