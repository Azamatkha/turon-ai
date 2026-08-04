import { useCallback, useEffect, useRef, useState } from "react";
import {
  getUnreadCount,
  listNotifications,
  markAllRead as apiMarkAllRead,
  markRead as apiMarkRead,
  streamNotifications,
  type ApiNotification,
} from "../services/notificationService";

// Asosiy yetkazish — SSE oqimi (kechikish deyarli nolga teng). Polling faqat
// zaxira: oqim uzilsa yoki proxy uni o'tkazmasa badge baribir yangilanadi.
// Brauzer fondagi tabda taymerni sekinlashtiradi, shuning uchun polling'ga
// tayanib bo'lmaydi — interval ataylab uzun qilingan.
const POLL_MS = 60_000;
// Oqim uzilganda qayta ulanishgacha kutish
const RECONNECT_MS = 5_000;

// Brauzer (OS) bildirishnomasi ikki marta chiqmasligi uchun ko'rsatilganlar
// id'si saqlanadi. Ro'yxat cheksiz o'smasin — oxirgi SEEN_MAX tasi qoladi.
const SEEN_KEY = "turon_notif_seen";
const SEEN_MAX = 200;

function loadSeen(): string[] {
  try {
    const raw = localStorage.getItem(SEEN_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed.filter((x) => typeof x === "string") : [];
  } catch {
    return [];
  }
}

function saveSeen(ids: string[]): string[] {
  const trimmed = ids.slice(-SEEN_MAX);
  try {
    localStorage.setItem(SEEN_KEY, JSON.stringify(trimmed));
  } catch {
    // localStorage to'lgan bo'lsa ham ish to'xtamasin
  }
  return trimmed;
}

// Brauzer bildirishnomasi qo'llab-quvvatlanadimi (eski brauzer yoki http:// da yo'q)
export function desktopSupported(): boolean {
  return typeof window !== "undefined" && "Notification" in window;
}

export function desktopPermission(): NotificationPermission | "unsupported" {
  return desktopSupported() ? Notification.permission : "unsupported";
}

export interface DesktopText {
  title: string;
  body: string;
}

/** Bildirishnomalar holati: badge soni, ro'yxat va OS popup'lari.
 *
 * `format` — bildirishnomani foydalanuvchi tilidagi matnga o'giradi
 * (matn bazada saqlanmaydi, faqat type + params keladi). */
export function useNotifications(format: (n: ApiNotification) => DesktopText) {
  const [unread, setUnread] = useState(0);
  const [items, setItems] = useState<ApiNotification[]>([]);
  const [loading, setLoading] = useState(false);

  // format har renderda yangi funksiya bo'ladi — effektni qayta ishga
  // tushirmasligi uchun ref orqali o'qiymiz.
  const formatRef = useRef(format);
  formatRef.current = format;

  const seenRef = useRef<string[]>(loadSeen());
  const lastCountRef = useRef(-1);

  // ---- OS (ekran burchagi) bildirishnomasi ----
  const pushDesktop = useCallback(async () => {
    if (!desktopSupported() || Notification.permission !== "granted") return;
    // Faqat foydalanuvchi shu sahifada TURGANDA popup kerak emas.
    // `visibilityState` yetarli emas: boshqa dasturga o'tilganda ham tab
    // ko'pincha "visible" bo'lib qolaveradi — shuning uchun fokus ham
    // tekshiriladi, aks holda YouTube'dagi kabi popup hech qachon chiqmasdi.
    if (document.visibilityState === "visible" && document.hasFocus()) return;

    let fresh: ApiNotification[] = [];
    try {
      const data = await listNotifications({ limit: 10, onlyUnread: true });
      fresh = data.items;
    } catch {
      return;
    }

    const seen = new Set(seenRef.current);
    // Eskisidan yangisiga — popup'lar to'g'ri tartibda chiqsin
    for (const n of [...fresh].reverse()) {
      if (seen.has(n.id)) continue;
      seen.add(n.id);
      const { title, body } = formatRef.current(n);
      const notif = new Notification(title, { body, tag: n.id });
      notif.onclick = () => {
        window.focus();
        notif.close();
      };
    }
    seenRef.current = saveSeen([...seen]);
  }, []);

  // O'qilmaganlar sonini yangilaydi va kerak bo'lsa OS popup'ini chiqaradi
  const syncCount = useCallback(async () => {
    let count: number;
    try {
      count = await getUnreadCount();
    } catch {
      // Tarmoq uzilishi badge'ni yo'qotmasin — jim o'tkazamiz
      return;
    }
    setUnread(count);
    // Soni oshgan bo'lsa — yangi bildirishnoma kelgan
    if (count > 0 && count !== lastCountRef.current) void pushDesktop();
    lastCountRef.current = count;
  }, [pushDesktop]);

  // ---- Real vaqtdagi oqim (asosiy yetkazish yo'li) ----
  useEffect(() => {
    let alive = true;
    let controller: AbortController | null = null;
    let retryTimer: number | null = null;

    const connect = async () => {
      if (!alive) return;
      controller = new AbortController();
      try {
        await streamNotifications(() => void syncCount(), controller.signal);
      } catch {
        // Ulanish uzildi yoki ochilmadi — pastda qayta urinamiz
      }
      if (!alive) return;
      // Uzilgan bo'lsa qayta ulanamiz; shu orada polling zaxira bo'lib turadi
      retryTimer = window.setTimeout(connect, RECONNECT_MS);
    };

    void connect();
    return () => {
      alive = false;
      controller?.abort();
      if (retryTimer !== null) clearTimeout(retryTimer);
    };
  }, [syncCount]);

  // ---- Polling (zaxira) ----
  // Oqim uzilib qolsa yoki proxy uni bloklasa ham badge yangilanib tursin.
  useEffect(() => {
    void syncCount();
    const id = setInterval(() => void syncCount(), POLL_MS);
    // Boshqa tabdan qaytganda darhol yangilanadi
    const onVisible = () => {
      if (document.visibilityState === "visible") void syncCount();
    };
    document.addEventListener("visibilitychange", onVisible);

    return () => {
      clearInterval(id);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [syncCount]);

  // ---- Ro'yxat ----
  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listNotifications({ limit: 30 });
      setItems(data.items);
      setUnread(data.unread_count);
      lastCountRef.current = data.unread_count;
    } catch {
      // Panelda bo'sh ro'yxat ko'rinadi — alohida xato bloki shart emas
    } finally {
      setLoading(false);
    }
  }, []);

  const markRead = useCallback(async (id: string) => {
    setItems((prev) =>
      prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
    );
    setUnread((c) => Math.max(0, c - 1));
    try {
      await apiMarkRead(id);
    } catch {
      void refresh();
    }
  }, [refresh]);

  const markAllRead = useCallback(async () => {
    setItems((prev) => prev.map((n) => ({ ...n, is_read: true })));
    setUnread(0);
    lastCountRef.current = 0;
    try {
      await apiMarkAllRead();
    } catch {
      void refresh();
    }
  }, [refresh]);

  /** Brauzer ruxsatini so'raydi. Faqat foydalanuvchi tugmani bosganda
   * chaqiriladi — sahifa ochilganda so'rash yaxshi amaliyot emas. */
  const requestDesktop = useCallback(async (): Promise<NotificationPermission | "unsupported"> => {
    if (!desktopSupported()) return "unsupported";
    const result = await Notification.requestPermission();
    if (result === "granted") {
      // Ruxsat endi berildi — hozirgi o'qilmaganlar "ko'rilgan" deb
      // belgilanadi, aks holda eski xabarlar birdan popup bo'lib chiqadi.
      try {
        const data = await listNotifications({ limit: 30, onlyUnread: true });
        seenRef.current = saveSeen([
          ...seenRef.current,
          ...data.items.map((n) => n.id),
        ]);
      } catch {
        // ruxsat baribir berildi — keyingi bildirishnomalar ishlayveradi
      }
    }
    return result;
  }, []);

  /** Sinov popup'i — ruxsat berilgan bo'lsa ham OS (Windows) darajasida
   *  bloklangan bo'lishi mumkin. Shu tugma orqali darhol tekshirib ko'riladi. */
  const testDesktop = useCallback((title: string, body: string): boolean => {
    if (!desktopSupported() || Notification.permission !== "granted") return false;
    try {
      new Notification(title, { body, tag: "turon-test" });
      return true;
    } catch {
      return false;
    }
  }, []);

  return {
    unread,
    items,
    loading,
    refresh,
    markRead,
    markAllRead,
    requestDesktop,
    testDesktop,
  };
}
