// Minimal .xlsx (OOXML) yozuvchi — yangi npm paketisiz.
//
// Nega o'z qo'limiz bilan: bank tarmog'idagi SSL/proxy tufayli yangi npm
// bog'liqlik Docker build'ni buzib qo'yishi mumkin. Avval SpreadsheetML (.xls)
// ishlatilgandi, lekin Windows/Excel uni "kengaytmaga mos kelmaydigan, xavfli
// fayl" deb ogohlantirardi — shuning uchun HAQIQIY .xlsx yasaymiz.
//
// .xlsx = ichida XML fayllar bo'lgan ZIP. ZIP'ni siqishsiz ("stored", method 0)
// yozamiz — Excel buni bemalol ochadi va bizga deflate kutubxonasi kerak emas.

export const xmlEsc = (s: string): string =>
  s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");

const CRC_TABLE = (() => {
  const t = new Uint32Array(256);
  for (let i = 0; i < 256; i++) {
    let c = i;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[i] = c >>> 0;
  }
  return t;
})();

const crc32 = (buf: Uint8Array): number => {
  let c = 0xffffffff;
  for (let i = 0; i < buf.length; i++) c = CRC_TABLE[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
};

export interface ZipFile {
  name: string;
  content: string;
}

/** Fayllarni siqishsiz ZIP'ga yig'adi (.xlsx aynan shunday ZIP). */
export function zipStore(files: ZipFile[], mimeType: string): Blob {
  const enc = new TextEncoder();
  const parts: Uint8Array[] = [];
  const central: Uint8Array[] = [];
  let offset = 0;

  for (const f of files) {
    const nameBytes = enc.encode(f.name);
    const data = enc.encode(f.content);
    const crc = crc32(data);

    const lh = new Uint8Array(30 + nameBytes.length);
    const dv = new DataView(lh.buffer);
    dv.setUint32(0, 0x04034b50, true); // local file header imzosi
    dv.setUint16(4, 20, true); // kerakli versiya
    dv.setUint16(6, 0x0800, true); // bayroq: nomlar UTF-8
    dv.setUint16(8, 0, true); // usul: 0 = stored (siqishsiz)
    dv.setUint16(10, 0, true); // vaqt
    dv.setUint16(12, 0x21, true); // sana: 1980-01-01 (fayl barqaror bo'lsin)
    dv.setUint32(14, crc, true);
    dv.setUint32(18, data.length, true); // siqilgan hajm
    dv.setUint32(22, data.length, true); // asl hajm
    dv.setUint16(26, nameBytes.length, true);
    dv.setUint16(28, 0, true); // extra
    lh.set(nameBytes, 30);
    parts.push(lh, data);

    const ch = new Uint8Array(46 + nameBytes.length);
    const cv = new DataView(ch.buffer);
    cv.setUint32(0, 0x02014b50, true); // central directory imzosi
    cv.setUint16(4, 20, true); // yasagan versiya
    cv.setUint16(6, 20, true); // kerakli versiya
    cv.setUint16(8, 0x0800, true);
    cv.setUint16(10, 0, true);
    cv.setUint16(12, 0, true);
    cv.setUint16(14, 0x21, true);
    cv.setUint32(16, crc, true);
    cv.setUint32(20, data.length, true);
    cv.setUint32(24, data.length, true);
    cv.setUint16(28, nameBytes.length, true);
    cv.setUint32(42, offset, true); // local header o'rni
    ch.set(nameBytes, 46);
    central.push(ch);

    offset += lh.length + data.length;
  }

  const centralSize = central.reduce((sum, c) => sum + c.length, 0);
  const eocd = new Uint8Array(22);
  const ev = new DataView(eocd.buffer);
  ev.setUint32(0, 0x06054b50, true); // end of central directory
  ev.setUint16(8, files.length, true);
  ev.setUint16(10, files.length, true);
  ev.setUint32(12, centralSize, true);
  ev.setUint32(16, offset, true);

  // Bo'laklarni bitta bufferga yig'amiz — Blob'ga aynan bitta (aniq tipdagi)
  // Uint8Array beriladi.
  const all = [...parts, ...central, eocd];
  const total = all.reduce((sum, c) => sum + c.length, 0);
  const out = new Uint8Array(total);
  let pos = 0;
  for (const chunk of all) {
    out.set(chunk, pos);
    pos += chunk.length;
  }
  return new Blob([out], { type: mimeType });
}

export const XLSX_MIME =
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

/** Bitta varaqli .xlsx paketi (Content_Types, rels, workbook, styles, sheet). */
export function packXlsx(sheetName: string, stylesXml: string, sheetXml: string): Blob {
  return zipStore(
    [
      {
        name: "[Content_Types].xml",
        content:
          '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
          '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">' +
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>' +
          '<Default Extension="xml" ContentType="application/xml"/>' +
          '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>' +
          '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>' +
          '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>' +
          "</Types>",
      },
      {
        name: "_rels/.rels",
        content:
          '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
          '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
          '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>' +
          "</Relationships>",
      },
      {
        name: "xl/workbook.xml",
        content:
          '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
          '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" ' +
          'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">' +
          `<sheets><sheet name="${xmlEsc(sheetName)}" sheetId="1" r:id="rId1"/></sheets>` +
          "</workbook>",
      },
      {
        name: "xl/_rels/workbook.xml.rels",
        content:
          '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' +
          '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
          '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>' +
          '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>' +
          "</Relationships>",
      },
      { name: "xl/styles.xml", content: stylesXml },
      { name: "xl/worksheets/sheet1.xml", content: sheetXml },
    ],
    XLSX_MIME
  );
}
