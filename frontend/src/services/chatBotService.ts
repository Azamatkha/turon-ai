// Bot javobini (simulyatsiya) tanlash
export function pickReply(t: string): string {
  const s = t.toLowerCase();
  if (/^(hi|hello|hey|salom|assalom)/.test(s))
    return "Salom! Men Turon AI — yordam berishdan xursandman. Biror narsani tushuntirish, matn yozish, reja tuzish yoki kod ustida ishlashni so‘rashingiz mumkin. Nima haqida gaplashamiz?";
  if (/\b(code|bug|python|javascript|error|function|kod|xato)\b/.test(s))
    return "Keling, birga ko‘rib chiqamiz. Kod parchasini va kutilgan natija bilan haqiqiy natijani yuboring — men muammoni bosqichма-bosqич topaman.";
  if (/\b(plan|strategy|marketing|roadmap|reja|strategiya)\b/.test(s))
    return "Mana toza tuzilma:\n\n1. Maqsad — choraklik bitta o‘lchanadigan maqsad.\n2. Auditoriya — kimga yetkazasiz va qaysi fikr ularni harakatga keltiradi.\n3. Kanallar — beshtani yarim qilgandan ko‘ra ikkitasini yaxshi qiling.\n4. Kalendar — muhim sanalar.\n5. Metrikalar — har hafta nimani tekshirasiz.\n\nBirortasini to‘liq yozib berayinmi?";
  if (/\b(explain|how|what|why|tushuntir|qanday|nima|nega)\b/.test(s))
    return "Yaxshi savol. Qisqasi: bu murakkab munosabatni bir nechta sodda, takrorlanadigan qoidaga aylantirishdir. Avval intuitsiyani, keyin aniq mexanikani beray — qay darajada chuqur tushuntirishni ayting.";
  return "Tushundim. Men bunday yondashardim: avval istagan natijani aniqlang, uni eng muhim ikki-uch qarorga bo‘ling, qolganini tafsilot sifatida hal qiling. Cheklovlaringizni ayting — aniqroq qilaman.";
}
