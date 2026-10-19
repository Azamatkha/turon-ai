import { createContext, useContext, useLayoutEffect, useState, ReactNode } from "react";

export type Theme = "light" | "dark";

const STORAGE_KEY = "turon-theme";

interface ThemeContextValue {
  theme: Theme;
  toggleTheme: () => void;
  /** Kirish sahifasi ochiq rejimni majburlaydi (qara: useForceLightTheme) */
  setForceLight: (force: boolean) => void;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

// Saytning umumiy mavzusi (light/dark). localStorage'da saqlanadi, shuning uchun
// sahifa yangilansa ham yoki Chat -> Admin -> Chat o'tilsa ham tanlov yo'qolmaydi.
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved === "dark" || saved === "light" ? saved : "light";
  });
  const [forceLight, setForceLight] = useState(false);

  // <html> klassi YAGONA joyda — shu yerda qo'yiladi: majburlov bo'lsa "light",
  // aks holda foydalanuvchi tanlovi. Saqlanadigan tanlov esa majburlovdan
  // qat'i nazar `theme` bo'lib qoladi.
  //
  // ILGARI login sahifasi klassni o'zi olib tashlardi. Sahifa NOLDAN yuklanganda
  // (masalan logout'dan keyin) uning effekti providernikidan OLDIN ishlardi:
  // o'sha paytda "dark" hali qo'yilmagan bo'lardi, keyin provider uni qo'yib
  // yuborardi — login inputlari va til tanlagich qorayib qolardi.
  // useLayoutEffect — sahifa chizilishidan oldin, aks holda bir lahza qora
  // ko'rinish "miltillab" o'tardi.
  useLayoutEffect(() => {
    const applied: Theme = forceLight ? "light" : theme;
    document.documentElement.classList.remove("light", "dark");
    document.documentElement.classList.add(applied);
  }, [theme, forceLight]);

  useLayoutEffect(() => {
    localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  const toggleTheme = () => setTheme((prev) => (prev === "light" ? "dark" : "light"));

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, setForceLight }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme — ThemeProvider ichida ishlatilishi kerak");
  return ctx;
}
