import type { MouseEvent } from "react";
import styles from "./MessageContent.module.css";

// Nusxalash tugmalari yorliqlari (interfeys tilida). Berilmasa — o'zbekcha.
export interface ContentLabels {
  copy: string;
  copied: string;
  copyTable: string;
}

const DEFAULT_LABELS: ContentLabels = {
  copy: "Nusxalash",
  copied: "Nusxalandi",
  copyTable: "Jadvalni nusxalash",
};

// HTML belgilarni xavfsizlaymiz (model matnidan teg kirmasligi uchun)
function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function encHref(u: string): string {
  return u.replace(/"/g, "%22");
}

// Atribut ichiga xavfsiz (yorliqlar tarjimadan keladi, baribir ekranlaymiz)
function attr(s: string): string {
  return escapeHtml(s).replace(/"/g, "&quot;");
}

// Bir qatordagi inline markdown: `kod`, **qalin**, [matn](url) va yalang'och url -> link
function inline(s: string): string {
  // Vaqtincha null-belgi bilan "stash" qilamiz — kod ichidagi ** yoki url,
  // matndagi raqamlar ("50 000") bilan chalkashmasin.
  const stashed: string[] = [];
  const stash = (html: string): string => {
    stashed.push(html);
    return "\x00" + (stashed.length - 1) + "\x00";
  };
  const anchor = (url: string, text: string): string =>
    `<a href="${encHref(url)}" target="_blank" rel="noopener noreferrer">${text}</a>`;

  // 0) Inline kod: `...` — ichidagi belgilar boshqa qoidalarga tushmaydi
  let out = s.replace(/`([^`\n]+)`/g, (_m, code: string) => stash(`<code class="${styles.inlineCode}">${code}</code>`));

  out = out.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

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

  // 3) Stash'dagilarni qaytaramiz
  return out.replace(/\x00(\d+)\x00/g, (_m, i: string) => stashed[Number(i)]);
}

// ---- Kod bloklari ----

const KEYWORDS = new Set(
  (
    "select from where and or not in is null as join left right inner outer on group by order having " +
    "insert into values update set delete create table alter drop limit offset distinct union all case when then else end " +
    "def class return if elif else for while import from as with try except finally raise lambda yield async await pass break continue none true false self " +
    "function const let var new this typeof instanceof export default interface type extends implements public private protected static void null undefined " +
    "true false"
  ).split(" ")
);

// Yengil, xavfsiz ranglash: matn allaqachon ekranlangan (escapeHtml), biz faqat
// <span> o'raymiz. Bitta regex bilan bir martalik o'tish — ichma-ich almashtirish yo'q.
const TOKEN =
  /(\/\/[^\n]*|#[^\n]*|--[^\n]*|\/\*[\s\S]*?\*\/)|("(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*')|(\b\d+(?:[.,]\d+)?\b)|([A-Za-z_][A-Za-z0-9_]*)/g;

function highlight(code: string, lang: string): string {
  // Oddiy matn / natija bloklari ranglanmaydi
  if (/^(text|txt|plain|output)$/i.test(lang)) return code;
  // "#" Python/bash'da izoh, boshqa tillarda (masalan CSS rang) emas
  const hashComment = /^(py|python|sh|bash|shell|yaml|yml|toml|ini|conf|r)$/i.test(lang) || !lang;
  return code.replace(TOKEN, (m, comment: string, str: string, num: string, word: string) => {
    if (comment) {
      if (comment.startsWith("#") && !hashComment) return m;
      return `<span class="${styles.tokComment}">${comment}</span>`;
    }
    if (str) return `<span class="${styles.tokString}">${str}</span>`;
    if (num) return `<span class="${styles.tokNumber}">${num}</span>`;
    if (word && KEYWORDS.has(word.toLowerCase())) return `<span class="${styles.tokKeyword}">${word}</span>`;
    return m;
  });
}

function renderCode(code: string, lang: string, labels: ContentLabels): string {
  const head = `<div class="${styles.codeHead}"><span class="${styles.codeLang}">${escapeHtml(lang || "code")}</span>`
    + `<button type="button" class="${styles.copyBtn}" data-act="copy-code" data-label="${attr(labels.copy)}" data-done="${attr(labels.copied)}">${escapeHtml(labels.copy)}</button></div>`;
  return `<div class="${styles.codeBlock}">${head}<pre class="${styles.pre}"><code>${highlight(code, lang)}</code></pre></div>`;
}

// ---- Jadvallar ----

// Jadval qatorini kataklarga bo'ladi: "| a | b |" -> ["a", "b"]
function splitTableRow(line: string): string[] {
  return line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((c) => c.trim());
}

const isTableRow = (l: string): boolean => /^\s*\|.*\|\s*$/.test(l);
// Ajratgich qator: faqat |, :, -, bo'sh joy va kamida bitta "-"
const isTableSep = (l: string): boolean =>
  /^\s*\|?[\s:|-]+\|?\s*$/.test(l) && l.includes("-");

// "22%", "1 250 000 so'm", "-3,5", "$120" — son ustuni (o'ngga tekislanadi)
const NUMERIC = /^[-+−]?[$€£₽]?\s*\d[\d\s.,]*\s*(%|so[‘'’`]?m|sum|сум|сўм|usd|eur|rub|mln|mlrd|млн|ming|oy|yil|kun)?\.?$/i;

function isNumericColumn(rows: string[][], k: number): boolean {
  const vals = rows.map((r) => (r[k] ?? "").replace(/\*\*/g, "").trim()).filter((v) => v && v !== "—" && v !== "-");
  return vals.length > 0 && vals.filter((v) => NUMERIC.test(v)).length / vals.length >= 0.8;
}

function renderTable(header: string[], rows: string[][], labels: ContentLabels): string {
  const numeric = header.map((_, k) => isNumericColumn(rows, k));
  const cls = (k: number) => (numeric[k] ? ` class="${styles.num}"` : "");
  const th = header.map((c, k) => `<th${cls(k)}>${inline(c)}</th>`).join("");
  const trs = rows
    .map((r) => {
      let cells = "";
      for (let k = 0; k < header.length; k++) cells += `<td${cls(k)}>${inline(r[k] ?? "")}</td>`;
      return `<tr>${cells}</tr>`;
    })
    .join("");
  const tools = `<div class="${styles.tableTools}"><button type="button" class="${styles.copyBtn}" data-act="copy-table" data-label="${attr(labels.copyTable)}" data-done="${attr(labels.copied)}">${escapeHtml(labels.copyTable)}</button></div>`;
  return `<div class="${styles.tableBlock}">${tools}<div class="${styles.tableWrap}"><table class="${styles.table}"><thead><tr>${th}</tr></thead><tbody>${trs}</tbody></table></div></div>`;
}

// Yengil markdown -> HTML: paragraf, ro'yxatlar (• va 1.), qalin, link, kod, JADVAL
function renderMarkdown(text: string, labels: ContentLabels): string {
  const lines = escapeHtml(text).split(/\r?\n/);
  const out: string[] = [];
  let list: "ul" | "ol" | null = null;
  const closeList = () => {
    if (list) {
      out.push(`</${list}>`);
      list = null;
    }
  };
  const openList = (kind: "ul" | "ol", start?: number) => {
    if (list === kind) return;
    closeList();
    out.push(kind === "ol" && start && start !== 1 ? `<ol start="${start}">` : `<${kind}>`);
    list = kind;
  };

  let i = 0;
  while (i < lines.length) {
    const line = lines[i].trimEnd();

    // Kod bloki: ```til ... ``` (yopilmagan bo'lsa — oxirigacha; oqim paytida ham to'g'ri ko'rinadi)
    const fence = line.match(/^\s*```\s*([\w+#.-]*)\s*$/);
    if (fence) {
      closeList();
      const body: string[] = [];
      i++;
      while (i < lines.length && !/^\s*```\s*$/.test(lines[i])) {
        body.push(lines[i]);
        i++;
      }
      i++; // yopuvchi ```
      out.push(renderCode(body.join("\n"), fence[1], labels));
      continue;
    }

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
      out.push(renderTable(header, rows, labels));
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
    const numbered = line.match(/^\s*(\d{1,3})[.)]\s+(.*)$/);
    if (bullet) {
      openList("ul");
      out.push(`<li>${inline(bullet[1])}</li>`);
    } else if (numbered) {
      openList("ol", Number(numbered[1]));
      out.push(`<li>${inline(numbered[2])}</li>`);
    } else if (/^\s*(-{3,}|\*{3,}|_{3,})\s*$/.test(line)) {
      closeList();
      out.push(`<hr class="${styles.hr}" />`);
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
  let out = s.replace(/\*\*(.+?)\*\*/g, "$1").replace(/`([^`\n]+)`/g, "$1");
  out = out.replace(
    /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
    (_m, text: string, url: string) => (text === url ? url : `${text} (${url})`)
  );
  return out;
}

export function toPlainText(text: string): string {
  const lines = text.split(/\r?\n/);
  const out: string[] = [];
  let inCode = false;
  for (const raw of lines) {
    const line = raw.trimEnd();
    // Kod bloki ichidagi qatorlar o'zgarishsiz, ``` qatorlarining o'zi tashlanadi
    if (/^\s*```/.test(line)) {
      inCode = !inCode;
      continue;
    }
    if (inCode) {
      out.push(raw);
      continue;
    }
    const bullet = line.match(/^\s*[*-]\s+(.*)$/);
    out.push(bullet ? `• ${stripInline(bullet[1])}` : stripInline(line));
  }
  return out.join("\n");
}

// Jadvalni TSV ko'rinishida (Excel/Word'ga qo'yilganda katak-katak tushadi)
function tableToTsv(table: HTMLTableElement): string {
  return Array.from(table.rows)
    .map((row) => Array.from(row.cells).map((c) => (c.textContent ?? "").replace(/\s+/g, " ").trim()).join("\t"))
    .join("\n");
}

// innerHTML ichidagi tugmalar — bitta tinglovchi (event delegation)
function onContentClick(e: MouseEvent<HTMLDivElement>) {
  const btn = (e.target as HTMLElement).closest<HTMLButtonElement>("button[data-act]");
  if (!btn) return;
  let text = "";
  if (btn.dataset.act === "copy-code") {
    text = btn.closest(`.${styles.codeBlock}`)?.querySelector("code")?.textContent ?? "";
  } else if (btn.dataset.act === "copy-table") {
    const table = btn.closest(`.${styles.tableBlock}`)?.querySelector("table");
    if (table) text = tableToTsv(table);
  }
  if (!text) return;
  navigator.clipboard?.writeText(text).then(() => {
    btn.textContent = btn.dataset.done ?? "✓";
    window.setTimeout(() => {
      btn.textContent = btn.dataset.label ?? "";
    }, 1400);
  }).catch(() => {
    /* clipboard yopiq (http yoki ruxsat yo'q) — matnni qo'lda belgilash mumkin */
  });
}

export default function MessageContent({ text, labels }: { text: string; labels?: ContentLabels }) {
  return (
    // Faqat ichki <button>lar bosiladi (klaviaturadan ham) — div o'zi interaktiv emas
    // eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-static-element-interactions
    <div
      className={styles.content}
      onClick={onContentClick}
      dangerouslySetInnerHTML={{ __html: renderMarkdown(text, labels ?? DEFAULT_LABELS) }}
    />
  );
}
