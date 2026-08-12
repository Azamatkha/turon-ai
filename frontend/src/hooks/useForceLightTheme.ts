import { useLayoutEffect } from "react";

/**
 * Kirish / ro'yxatdan o'tish sahifalarini majburan OCHIQ (light) rejimda
 * ko'rsatadi.
 *
 * Muammo: mavzu `html` elementiga `dark` klassi bilan qo'yiladi va u
 * localStorage'da saqlanadi. Foydalanuvchi chatda tungi rejimga o'tib, keyin
 * tizimdan chiqsa, klass saqlanib qolardi — login formasi esa faqat ochiq
 * ko'rinishda chizilgan (unda mavzu almashtirgich ham yo'q). Natijada global
 * dark qoidalari input fonini qoraytirib, yozuv va placeholder o'qilmas
 * bo'lib qolardi.
 *
 * Sahifa ochilganda klassni vaqtincha olib turamiz va chiqishda AYNAN
 * joyiga qaytaramiz — foydalanuvchining tanlovi yo'qolmaydi, qayta
 * kirganda chat yana tungi rejimda ochiladi.
 */
export function useForceLightTheme(): void {
  useLayoutEffect(() => {
    const el = document.documentElement;
    if (!el.classList.contains("dark")) return;
    el.classList.remove("dark");
    el.classList.add("light");
    return () => {
      el.classList.remove("light");
      el.classList.add("dark");
    };
  }, []);
}
