// To'lov jadvalini KO'RSATISH va Excel'ga eksport qilish.
//
// HISOB BU YERDA EMAS: jadval qatorlari backenddan keladi
// (`services/calculatorService.ts` -> POST /v1/calculator/schedule).
// Ilgari shu faylda `buildSchedule()` bor edi — ya'ni kredit formulasi
// frontda ham, backendda ham turishi kerak bo'lardi. Endi formula yagona
// manbada (backend `src/calculator/services.py`), bu fayl esa faqat
// ko'rinish qatlami.

import type { ScheduleResultDto } from "../services/calculatorService";
import { packXlsx, xmlEsc } from "./xlsx";

export interface ScheduleRow {
  k: number;          // tartib raqami
  date: Date;         // to'lov sanasi
  balance: number;    // to'lovdan OLDINGI kredit qoldig'i
  principal: number;  // asosiy qarzni to'lash summasi
  interest: number;   // foizlar summasi
  total: number;      // jami to'lanadigan summa
  days: number;       // oldingi to'lovdan beri o'tgan kunlar
}

export interface ScheduleResult {
  rows: ScheduleRow[];
  totalPrincipal: number;
  totalInterest: number;
  totalPaid: number;
  insurance: number;
  fullCost: number;
}

/**
 * Backend javobini (snake_case, sana — ISO matn) ko'rinish qatlami
 * kutadigan shaklga (camelCase, sana — `Date`) o'giradi.
 *
 * Sana `new Date("2026-08-14")` bilan emas, qo'lda ajratib yasaladi: ISO
 * "kun" formatini brauzer UTC deb o'qiydi va UTC+5 da sana bir kun orqaga
 * surilib ketardi (14-avgust -> 13-avgust).
 */
export function scheduleFromDto(dto: ScheduleResultDto): ScheduleResult {
  return {
    rows: dto.rows.map((r) => {
      const [y, m, d] = r.date.split("-").map(Number);
      return {
        k: r.k,
        date: new Date(y, m - 1, d),
        balance: r.balance,
        principal: r.principal,
        interest: r.interest,
        total: r.total,
        days: r.days,
      };
    }),
    totalPrincipal: dto.total_principal,
    totalInterest: dto.total_interest,
    totalPaid: dto.total_paid,
    insurance: dto.insurance,
    fullCost: dto.full_cost,
  };
}

// "1 234 567.89" — bo'shliq bilan guruhlangan, 2 kasr xona
export const fmt2 = (n: number): string => {
  const fixed = n.toFixed(2);
  const [intPart, dec] = fixed.split(".");
  const neg = intPart.startsWith("-");
  const digits = neg ? intPart.slice(1) : intPart;
  return `${neg ? "-" : ""}${digits.replace(/\B(?=(\d{3})+(?!\d))/g, " ")}.${dec}`;
};

export const fmtDate = (d: Date): string => {
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  return `${dd}.${mm}.${d.getFullYear()}`;
};

// ---- Excel (.xlsx) eksport ----

export interface ExcelLabels {
  title: string;
  no: string;
  date: string;
  balance: string;
  principal: string;
  interest: string;
  total: string;
  days: string;
  totalRow: string;
  insurance: string;
  fullCost: string;
  currency: string;
}

// styles.xml dagi cellXfs tartibi bilan mos stil indekslari
const S = {
  title: 1,
  hdr: 2,
  int: 3,
  intZ: 4,
  date: 5,
  dateZ: 6,
  num: 7,
  numZ: 8,
  numB: 9,
  numBZ: 10,
  totLbl: 11,
  totNum: 12,
  sumLbl: 13,
  sumNum: 14,
  sumLblB: 15,
  sumNumB: 16,
} as const;

const colRef = (i: number): string => String.fromCharCode(65 + i);

const cNum = (ref: string, v: number, style: number): string =>
  `<c r="${ref}" s="${style}"><v>${v}</v></c>`;

const cStr = (ref: string, v: string, style: number): string =>
  `<c r="${ref}" s="${style}" t="inlineStr"><is><t xml:space="preserve">${xmlEsc(v)}</t></is></c>`;

const cEmpty = (ref: string, style: number): string => `<c r="${ref}" s="${style}"/>`;

function buildSheetXml(res: ScheduleResult, L: ExcelLabels): string {
  const rows: string[] = [];
  const merges: string[] = [];
  let r = 1;

  // Sarlavha (A:G birlashtirilgan)
  rows.push(`<row r="${r}" ht="30" customHeight="1">${cStr("A" + r, L.title, S.title)}</row>`);
  merges.push(`A${r}:G${r}`);
  r++;

  rows.push(`<row r="${r}" ht="8" customHeight="1"/>`);
  r++;

  // Ustun sarlavhalari
  const heads = [L.no, L.date, L.balance, L.principal, L.interest, L.total, L.days];
  rows.push(
    `<row r="${r}" ht="34" customHeight="1">` +
      heads.map((h, i) => cStr(colRef(i) + r, h, S.hdr)).join("") +
      "</row>"
  );
  r++;

  // To'lovlar (juft qatorlar zebra fonda)
  for (const row of res.rows) {
    const z = row.k % 2 === 0;
    rows.push(
      `<row r="${r}" ht="19" customHeight="1">` +
        cNum("A" + r, row.k, z ? S.intZ : S.int) +
        cStr("B" + r, fmtDate(row.date), z ? S.dateZ : S.date) +
        cNum("C" + r, +row.balance.toFixed(2), z ? S.numZ : S.num) +
        cNum("D" + r, +row.principal.toFixed(2), z ? S.numZ : S.num) +
        cNum("E" + r, +row.interest.toFixed(2), z ? S.numZ : S.num) +
        cNum("F" + r, +row.total.toFixed(2), z ? S.numBZ : S.numB) +
        cNum("G" + r, row.days, z ? S.intZ : S.int) +
        "</row>"
    );
    r++;
  }

  // "Jami" — yorliq A:C birlashtiriladi (tor ustunda kesilib qolmasin)
  rows.push(
    `<row r="${r}" ht="24" customHeight="1">` +
      cStr("A" + r, L.totalRow, S.totLbl) +
      cEmpty("B" + r, S.totLbl) +
      cEmpty("C" + r, S.totLbl) +
      cNum("D" + r, +res.totalPrincipal.toFixed(2), S.totNum) +
      cNum("E" + r, +res.totalInterest.toFixed(2), S.totNum) +
      cNum("F" + r, +res.totalPaid.toFixed(2), S.totNum) +
      cEmpty("G" + r, S.totNum) +
      "</row>"
  );
  merges.push(`A${r}:C${r}`);
  r++;

  rows.push(`<row r="${r}" ht="8" customHeight="1"/>`);
  r++;

  // Sug'urta va to'liq qiymat — yorliq A:E, qiymat F ("Jami to'lov") ustunida
  const extra: Array<[string, number, number, number]> = [
    [L.insurance, res.insurance, S.sumLbl, S.sumNum],
    [L.fullCost, res.fullCost, S.sumLblB, S.sumNumB],
  ];
  for (const [label, value, lblStyle, numStyle] of extra) {
    rows.push(
      `<row r="${r}" ht="22" customHeight="1">` +
        cStr("A" + r, label, lblStyle) +
        ["B", "C", "D", "E"].map((c) => cEmpty(c + r, lblStyle)).join("") +
        cNum("F" + r, +value.toFixed(2), numStyle) +
        "</row>"
    );
    merges.push(`A${r}:E${r}`);
    r++;
  }

  const widths = [5.5, 12, 16.5, 18.5, 18.5, 18.5, 9.5];
  const cols = widths
    .map((w, i) => `<col min="${i + 1}" max="${i + 1}" width="${w}" customWidth="1"/>`)
    .join("");

  return (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">' +
    // Sarlavha qatori muzlatiladi — pastga surganda ko'rinib turadi
    '<sheetViews><sheetView workbookViewId="0">' +
    '<pane ySplit="3" topLeftCell="A4" activePane="bottomLeft" state="frozen"/>' +
    "</sheetView></sheetViews>" +
    '<sheetFormatPr defaultRowHeight="18"/>' +
    `<cols>${cols}</cols>` +
    `<sheetData>${rows.join("")}</sheetData>` +
    `<mergeCells count="${merges.length}">` +
    merges.map((m) => `<mergeCell ref="${m}"/>`).join("") +
    "</mergeCells>" +
    '<pageMargins left="0.4" right="0.4" top="0.5" bottom="0.5" header="0.3" footer="0.3"/>' +
    '<pageSetup orientation="landscape" fitToWidth="1" fitToHeight="0"/>' +
    "</worksheet>"
  );
}

const THIN = '<color rgb="FFB7C4D4"/>';
const STYLES_XML =
  '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
  '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">' +
  '<numFmts count="1"><numFmt numFmtId="164" formatCode="#,##0.00"/></numFmts>' +
  '<fonts count="5">' +
  '<font><sz val="11"/><name val="Calibri"/></font>' +
  '<font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font>' +
  '<font><b/><sz val="15"/><color rgb="FF1B4B7A"/><name val="Calibri"/></font>' +
  '<font><b/><sz val="11"/><color rgb="FF1B4B7A"/><name val="Calibri"/></font>' +
  '<font><b/><sz val="11"/><name val="Calibri"/></font>' +
  "</fonts>" +
  '<fills count="5">' +
  '<fill><patternFill patternType="none"/></fill>' +
  '<fill><patternFill patternType="gray125"/></fill>' +
  '<fill><patternFill patternType="solid"><fgColor rgb="FF1B4B7A"/><bgColor indexed="64"/></patternFill></fill>' +
  '<fill><patternFill patternType="solid"><fgColor rgb="FFDCE6F1"/><bgColor indexed="64"/></patternFill></fill>' +
  '<fill><patternFill patternType="solid"><fgColor rgb="FFF5F8FB"/><bgColor indexed="64"/></patternFill></fill>' +
  "</fills>" +
  '<borders count="3">' +
  "<border><left/><right/><top/><bottom/><diagonal/></border>" +
  `<border><left style="thin">${THIN}</left><right style="thin">${THIN}</right>` +
  `<top style="thin">${THIN}</top><bottom style="thin">${THIN}</bottom><diagonal/></border>` +
  `<border><left style="thin">${THIN}</left><right style="thin">${THIN}</right>` +
  `<top style="medium"><color rgb="FF1B4B7A"/></top><bottom style="thin">${THIN}</bottom><diagonal/></border>` +
  "</borders>" +
  '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>' +
  '<cellXfs count="17">' +
  '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>' +
  '<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment vertical="center"/></xf>' +
  '<xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>' +
  '<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>' +
  '<xf numFmtId="0" fontId="0" fillId="4" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>' +
  '<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>' +
  '<xf numFmtId="0" fontId="0" fillId="4" borderId="1" xfId="0" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>' +
  '<xf numFmtId="164" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1" applyAlignment="1"><alignment vertical="center"/></xf>' +
  '<xf numFmtId="164" fontId="0" fillId="4" borderId="1" xfId="0" applyNumberFormat="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="center"/></xf>' +
  '<xf numFmtId="164" fontId="4" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyFont="1" applyBorder="1" applyAlignment="1"><alignment vertical="center"/></xf>' +
  '<xf numFmtId="164" fontId="4" fillId="4" borderId="1" xfId="0" applyNumberFormat="1" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="center"/></xf>' +
  '<xf numFmtId="0" fontId="3" fillId="3" borderId="2" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="left" vertical="center"/></xf>' +
  '<xf numFmtId="164" fontId="3" fillId="3" borderId="2" xfId="0" applyNumberFormat="1" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="center"/></xf>' +
  '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment horizontal="left" vertical="center"/></xf>' +
  '<xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyAlignment="1"><alignment vertical="center"/></xf>' +
  '<xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment horizontal="left" vertical="center"/></xf>' +
  '<xf numFmtId="164" fontId="3" fillId="0" borderId="0" xfId="0" applyNumberFormat="1" applyFont="1" applyAlignment="1"><alignment vertical="center"/></xf>' +
  "</cellXfs>" +
  '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>' +
  "</styleSheet>";

/** To'lov jadvalidan haqiqiy .xlsx faylni (Blob) yasaydi. */
export function buildScheduleXlsx(res: ScheduleResult, L: ExcelLabels): Blob {
  return packXlsx("Jadval", STYLES_XML, buildSheetXml(res, L));
}

/** Yuklanadigan fayl nomi — sana-vaqt bilan, shunda fayllar bir-birining
 * ustiga tushmaydi: "tolov_jadvali_9_34_28_7_2026.xlsx" (soat_daqiqa_kun_oy_yil). */
export function scheduleFileName(d: Date = new Date()): string {
  const p = [
    d.getHours(),
    d.getMinutes(),
    d.getDate(),
    d.getMonth() + 1,
    d.getFullYear(),
  ].join("_");
  return `tolov_jadvali_${p}.xlsx`;
}

export function downloadSchedule(res: ScheduleResult, labels: ExcelLabels, filename: string): void {
  const blob = buildScheduleXlsx(res, labels);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

