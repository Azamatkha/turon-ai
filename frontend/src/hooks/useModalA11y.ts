import { useEffect, useRef } from "react";

// Modal oynalar uchun umumiy klaviatura xulqi (WCAG 2.1.2, 2.4.3):
//  - Esc — oynani yopadi (yoki `onEscape` nima qilsa, o'shani);
//  - Tab / Shift+Tab — fokus oyna ICHIDA aylanadi, orqadagi sahifaga chiqmaydi;
//  - ochilganda fokus oynaga o'tadi, yopilganda uni ochgan tugmaga qaytadi.
//
// Ishlatish: `const ref = useModalA11y<HTMLDivElement>(onClose);` va shu ref'ni
// oynaning ICHKI paneliga (qorong'i fonga emas) beriladi.

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), ' +
  'select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

// Ochiq oynalar steki: oyna ustiga oyna ochilganda (Kalkulyator -> To'lov
// jadvali) Esc va Tab faqat ENG USTKI oynaga tegishi kerak.
const stack: symbol[] = [];

// Hozir birorta modal ochiqmi — sahifa darajasidagi Esc ishlovchilari uchun
export const isAnyModalOpen = () => stack.length > 0;

function visibleFocusable(root: HTMLElement): HTMLElement[] {
  return Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
    (el) => el.getClientRects().length > 0,
  );
}

export function useModalA11y<T extends HTMLElement>(onEscape: () => void, active: boolean = true) {
  const ref = useRef<T>(null);
  // Har renderda yangi funksiya kelsa ham effekt qayta ishga tushmasin
  const onEscapeRef = useRef(onEscape);
  onEscapeRef.current = onEscape;

  useEffect(() => {
    if (!active) return;
    const el = ref.current;
    if (!el) return;

    const id = Symbol("modal");
    stack.push(id);
    const isTop = () => stack[stack.length - 1] === id;
    const opener = document.activeElement as HTMLElement | null;

    // Boshlang'ich fokus: komponent o'zi qo'ymagan bo'lsa — birinchi kiritish
    // maydoni (faqat sichqonchali qurilmada: telefonda bu klaviaturani ochib
    // yuborardi), u bo'lmasa oynaning o'zi.
    if (!el.contains(document.activeElement)) {
      const finePointer = window.matchMedia("(hover: hover) and (pointer: fine)").matches;
      const field = finePointer
        ? visibleFocusable(el).find((n) => n.matches("[data-autofocus], input, textarea"))
        : undefined;
      if (field) {
        field.focus();
      } else {
        if (!el.hasAttribute("tabindex")) el.tabIndex = -1;
        // Oynaning o'ziga halqa chizilmasin — u faqat fokus "langari"
        el.style.outline = "none";
        el.focus();
      }
    }

    const onKey = (e: KeyboardEvent) => {
      if (!isTop()) return;

      if (e.key === "Escape") {
        // Oyna ichida ochiq dropdown bo'lsa, Esc avval UNI yopadi (o'zining
        // ishlovchisi bilan) — oyna ochiq qoladi.
        if (el.querySelector('[aria-haspopup][aria-expanded="true"]')) return;
        e.stopPropagation();
        onEscapeRef.current();
        return;
      }

      if (e.key !== "Tab") return;
      const items = visibleFocusable(el);
      if (items.length === 0) {
        e.preventDefault();
        return;
      }
      const first = items[0];
      const last = items[items.length - 1];
      const current = document.activeElement as HTMLElement | null;
      // Fokus oynadan tashqarida (yoki oynaning o'zida) bo'lsa — ichkariga qaytaramiz
      if (!current || !el.contains(current) || current === el) {
        e.preventDefault();
        (e.shiftKey ? last : first).focus();
      } else if (e.shiftKey && current === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && current === last) {
        e.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      const i = stack.indexOf(id);
      if (i !== -1) stack.splice(i, 1);
      // Fokusni oynani ochgan elementga qaytaramiz (u hali sahifada bo'lsa)
      if (opener && document.contains(opener)) opener.focus();
    };
  }, [active]);

  return ref;
}
