// Userning FILIALINI aniqlaydi. Bazada alohida "filial" ustuni yo'q: EDO'dan
// keladigan ma'lumotda filial goh departament o'rnida ("Samarqand BXM"), goh
// lavozim ichida ("Bosh mutaxassis (Shahrisabz BXM bo'yicha)") yoziladi.
// Shu ikki matndan filial nomini ajratib olamiz — bazaga tegmasdan.

// "<Nom> [shahar|tumani|viloyati] BXM | BXO | bank xizmatlari markazi/ofisi"
const BRANCH_RE =
  /([\p{L}ʻʼ'‘’`-]+(?:\s+(?:shahar|tumani|viloyati))?)\s+(bxm|bxo|bank\s+xizmatlari\s+(?:markazi|ofisi))/iu;

// Filial topilmadi, lekin departament bor — bosh ofis bo'limi
export const HEAD_OFFICE = "__head_office__";
// Filial ham, aniq departament ham yo'q (bo'sh yoki "Boshqa")
export const NO_BRANCH = "__none__";

const VAGUE_DEPTS = new Set(["boshqa", "бошқа", "другое", "прочее"]);

function normalizeName(raw: string): string {
  const name = raw.replace(/[ʻʼ‘’`]/g, "'").toLowerCase();
  // Faqat birinchi harf katta: "TOSHKENT SHAHAR" -> "Toshkent shahar"
  return name.charAt(0).toUpperCase() + name.slice(1);
}

function fromText(text: string | undefined | null): string | null {
  if (!text) return null;
  const m = BRANCH_RE.exec(text);
  if (!m) return null;
  const kind = /ofisi|bxo/i.test(m[2]) ? "BXO" : "BXM";
  return `${normalizeName(m[1])} ${kind}`;
}

/** Filial nomi ("Samarqand BXM"), yoki HEAD_OFFICE / NO_BRANCH. */
export function userBranch(dept: string | undefined | null, position: string | undefined | null): string {
  const found = fromText(dept) ?? fromText(position);
  if (found) return found;
  // "Boshqa" departamenti hech narsa demaydi — bosh ofis deb hisoblamaymiz
  const d = (dept ?? "").trim();
  return d && !VAGUE_DEPTS.has(d.toLowerCase()) ? HEAD_OFFICE : NO_BRANCH;
}
