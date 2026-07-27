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

// Yacheyka yasovchilar. `merge` — o'ngga nechta yacheyka bilan birlashtirish
// (uzun yorliq tor ustunda kesilib qolmasligi uchun kerak).
const cell = (
  type: "Number" | "String",
  value: string,
  style?: string,
  merge?: number
): string => {
  const attrs =
    (style ? ` ss:StyleID="${style}"` : "") +
    (merge ? ` ss:MergeAcross="${merge}"` : "");
  return `<Cell${attrs}><Data ss:Type="${type}">${value}</Data></Cell>`;
};

const numCell = (v: number, style = "num"): string =>
  cell("Number", v.toFixed(2), style);

const txtCell = (v: string, style?: string, merge?: number): string =>
  cell("String", xmlEsc(v), style, merge);

const intCell = (v: number, style = "int"): string =>
  cell("Number", String(v), style);

// Bo'sh (lekin chegarali) yacheykalar — jadval to'ri uzilib qolmasin
const emptyCells = (n: number, style: string): string =>
  Array.from({ length: n }, () => `<Cell ss:StyleID="${style}"/>`).join("");

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
  // Sarlavha — 7 ustun bo'ylab birlashtirilgan, katta qalin shrift
  const titleRow =
    `<Row ss:Height="30">${txtCell(L.title, "title", 6)}</Row>` +
    '<Row ss:Height="8"/>';

  const header =
    '<Row ss:Height="34">' +
    [L.no, L.date, L.balance, L.principal, L.interest, L.total, L.days]
      .map((h) => txtCell(h, "hdr"))
      .join("") +
    "</Row>";

  // Toq/juft qatorlar biroz farqli fonda — uzun jadvalni ko'z bilan kuzatish oson
  const body = res.rows
    .map((r) => {
      const z = r.k % 2 === 0 ? "z" : "";
      return (
        '<Row ss:Height="19">' +
        intCell(r.k, `int${z}`) +
        txtCell(fmtDate(r.date), `date${z}`) +
        numCell(r.balance, `num${z}`) +
        numCell(r.principal, `num${z}`) +
        numCell(r.interest, `num${z}`) +
        numCell(r.total, `numB${z}`) +
        intCell(r.days, `int${z}`) +
        "</Row>"
      );
    })
    .join("");

  // "Jami" — yorliq 3 ustunga birlashtirilgan (kesilib qolmasin)
  const totals =
    '<Row ss:Height="24">' +
    txtCell(L.totalRow, "totLbl", 2) +
    numCell(res.totalPrincipal, "totNum") +
    numCell(res.totalInterest, "totNum") +
    numCell(res.totalPaid, "totNum") +
    emptyCells(1, "totNum") +
    "</Row>";

  // Sug'urta / to'liq qiymat — yorliq 4 ustunga birlashtiriladi, qiymat
  // "Jami to'lov" ustuni ostida turadi (avval tor A ustunida kesilib qolardi)
  const extra =
    '<Row ss:Height="8"/>' +
    '<Row ss:Height="22">' +
    txtCell(L.insurance, "sumLbl", 4) +
    numCell(res.insurance, "sumNum") +
    "</Row>" +
    '<Row ss:Height="22">' +
    txtCell(L.fullCost, "sumLblB", 4) +
    numCell(res.fullCost, "sumNumB") +
    "</Row>";

  // Chegara va shriftlarni takrorlab yozmaslik uchun qisqartmalar
  const B = (pos: string, w = "1", color = "#B7C4D4") =>
    `<Border ss:Position="${pos}" ss:LineStyle="Continuous" ss:Weight="${w}" ss:Color="${color}"/>`;
  const box = `<Borders>${B("Top")}${B("Bottom")}${B("Left")}${B("Right")}</Borders>`;
  const FONT = 'ss:FontName="Calibri" ss:Size="11"';
  const ZEBRA = '<Interior ss:Color="#F5F8FB" ss:Pattern="Solid"/>';
  const NUMFMT = '<NumberFormat ss:Format="#,##0.00"/>';

  return `<?xml version="1.0" encoding="UTF-8"?>
<?mso-application progid="Excel.Sheet"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:x="urn:schemas-microsoft-com:office:excel">
 <Styles>
  <Style ss:ID="Default" ss:Name="Normal"><Alignment ss:Vertical="Center"/><Font ${FONT}/></Style>

  <Style ss:ID="title"><Font ss:FontName="Calibri" ss:Size="15" ss:Bold="1" ss:Color="#1B4B7A"/><Alignment ss:Horizontal="Left" ss:Vertical="Center"/></Style>

  <Style ss:ID="hdr"><Font ss:FontName="Calibri" ss:Size="11" ss:Bold="1" ss:Color="#FFFFFF"/><Interior ss:Color="#1B4B7A" ss:Pattern="Solid"/><Alignment ss:Horizontal="Center" ss:Vertical="Center" ss:WrapText="1"/>${box}</Style>

  <Style ss:ID="int"><Alignment ss:Horizontal="Center" ss:Vertical="Center"/>${box}</Style>
  <Style ss:ID="intz"><Alignment ss:Horizontal="Center" ss:Vertical="Center"/>${box}${ZEBRA}</Style>
  <Style ss:ID="date"><Alignment ss:Horizontal="Center" ss:Vertical="Center"/>${box}</Style>
  <Style ss:ID="datez"><Alignment ss:Horizontal="Center" ss:Vertical="Center"/>${box}${ZEBRA}</Style>
  <Style ss:ID="num">${NUMFMT}${box}</Style>
  <Style ss:ID="numz">${NUMFMT}${box}${ZEBRA}</Style>
  <Style ss:ID="numB"><Font ss:FontName="Calibri" ss:Size="11" ss:Bold="1"/>${NUMFMT}${box}</Style>
  <Style ss:ID="numBz"><Font ss:FontName="Calibri" ss:Size="11" ss:Bold="1"/>${NUMFMT}${box}${ZEBRA}</Style>

  <Style ss:ID="totLbl"><Font ss:FontName="Calibri" ss:Size="11" ss:Bold="1" ss:Color="#1B4B7A"/><Interior ss:Color="#DCE6F1" ss:Pattern="Solid"/><Alignment ss:Horizontal="Left" ss:Vertical="Center"/><Borders>${B("Top", "2", "#1B4B7A")}${B("Bottom")}${B("Left")}${B("Right")}</Borders></Style>
  <Style ss:ID="totNum"><Font ss:FontName="Calibri" ss:Size="11" ss:Bold="1" ss:Color="#1B4B7A"/><Interior ss:Color="#DCE6F1" ss:Pattern="Solid"/>${NUMFMT}<Borders>${B("Top", "2", "#1B4B7A")}${B("Bottom")}${B("Left")}${B("Right")}</Borders></Style>

  <Style ss:ID="sumLbl"><Alignment ss:Horizontal="Left" ss:Vertical="Center"/></Style>
  <Style ss:ID="sumNum">${NUMFMT}</Style>
  <Style ss:ID="sumLblB"><Font ss:FontName="Calibri" ss:Size="11" ss:Bold="1" ss:Color="#1B4B7A"/><Alignment ss:Horizontal="Left" ss:Vertical="Center"/></Style>
  <Style ss:ID="sumNumB"><Font ss:FontName="Calibri" ss:Size="11" ss:Bold="1" ss:Color="#1B4B7A"/>${NUMFMT}</Style>
 </Styles>
 <Worksheet ss:Name="Jadval">
  <Table ss:DefaultRowHeight="18">
   <Column ss:Width="38"/><Column ss:Width="82"/><Column ss:Width="112"/>
   <Column ss:Width="126"/><Column ss:Width="126"/><Column ss:Width="126"/>
   <Column ss:Width="66"/>
   ${titleRow}${header}${body}${totals}${extra}
  </Table>
  <WorksheetOptions xmlns="urn:schemas-microsoft-com:office:excel">
   <PageSetup><Layout x:Orientation="Landscape"/><PageMargins x:Bottom="0.5" x:Left="0.4" x:Right="0.4" x:Top="0.5"/></PageSetup>
   <FitToPage/>
   <Print><FitWidth>1</FitWidth><FitHeight>0</FitHeight><ValidPrinterInfo/></Print>
   <FreezePanes/><FrozenNoSplit/>
   <SplitHorizontal>3</SplitHorizontal><TopRowBottomPane>3</TopRowBottomPane>
   <ActivePane>2</ActivePane>
  </WorksheetOptions>
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
