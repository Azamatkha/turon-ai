import { useEffect, useState } from "react";

// CSS media-so'rovini React holatiga bog'laydi (masalan, mobil ekranni aniqlash).
// SSR yo'q, shuning uchun boshlang'ich qiymat darhol matchMedia'dan olinadi.
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => window.matchMedia(query).matches);

  useEffect(() => {
    const mql = window.matchMedia(query);
    const onChange = (e: MediaQueryListEvent) => setMatches(e.matches);
    mql.addEventListener("change", onChange);
    setMatches(mql.matches);
    return () => mql.removeEventListener("change", onChange);
  }, [query]);

  return matches;
}

// Umumiy breakpoint: telefon/kichik planshet
export function useIsMobile(): boolean {
  return useMediaQuery("(max-width: 768px)");
}
