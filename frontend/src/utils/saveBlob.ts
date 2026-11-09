// Brauzerda faylni yuklab olish (Blob -> vaqtinchalik havola -> bosish)
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  // Ba'zi brauzerlar yuklashni keyinroq boshlaydi — havolani darhol o'chirmaymiz
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

// Content-Disposition'dan fayl nomi: avval filename* (UTF-8), keyin filename
export function filenameFromDisposition(header: string | null, fallback: string): string {
  if (!header) return fallback;
  const star = /filename\*=UTF-8''([^;]+)/i.exec(header);
  if (star) {
    try {
      return decodeURIComponent(star[1]);
    } catch {
      /* noto'g'ri kodlangan — oddiy nomga o'tamiz */
    }
  }
  const plain = /filename="?([^";]+)"?/i.exec(header);
  return plain ? plain[1] : fallback;
}
