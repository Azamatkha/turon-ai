import { useEffect, useRef, useState } from "react";
import type { Chat, Msg } from "../types/chat";
import { pickReply } from "../services/chatBotService";
import { seedChats } from "../services/seedData";

// Suhbatlar ro'yxati, faol suhbat va bot javobini (simulyatsiya) "yozish" effekti bilan boshqaradi
export function useChatSimulation() {
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // Javob boshlanishidan oldingi qisqa kutish (setTimeout) — to'xtatishda bekor qilish uchun
  const pendingRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [activeId, setActiveId] = useState("c1");
  const [chats, setChats] = useState<Chat[]>(seedChats);
  const [draft, setDraft] = useState("");
  const [thinking, setThinking] = useState(false);
  // `generating` — javob boshlanishidan to yozib bo'lgunigacha bo'lgan butun davr
  // (thinking faqat matn paydo bo'lguncha bo'lgan qisqa kutish bosqichi)
  const [generating, setGenerating] = useState(false);

  // Komponent yopilganda taymerlarni tozalash
  useEffect(() => () => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (pendingRef.current) clearTimeout(pendingRef.current);
  }, []);

  const setActiveMsgs = (updater: (m: Msg[]) => Msg[]) =>
    setChats((cs) => cs.map((c) => (c.id === activeId ? { ...c, messages: updater(c.messages) } : c)));

  const newChat = () => {
    const id = "c" + Date.now();
    setChats((cs) => [{ id, group: "Today", title: "", messages: [] }, ...cs]);
    setActiveId(id);
    setDraft("");
    setThinking(false);
    setGenerating(false);
    if (timerRef.current) clearInterval(timerRef.current);
    if (pendingRef.current) clearTimeout(pendingRef.current);
  };

  // Tarixdan suhbatni o'chiradi. O'chirilgan suhbat faol bo'lsa, ro'yxatdagi
  // birinchi qolgan suhbatga o'tamiz (yo'q bo'lsa — yangi bo'sh suhbat ochamiz).
  const removeChat = (id: string) => {
    setChats((cs) => {
      const next = cs.filter((c) => c.id !== id);
      if (id === activeId) {
        if (next.length > 0) {
          setActiveId(next[0].id);
        } else {
          const freshId = "c" + Date.now();
          setActiveId(freshId);
          return [{ id: freshId, group: "Today", title: "", messages: [] }];
        }
      }
      return next;
    });
  };

  const respond = (userText: string) => {
    const full = pickReply(userText);
    const id = "a" + Date.now();
    setThinking(false);
    setActiveMsgs((m) => [...m, { id, role: "assistant", text: "" }]);
    const parts = full.split(/(\s+)/);
    let i = 0;
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      i++;
      const partial = parts.slice(0, i).join("");
      setActiveMsgs((m) => m.map((x) => (x.id === id ? { ...x, text: partial } : x)));
      if (i >= parts.length && timerRef.current) {
        clearInterval(timerRef.current);
        setGenerating(false);
      }
    }, 26);
  };

  const send = (forced?: string) => {
    const text = (forced ?? draft).trim();
    if (!text || generating) return;
    const um: Msg = { id: "u" + Date.now(), role: "user", text };
    setChats((cs) =>
      cs.map((c) => {
        if (c.id !== activeId) return c;
        const title = c.messages.length === 0 ? text.slice(0, 42) : c.title;
        return { ...c, title, messages: [...c.messages, um] };
      })
    );
    setDraft("");
    setThinking(true);
    setGenerating(true);
    pendingRef.current = setTimeout(() => respond(text), 750);
  };

  // Javob yozilishini to'xtatadi — yozilgan qismi qoladi
  const stop = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (pendingRef.current) clearTimeout(pendingRef.current);
    setThinking(false);
    setGenerating(false);
  };

  // Oxirgi foydalanuvchi savoliga botning javobini qaytadan yaratadi
  const regenerate = () => {
    if (generating) return;
    const msgs = chats.find((c) => c.id === activeId)?.messages || [];
    let lastUser = "";
    for (let i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].role === "user") { lastUser = msgs[i].text; break; }
    }
    if (!lastUser) return;
    // Oxirgi foydalanuvchi savolidan keyingi bot javob(lar)ini olib tashlaymiz
    setActiveMsgs((m) => {
      const copy = [...m];
      while (copy.length && copy[copy.length - 1].role === "assistant") copy.pop();
      return copy;
    });
    setThinking(true);
    setGenerating(true);
    pendingRef.current = setTimeout(() => respond(lastUser), 600);
  };

  const active = chats.find((c) => c.id === activeId) || { messages: [] as Msg[], title: "" };
  const rawMsgs = active.messages || [];
  const isEmpty = rawMsgs.length === 0 && !thinking;
  const hasMessages = rawMsgs.length > 0 || thinking;
  const canSend = draft.trim().length > 0 && !generating;

  return {
    chats,
    activeId,
    setActiveId,
    active,
    rawMsgs,
    isEmpty,
    hasMessages,
    canSend,
    draft,
    setDraft,
    thinking,
    generating,
    newChat,
    removeChat,
    send,
    stop,
    regenerate,
  };
}
