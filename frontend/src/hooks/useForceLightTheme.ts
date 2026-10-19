import { useLayoutEffect } from "react";
import { useTheme } from "../contexts/ThemeContext";

/**
 * Kirish / ro'yxatdan o'tish sahifalarini majburan OCHIQ (light) rejimda
 * ko'rsatadi.
 *
 * Muammo: mavzu `html` elementiga `dark` klassi bilan qo'yiladi va u
 * localStorage'da saqlanadi. Foydalanuvchi chatda tungi rejimga o'tib, keyin
 * tizimdan chiqsa, login formasi (u faqat ochiq ko'rinishda chizilgan, mavzu
 * almashtirgichi ham yo'q) qorong'i bo'lib, yozuv o'qilmas bo'lib qolardi.
 *
 * Klassga bu yerdan TEGILMAYDI — ThemeProvider'ga majburlov aytiladi, klassni
 * u qo'yadi (qara: ThemeContext). Sahifadan chiqilganda majburlov olinadi va
 * foydalanuvchining tanlovi (masalan tungi rejim) o'z-o'zidan qaytadi.
 */
export function useForceLightTheme(): void {
  const { setForceLight } = useTheme();
  useLayoutEffect(() => {
    setForceLight(true);
    return () => setForceLight(false);
  }, [setForceLight]);
}
