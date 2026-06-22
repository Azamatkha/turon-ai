import { createContext, useContext, useEffect, useState, ReactNode } from "react";

export type Theme = "light" | "dark";

const STORAGE_KEY = "turon-theme";

interface ThemeContextValue {
  theme: Theme;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

// Saytning umumiy mavzusi (light/dark). localStorage'da saqlanadi, shuning uchun
// sahifa yangilansa ham yoki Chat -> Admin -> Chat o'tilsa ham tanlov yo'qolmaydi.
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved === "dark" || saved === "light" ? saved : "light";
  });

  // Mavzu o'zgarganda <html> elementiga klass qo'shamiz (kelajakda global
  // CSS o'zgaruvchilari uchun) va tanlovni saqlaymiz
  useEffect(() => {
    document.documentElement.classList.remove("light", "dark");
    document.documentElement.classList.add(theme);
    localStorage.setItem(STORAGE_KEY, theme);
  }, [theme]);

  const toggleTheme = () => setTheme((prev) => (prev === "light" ? "dark" : "light"));

  return <ThemeContext.Provider value={{ theme, toggleTheme }}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme — ThemeProvider ichida ishlatilishi kerak");
  return ctx;
}
