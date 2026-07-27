// To'lov jadvali (amortizatsiya) hisobi va Excel'ga eksporti.
// Ko'rish oynasi ham, yuklash tugmasi ham SHU yerdan foydalanadi — jadval
// ikki joyda ikki xil chiqmasligi uchun.

export type PayMethod = "flat" | "annuity" | "diff";

// Sug'urta — asosiy qarzning shu ulushi. Rasmiy sayt shablonidan olindi:
// 1 000 000 -> 12 000 va 20 000 000 -> 240 000 (ikkalasi ham 1.2%).
export const INSURANCE_RATE = 0.012;

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

const addMonths = (date: Date, m: number): Date => {
  const d = new Date(date);
  d.setMonth(d.getMonth() + m);
  return d;
};

export function buildSchedule(
  principal: number,
  ratePct: number,
  months: number,
  method: PayMethod,
  startDate: Date = new Date()
): ScheduleResult {
  const r = ratePct / 100 / 12;
  const n = Math.max(1, Math.round(months));
  const annuityPay =
    r === 0 ? principal / n : (principal * r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
  // Ustama (flat): foiz butun summaga hisoblanadi, oylarga teng bo'linadi
  const flatInterestPer = (principal * (ratePct / 100) * (n / 12)) / n;

  const rows: ScheduleRow[] = [];
  let balance = principal;
  let prev = startDate;
  let totalInterest = 0;

  for (let k = 1; k <= n; k++) {
    const date = addMonths(startDate, k);
    const days = Math.round((date.getTime() - prev.getTime()) / 86_400_000);
    const bal = balance;
    let interest: number;
    let principalPay: number;

    if (method === "annuity") {
      interest = bal * r;
      principalPay = annuityPay - interest;
    } else if (method === "diff") {
      principalPay = principal / n;
      interest = bal * r;
    } else {
      principalPay = principal / n;
      interest = flatInterestPer;
    }
    // Oxirgi oy — qoldiqni to'liq yopamiz (yumaloqlash qoldig'i qolmasin)
    if (k === n) principalPay = bal;

    const total = principalPay + interest;
    totalInterest += interest;
    rows.push({ k, date, balance: bal, principal: principalPay, interest, total, days });
    balance = bal - principalPay;
    prev = date;
  }

  const insurance = principal * INSURANCE_RATE;
  const totalPaid = principal + totalInterest;
  return {
    rows,
    totalPrincipal: principal,
    totalInterest,
    totalPaid,
    insurance,
    fullCost: totalPaid + insurance,
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

// ---- Excel eksport ----
// Yangi npm paketi QO'SHMAYMIZ (bank tarmog'idagi SSL/proxy tufayli build
// buzilib ketmasin) — Excel o'zi ochadigan SpreadsheetML 2003 (XML) formatida
// yasaymiz. Raqamlar haqiqiy son sifatida ketadi, ustun kengligi va qalin
// sarlavha ham ishlaydi.

const xmlEsc = (s: string): string =>
  s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

const numCell = (v: number): string =>
  `<Cell ss:StyleID="num"><Data ss:Type="Number">${v.toFixed(2)}</Data></Cell>`;

const txtCell = (v: string, style = ""): string =>
  `<Cell${style ? ` ss:StyleID="${style}"` : ""}><Data ss:Type="String">${xmlEsc(v)}</Data></Cell>`;

const intCell = (v: number): string =>
  `<Cell><Data ss:Type="Number">${v}</Data></Cell>`;

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

export function scheduleToExcelXml(res: ScheduleResult, L: ExcelLabels): string {
  const header =
    "<Row ss:StyleID='hdr'>" +
    [L.no, L.date, L.balance, L.principal, L.interest, L.total, L.days]
      .map((h) => txtCell(h, "hdr"))
      .join("") +
    "</Row>";

  const body = res.rows
    .map(
      (r) =>
        "<Row>" +
        intCell(r.k) +
        txtCell(fmtDate(r.date)) +
        numCell(r.balance) +
        numCell(r.principal) +
        numCell(r.interest) +
        numCell(r.total) +
        intCell(r.days) +
        "</Row>"
    )
    .join("");

  const totals =
    "<Row ss:StyleID='tot'>" +
    txtCell(L.totalRow, "tot") +
    txtCell("", "tot") +
    txtCell("", "tot") +
    numCell(res.totalPrincipal) +
    numCell(res.totalInterest) +
    numCell(res.totalPaid) +
    txtCell("", "tot") +
    "</Row>";

  const extra =
    "<Row/>" +
    `<Row>${txtCell(L.insurance, "bold")}${txtCell("")}${txtCell("")}${txtCell("")}${txtCell("")}${numCell(res.insurance)}</Row>` +
    `<Row>${txtCell(L.fullCost, "bold")}${txtCell("")}${txtCell("")}${txtCell("")}${txtCell("")}${numCell(res.fullCost)}</Row>`;

  return `<?xml version="1.0" encoding="UTF-8"?>
<?mso-application progid="Excel.Sheet"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
 <Styles>
  <Style ss:ID="Default" ss:Name="Normal"><Alignment ss:Vertical="Center"/><Font ss:FontName="Calibri" ss:Size="11"/></Style>
  <Style ss:ID="hdr"><Font ss:FontName="Calibri" ss:Size="11" ss:Bold="1"/><Interior ss:Color="#DCE6F1" ss:Pattern="Solid"/><Alignment ss:Horizontal="Center" ss:WrapText="1" ss:Vertical="Center"/></Style>
  <Style ss:ID="num"><NumberFormat ss:Format="#,##0.00"/></Style>
  <Style ss:ID="tot"><Font ss:FontName="Calibri" ss:Size="11" ss:Bold="1"/><NumberFormat ss:Format="#,##0.00"/></Style>
  <Style ss:ID="bold"><Font ss:FontName="Calibri" ss:Size="11" ss:Bold="1"/></Style>
 </Styles>
 <Worksheet ss:Name="Jadval">
  <Table>
   <Column ss:Width="34"/><Column ss:Width="72"/><Column ss:Width="104"/>
   <Column ss:Width="118"/><Column ss:Width="118"/><Column ss:Width="118"/>
   <Column ss:Width="62"/>
   <Row><Cell ss:StyleID="bold"><Data ss:Type="String">${xmlEsc(L.title)}</Data></Cell></Row>
   <Row/>
   ${header}${body}${totals}${extra}
  </Table>
 </Worksheet>
</Workbook>`;
}

export function downloadSchedule(res: ScheduleResult, labels: ExcelLabels, filename: string): void {
  const xml = scheduleToExcelXml(res, labels);
  // UTF-8 BOM — Excel kirill/lotin harflarni to'g'ri o'qishi uchun
  const blob = new Blob(["﻿" + xml], { type: "application/vnd.ms-excel;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
