import { useState } from "react";
import type { Lang } from "../types/lang";

// Til holatini va tanlangan tildagi lug'atni qaytaradi — `const T = STR[lang]` takrorini yo'qotadi
export function useLang<T>(dict: Record<Lang, T>, initial: Lang = "uz") {
  const [lang, setLang] = useState<Lang>(initial);
  return { lang, setLang, t: dict[lang] };
}
