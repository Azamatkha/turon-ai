import { useState } from "react";
import type { Lang } from "../types/lang";

const STORAGE_KEY = "turon-lang";

function isLang(v: string | null): v is Lang {
  return v === "uz" || v === "uz_cyrl" || v === "ru";
}

// Til holatini va tanlangan tildagi lug'atni qaytaradi — `const T = STR[lang]` takrorini yo'qotadi.
// Tanlov localStorage'da saqlanadi (ThemeContext'dagi kabi), shuning uchun Login'da tanlangan
// til Chat/Admin sahifalariga o'tganda ham (yangi useLang chaqiruvi bo'lsa ham) yo'qolmaydi.
export function useLang<T>(dict: Record<Lang, T>, initial: Lang = "uz") {
  const [lang, setLangState] = useState<Lang>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return isLang(saved) ? saved : initial;
  });

  const setLang = (v: Lang) => {
    setLangState(v);
    localStorage.setItem(STORAGE_KEY, v);
  };

  return { lang, setLang, t: dict[lang] };
}
