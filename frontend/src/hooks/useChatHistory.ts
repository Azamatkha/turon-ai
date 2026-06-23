import { useEffect, useRef, useState } from "react";
import type { Chat, Msg } from "../types/chat";
import { pickReply } from "../services/chatBotService";
import {
  listSessions, createSession, getSession, deleteSession, addMessage, renameSession,
} from "../services/chatHistoryService";

// Sanaga qarab sidebar guruhini aniqlaydi
function groupFor(iso: string): string {
  const day = 24 * 3600 * 1000;
  const now = new Date();
  const startToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const t = new Date(iso).getTime();
  if (t >= startToday) return "Today";
  if (t >= startToday - day) return "Yesterday";
  return "Previous 7 Days";
}

// Chat tarixini BACKEND (PostgreSQL) bilan boshqaradi — foydalanuvchiga bog'langan.
// useChatSimulation bilan bir xil interfeysni qaytaradi (ChatPage o'zgarmaydi).
export function useChatHistory() {
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pendingRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const loaded = useRef<Set<string>>(new Set());

  const [chats, setChats] = useState<Chat[]>([]);
  const [activeId, setActiveIdState] = useState("");
  const [draft, setDraft] = useState("");
  const [thinking, setThinking] = useState(false);
  const [generating, setGenerating] = useState(false);

  // Boshlang'ich yuklash: suhbatlar ro'yxati + birinchisining xabarlari
  useEffect(() => {
    (async () => {
      try {
        const sessions = await listSessions();
        const mapped: Chat[] = sessions.map((s) => ({
          id: s.id, group: groupFor(s.updated_at), title: s.title, messages: [],
        }));
        setChats(mapped);
        if (mapped.length) await openSession(mapped[0].id);
      } catch {
        /* backend tayyor emas — bo'sh holat */
      }
    })();
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (pendingRef.current) clearTimeout(pendingRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const openSession = async (id: string) => {
    setActiveIdState(id);
    if (loaded.current.has(id)) return;
    try {
      const detail = await getSession(id);
      const msgs: Msg[] = detail.messages.map((m) => ({ id: m.id, role: m.role, text: m.content, time: m.created_at }));
      setChats((cs) => cs.map((c) => (c.id === id ? { ...c, title: detail.title, messages: msgs } : c)));
      loaded.current.add(id);
    } catch {
      /* ignore */
    }
  };

  const setActiveId = (id: string) => { void openSession(id); };

  const setActiveMsgs = (id: string, updater: (m: Msg[]) => Msg[]) =>
    setChats((cs) => cs.map((c) => (c.id === id ? { ...c, messages: updater(c.messages) } : c)));

  const newChat = async () => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (pendingRef.current) clearTimeout(pendingRef.current);
    setThinking(false); setGenerating(false); setDraft("");
    try {
      const s = await createSession("");
      loaded.current.add(s.id);
      setChats((cs) => [{ id: s.id, group: "Today", title: "", messages: [] }, ...cs]);
      setActiveIdState(s.id);
    } catch { /* ignore */ }
  };

  const renameChat = async (id: string, title: string) => {
    const next = title.trim();
    if (!next) return;
    setChats((cs) => cs.map((c) => (c.id === id ? { ...c, title: next } : c)));
    try { await renameSession(id, next); } catch { /* ignore */ }
  };

  const removeChat = async (id: string) => {
    try { await deleteSession(id); } catch { /* ignore */ }
    setChats((cs) => {
      const next = cs.filter((c) => c.id !== id);
      if (id === activeId) setActiveIdState(next[0]?.id ?? "");
      return next;
    });
  };

  const respond = (sessionId: string, userText: string) => {
    const full = pickReply(userText);
    const tempId = "a" + Date.now();
    setThinking(false);
    setActiveMsgs(sessionId, (m) => [...m, { id: tempId, role: "assistant", text: "", time: new Date().toISOString() }]);
    const parts = full.split(/(\s+)/);
    let i = 0;
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      i++;
      const partial = parts.slice(0, i).join("");
      setActiveMsgs(sessionId, (m) => m.map((x) => (x.id === tempId ? { ...x, text: partial } : x)));
      if (i >= parts.length && timerRef.current) {
        clearInterval(timerRef.current);
        setGenerating(false);
        addMessage(sessionId, "assistant", full).catch(() => {});  // DB ga saqlash
      }
    }, 26);
  };

  const send = async (forced?: string) => {
    const text = (forced ?? draft).trim();
    if (!text || generating) return;

    // Faol suhbat bo'lmasa — yangi yaratamiz
    let sessionId = activeId;
    if (!sessionId) {
      try {
        const s = await createSession("");
        loaded.current.add(s.id);
        setChats((cs) => [{ id: s.id, group: "Today", title: "", messages: [] }, ...cs]);
        setActiveIdState(s.id);
        sessionId = s.id;
      } catch { return; }
    }

    const um: Msg = { id: "u" + Date.now(), role: "user", text, time: new Date().toISOString() };
    setChats((cs) => cs.map((c) => {
      if (c.id !== sessionId) return c;
      const title = c.messages.length === 0 ? text.slice(0, 42) : c.title;
      return { ...c, title, messages: [...c.messages, um] };
    }));
    setDraft("");
    setThinking(true);
    setGenerating(true);
    addMessage(sessionId, "user", text).catch(() => {});  // DB ga saqlash
    pendingRef.current = setTimeout(() => respond(sessionId, text), 750);
  };

  const stop = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (pendingRef.current) clearTimeout(pendingRef.current);
    setThinking(false); setGenerating(false);
  };

  const regenerate = () => {
    if (generating || !activeId) return;
    const msgs = chats.find((c) => c.id === activeId)?.messages || [];
    let lastUser = "";
    for (let i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].role === "user") { lastUser = msgs[i].text; break; }
    }
    if (!lastUser) return;
    setActiveMsgs(activeId, (m) => {
      const copy = [...m];
      while (copy.length && copy[copy.length - 1].role === "assistant") copy.pop();
      return copy;
    });
    setThinking(true); setGenerating(true);
    pendingRef.current = setTimeout(() => respond(activeId, lastUser), 600);
  };

  const active = chats.find((c) => c.id === activeId) || { messages: [] as Msg[], title: "" };
  const rawMsgs = active.messages || [];
  const isEmpty = rawMsgs.length === 0 && !thinking;
  const hasMessages = rawMsgs.length > 0 || thinking;
  const canSend = draft.trim().length > 0 && !generating;

  return {
    chats, activeId, setActiveId, active, rawMsgs, isEmpty, hasMessages, canSend,
    draft, setDraft, thinking, generating, newChat, removeChat, renameChat, send, stop, regenerate,
  };
}
