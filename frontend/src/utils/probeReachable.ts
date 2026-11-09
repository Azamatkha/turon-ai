// Tashqi sayt shu kompyuterdan ochiladimi — yashirin rasm yuklab tekshiriladi.
// Rasm CORS'ga tushmaydi: yuklansa — sayt ochiq, xato/timeout — bloklangan.
// (Bank ichki tarmog'ida t.me sahifasi ochilsa ham telegram.org resurslari
// bloklangan bo'ladi — sahifa "yalang'och" chiqadi. Shuning uchun aynan resurs tekshiriladi.)
export function probeReachable(imageUrl: string, timeoutMs = 3000): Promise<boolean> {
  return new Promise((resolve) => {
    const img = new Image();
    let done = false;
    const finish = (ok: boolean) => {
      if (done) return;
      done = true;
      window.clearTimeout(timer);
      img.onload = img.onerror = null;
      resolve(ok);
    };
    const timer = window.setTimeout(() => finish(false), timeoutMs);
    img.onload = () => finish(true);
    img.onerror = () => finish(false);
    // Kesh aldamasin — har safar haqiqiy so'rov
    img.src = `${imageUrl}${imageUrl.includes("?") ? "&" : "?"}_=${Date.now()}`;
  });
}

// Telegram resurslari ochiladimi (t.me sahifasining logotipi)
export const TELEGRAM_PROBE_URL = "https://telegram.org/img/t_logo.png";
