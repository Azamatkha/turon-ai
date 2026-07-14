import { useEffect, useRef, useState } from "react";
import type { Chat, Msg } from "../types/chat";
import { askReply } from "../services/chatBotService";
import {
  listSessions, createSession, getSession, deleteSession, addMessage, deleteMessage, renameSession, voteMessage, generateTitle, pinSession,
} from "../services/chatHistoryService";

// Vaqtinchalik (hali backend'ga saqlanmagan) xabar ID'lari "a"/"u" + timestamp
// ko'rinishida (tire yo'q). Backend'dagi haqiqiy ID — UUID (tire bor).
const isPersistedId = (id: string) => id.includes("-");

// Chat tarixini BACKEND (PostgreSQL) bilan boshqaradi — foydalanuvchiga bog'langan.
// useChatSimulation bilan bir xil interfeysni qaytaradi (ChatPage o'zgarmaydi).
export function useChatHistory(newChatLabel: string = "Yangi suhbat") {
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
          id: s.id, title: s.title, pinned: s.is_pinned, lastMessageAt: s.updated_at, messages: [],
        }));
        setChats(mapped);
        // Login'da avtomatik ochmaymiz — bo'sh (yangi) chat ko'rinadi, user o'zi tanlaydi
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
      const msgs: Msg[] = detail.messages.map((m) => ({ id: m.id, role: m.role, text: m.content, time: m.created_at, vote: m.vote ?? null }));
      // upsert: ro'yxatda bo'lsa yangilaymiz, bo'lmasa (to'g'ridan-to'g'ri link/refresh
      // — ro'yxat hali yuklanmagan) qo'shamiz
      setChats((cs) =>
        cs.some((c) => c.id === id)
          ? cs.map((c) => (c.id === id ? { ...c, title: detail.title, messages: msgs } : c))
          : [{ id, title: detail.title, pinned: detail.is_pinned, lastMessageAt: detail.updated_at, messages: msgs }, ...cs]
      );
      loaded.current.add(id);
    } catch {
      /* ignore */
    }
  };

  const setActiveId = (id: string) => { void openSession(id); };

  const setActiveMsgs = (id: string, updater: (m: Msg[]) => Msg[]) =>
    setChats((cs) => cs.map((c) => (c.id === id ? { ...c, messages: updater(c.messages) } : c)));

  // Backend sessiyasini HOZIR yaratmaymiz — bo'sh chat tarixga tushib qolmasligi
  // uchun. Sessiya faqat birinchi xabar yuborilganda (send() ichida) yaratiladi.
  const newChat = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (pendingRef.current) clearTimeout(pendingRef.current);
    setThinking(false); setGenerating(false); setDraft("");
    setActiveIdState("");
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

  // Pin/unpin — mahalliy holatni darhol yangilaymiz (optimistic), xato bo'lsa qaytaramiz
  const togglePin = async (id: string) => {
    const chat = chats.find((c) => c.id === id);
    if (!chat) return;
    const next = !chat.pinned;
    setChats((cs) => cs.map((c) => (c.id === id ? { ...c, pinned: next } : c)));
    try {
      await pinSession(id, next);
    } catch {
      setChats((cs) => cs.map((c) => (c.id === id ? { ...c, pinned: !next } : c)));
    }
  };

  const respond = async (
    sessionId: string,
    userText: string,
    history: { role: string; content: string }[] = []
  ) => {
    // Backend RAG endpointidan haqiqiy javobni olamiz (Qdrant qidiruv + Qwen + history)
    const res = await askReply(userText, history);
    const full = res.text;
    const totalTokens = res.completionTokens;
    const tempId = "a" + Date.now();
    setThinking(false);
    // Boshida completionTokens = 0 — matn yozilishi bilan real vaqt oshib boradi
    setActiveMsgs(sessionId, (m) => [
      ...m,
      {
        id: tempId,
        role: "assistant",
        text: "",
        time: new Date().toISOString(),
        debug: { finishReason: res.finishReason, completionTokens: 0, maxTokens: res.maxTokens },
      },
    ]);
    const parts = full.split(/(\s+)/);
    let i = 0;
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      i++;
      const partial = parts.slice(0, i).join("");
      // Yozilgan ulushga mutanosib token soni — oxirgi qadamda aniq totalTokens'ga tushadi
      const liveTokens = Math.round((totalTokens * Math.min(i, parts.length)) / parts.length);
      setActiveMsgs(sessionId, (m) =>
        m.map((x) =>
          x.id === tempId
            ? { ...x, text: partial, debug: x.debug ? { ...x.debug, completionTokens: liveTokens } : x.debug }
            : x
        )
      );
      if (i >= parts.length && timerRef.current) {
        clearInterval(timerRef.current);
        setGenerating(false);
        // DB ga saqlaymiz va vaqtinchalik id'ni haqiqiy DB id'ga almashtiramiz (like/dislike uchun)
        addMessage(sessionId, "assistant", full)
          .then((saved) =>
            setActiveMsgs(sessionId, (m) => m.map((x) => (x.id === tempId ? { ...x, id: saved.id } : x)))
          )
          .catch(() => {});
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
        const s = await createSession(newChatLabel);
        loaded.current.add(s.id);
        setChats((cs) => [{ id: s.id, title: newChatLabel, pinned: false, lastMessageAt: s.updated_at, messages: [] }, ...cs]);
        setActiveIdState(s.id);
        sessionId = s.id;
      } catch { return; }
    }

    // Oldingi suhbat (shu savoldan avvalgi xabarlar) — mavzu davomiyligi uchun
    const prevMsgs = chats.find((c) => c.id === sessionId)?.messages ?? [];
    const history = prevMsgs
      .filter((m) => m.text)
      .map((m) => ({ role: m.role, content: m.text }));

    const isFirstMessage = prevMsgs.length === 0;
    const now = new Date().toISOString();
    const um: Msg = { id: "u" + Date.now(), role: "user", text, time: now };
    setChats((cs) => cs.map((c) => {
      if (c.id !== sessionId) return c;
      const title = c.messages.length === 0 ? text.slice(0, 42) : c.title;
      return { ...c, title, lastMessageAt: now, messages: [...c.messages, um] };
    }));
    setDraft("");
    setThinking(true);
    setGenerating(true);
    addMessage(sessionId, "user", text).catch(() => {});  // DB ga saqlash

    if (isFirstMessage) {
      // Birinchi xabar — Qwen orqali qisqa sarlavha (ChatGPT uslubida) yasab,
      // backend'ga saqlaymiz. Muvaffaqiyatsiz bo'lsa — hozirgi qisqartirilgan
      // matnni zaxira sifatida saqlaymiz (persist bo'lmay qolmasin).
      const fallbackTitle = text.slice(0, 42);
      generateTitle(text)
        .then((title) => {
          const finalTitle = title || fallbackTitle;
          setChats((cs) => cs.map((c) => (c.id === sessionId ? { ...c, title: finalTitle } : c)));
          return renameSession(sessionId, finalTitle);
        })
        .catch(() => {
          renameSession(sessionId, fallbackTitle).catch(() => {});
        });
    }

    pendingRef.current = setTimeout(() => respond(sessionId, text, history), 750);
  };

  const stop = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (pendingRef.current) clearTimeout(pendingRef.current);
    setThinking(false); setGenerating(false);
  };

  const regenerate = () => {
    if (generating || !activeId) return;
    const msgs = chats.find((c) => c.id === activeId)?.messages || [];
    let lastUser = ""; let idx = -1;
    for (let i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].role === "user") { lastUser = msgs[i].text; idx = i; break; }
    }
    if (!lastUser) return;
    const history = msgs.slice(0, idx).filter((m) => m.text).map((m) => ({ role: m.role, content: m.text }));

    // Oxirgi javobdan keyingi assistant xabar(lar)ni backend'dan ham o'chiramiz —
    // aks holda sahifa yangilanganda eski javob qayta paydo bo'lib qoladi.
    for (const m of msgs.slice(idx + 1)) {
      if (m.role === "assistant" && isPersistedId(m.id)) {
        deleteMessage(activeId, m.id).catch(() => {});
      }
    }

    setActiveMsgs(activeId, (m) => {
      const copy = [...m];
      while (copy.length && copy[copy.length - 1].role === "assistant") copy.pop();
      return copy;
    });
    setThinking(true); setGenerating(true);
    pendingRef.current = setTimeout(() => respond(activeId, lastUser, history), 600);
  };

  // Xabarga like/dislike — mahalliy holatni yangilab, DB ga saqlaymiz
  const voteMsg = (messageId: string, vote: "up" | "down" | null) => {
    if (!activeId) return;
    setActiveMsgs(activeId, (m) => m.map((x) => (x.id === messageId ? { ...x, vote } : x)));
    voteMessage(activeId, messageId, vote).catch(() => {});
  };

  const active = chats.find((c) => c.id === activeId) || { messages: [] as Msg[], title: "" };
  const rawMsgs = active.messages || [];
  const isEmpty = rawMsgs.length === 0 && !thinking;
  const hasMessages = rawMsgs.length > 0 || thinking;
  const canSend = draft.trim().length > 0 && !generating;

  return {
    chats, activeId, setActiveId, active, rawMsgs, isEmpty, hasMessages, canSend,
    draft, setDraft, thinking, generating, newChat, removeChat, togglePin, renameChat, send, stop, regenerate, voteMsg,
  };
}
