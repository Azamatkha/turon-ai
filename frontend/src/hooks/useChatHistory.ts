import { useEffect, useRef, useState } from "react";
import type { Chat, Msg } from "../types/chat";
import { askReply, askReplyStream } from "../services/chatBotService";
import {
  listSessions, createSession, getSession, deleteSession, addMessage, deleteMessage, renameSession, voteMessage, generateTitle, pinSession,
} from "../services/chatHistoryService";

// Vaqtinchalik (hali backend'ga saqlanmagan) xabar ID'lari "a"/"u" + timestamp
// ko'rinishida (tire yo'q). Backend'dagi haqiqiy ID — UUID (tire bor).
const isPersistedId = (id: string) => id.includes("-");

// Suhbatni ro'yxat tepasiga ko'taradigan vaqt belgisi.
// MUHIM: brauzer soati bilan server soati bir xil bo'lmasligi mumkin (server
// oldinda/orqada yursa, `new Date()` eski suhbatlarning server vaqtidan kichik
// bo'lib qolib, yangi xabar yozilgan suhbat tepaga chiqmasdi). Shuning uchun
// mavjud eng katta vaqtdan kafolatli katta qiymat olamiz — tartib soat farqiga
// bog'liq bo'lmaydi.
function bumpedTimestamp(cs: Chat[]): string {
  const maxMs = cs.reduce((mx, c) => {
    const t = new Date(c.lastMessageAt).getTime();
    return Number.isNaN(t) ? mx : Math.max(mx, t);
  }, 0);
  return new Date(Math.max(Date.now(), maxMs + 1000)).toISOString();
}

// Aniq (bitta mahsulot) javobda "Batafsil:" havolasi bo'ladi. Model ba'zan bunday
// javobga ham keraksiz "Shu turlardan qaysi biri..." savolini qo'shib qo'yadi —
// uni oxiridan olib tashlaymiz (ro'yxat javobiga tegmaymiz).
function stripStrayFollowup(text: string): string {
  if (!/batafsil:/i.test(text)) return text;
  const lines = text.replace(/\s+$/, "").split("\n");
  while (lines.length) {
    const low = lines[lines.length - 1].toLowerCase().trim();
    if (!low) { lines.pop(); continue; }
    if ((low.includes("qaysi biri") || low.includes("qaysinisi")) && low.includes("beray")) {
      lines.pop();
      continue;
    }
    break;
  }
  return lines.join("\n").replace(/\s+$/, "");
}

// Chat tarixini BACKEND (PostgreSQL) bilan boshqaradi — foydalanuvchiga bog'langan.
// useChatSimulation bilan bir xil interfeysni qaytaradi (ChatPage o'zgarmaydi).
export function useChatHistory(newChatLabel: string = "Yangi suhbat") {
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pendingRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const loaded = useRef<Set<string>>(new Set());

  const [chats, setChats] = useState<Chat[]>([]);
  // `chats`ning doim eng oxirgi qiymati — event handler'lar stale closure'ga
  // tushmasligi uchun (masalan togglePin joriy `pinned`ni shu yerdan o'qiydi).
  const chatsRef = useRef<Chat[]>([]);
  chatsRef.current = chats;
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
        // MUHIM: almashtirmaymiz, BIRLASHTIRAMIZ. Ro'yxat so'rovi xabarlar
        // so'rovidan kech kelsa, oddiy setChats(mapped) yuklangan xabarlarni va
        // yangi lastMessageAt'ni o'chirib yuborardi (refresh'da xabarlar yo'qolib,
        // suhbat tartibi eskiga qaytardi).
        setChats((cs) => {
          const merged = mapped.map((m) => {
            const ex = cs.find((c) => c.id === m.id);
            if (!ex) return m;
            const exTime = new Date(ex.lastMessageAt).getTime();
            const mTime = new Date(m.lastMessageAt).getTime();
            const exNewer = !Number.isNaN(exTime) && (Number.isNaN(mTime) || exTime > mTime);
            return {
              ...m,
              messages: ex.messages.length ? ex.messages : m.messages,
              title: ex.messages.length ? ex.title : m.title,
              lastMessageAt: exNewer ? ex.lastMessageAt : m.lastMessageAt,
            };
          });
          // Faqat mahalliy mavjud (hali ro'yxatga tushmagan) suhbatlarni saqlaymiz
          const localOnly = cs.filter((c) => !mapped.some((m) => m.id === c.id));
          return [...localOnly, ...merged];
        });
        // Login'da avtomatik ochmaymiz — bo'sh (yangi) chat ko'rinadi, user o'zi tanlaydi
      } catch {
        /* backend tayyor emas — bo'sh holat */
      }
    })();
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (pendingRef.current) clearTimeout(pendingRef.current);
      if (abortRef.current) abortRef.current.abort();
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

  // Pin/unpin — mahalliy holatni darhol yangilaymiz (optimistic), xato bo'lsa qaytaramiz.
  // MUHIM: joriy `pinned` qiymatini eski render'dagi `chats`dan emas, doim eng oxirgi
  // holatni ushlab turadigan `chatsRef`dan o'qiymiz — aks holda stale closure tufayli
  // parity buzilib, bir suhbatni belgilash uchun ikki marta bosishga to'g'ri kelardi.
  const togglePin = async (id: string) => {
    const chat = chatsRef.current.find((c) => c.id === id);
    if (!chat) return;
    const next = !chat.pinned;
    // Faqat optimistik — darrov ko'rinadi. Xato bo'lsa ham QAYTARMAYMIZ (rename
    // kabi): backend odatda saqlaydi (refresh'da ko'rinardi), lekin javobda
    // xato qaytarsa revert optimistik yangilanishni bekor qilib, "refresh
    // qilmaguncha o'zgarmadi" degan taassurot qoldirardi.
    setChats((cs) => cs.map((c) => (c.id === id ? { ...c, pinned: next } : c)));
    pinSession(id, next).catch(() => {});
  };

  // Vaqtinchalik assistant xabarini haqiqiy javob bilan yakunlab, DB ga saqlaydi
  const finalizeAssistant = (
    sessionId: string,
    tempId: string,
    res: { text: string; finishReason: string; completionTokens: number; maxTokens: number }
  ) => {
    const finalText = stripStrayFollowup(res.text);
    setActiveMsgs(sessionId, (m) =>
      m.map((x) =>
        x.id === tempId
          ? {
              ...x,
              text: finalText,
              debug: {
                finishReason: res.finishReason,
                completionTokens: res.completionTokens,
                maxTokens: res.maxTokens,
              },
            }
          : x
      )
    );
    setGenerating(false);
    // AI javobi ham faollik — suhbat sidebarda tepaga chiqsin (refresh kutmasdan)
    setChats((cs) => {
      const bumped = bumpedTimestamp(cs);
      return cs.map((c) => (c.id === sessionId ? { ...c, lastMessageAt: bumped } : c));
    });
    // DB ga saqlaymiz va vaqtinchalik id'ni haqiqiy DB id'ga almashtiramiz (like/dislike uchun)
    addMessage(sessionId, "assistant", finalText)
      .then((saved) =>
        setActiveMsgs(sessionId, (m) => m.map((x) => (x.id === tempId ? { ...x, id: saved.id } : x)))
      )
      .catch(() => {});
  };

  const respond = async (
    sessionId: string,
    userText: string,
    history: { role: string; content: string }[] = []
  ) => {
    const tempId = "a" + Date.now();
    const abort = new AbortController();
    abortRef.current = abort;

    // Birinchi token kelmaguncha "thinking" indikatori turadi — bo'sh bubble
    // ko'rinmasin. Birinchi token (yoki yakun) kelganda assistant xabarini qo'shamiz.
    let started = false;
    const ensureStarted = () => {
      if (started) return;
      started = true;
      setThinking(false);
      setActiveMsgs(sessionId, (m) => [
        ...m,
        {
          id: tempId,
          role: "assistant",
          text: "",
          time: new Date().toISOString(),
          debug: { finishReason: "", completionTokens: 0, maxTokens: 0 },
        },
      ]);
    };

    try {
      // Streaming: backend token-token yuboradi — real vaqtda matn va token o'sib boradi
      const res = await askReplyStream(
        userText,
        history,
        (fullText) => {
          ensureStarted();
          setActiveMsgs(sessionId, (m) =>
            m.map((x) =>
              x.id === tempId
                ? { ...x, text: fullText }
                : x
            )
          );
        },
        abort.signal
      );
      ensureStarted();
      finalizeAssistant(sessionId, tempId, res);
    } catch {
      // Foydalanuvchi to'xtatgan bo'lsa — hozirgi matnni qoldiramiz, xato deb ko'rsatmaymiz
      if (abort.signal.aborted) {
        setGenerating(false);
        return;
      }
      // Streaming ishlamadi — eski (oqimsiz) yo'lga qaytamiz
      try {
        const res = await askReply(userText, history);
        ensureStarted();
        finalizeAssistant(sessionId, tempId, res);
      } catch {
        setThinking(false);
        setGenerating(false);
      }
    } finally {
      if (abortRef.current === abort) abortRef.current = null;
    }
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
        setChats((cs) => [
          { id: s.id, title: newChatLabel, pinned: false, lastMessageAt: bumpedTimestamp(cs), messages: [] },
          ...cs,
        ]);
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
    setChats((cs) => {
      const bumped = bumpedTimestamp(cs);
      return cs.map((c) => {
        if (c.id !== sessionId) return c;
        const title = c.messages.length === 0 ? text.slice(0, 42) : c.title;
        return { ...c, title, lastMessageAt: bumped, messages: [...c.messages, um] };
      });
    });
    setDraft("");
    setThinking(true);
    setGenerating(true);
    // DB ga saqlaymiz va vaqtinchalik id'ni haqiqiy DB id'ga almashtiramiz —
    // busiz keyinchalik tahrirlash/qayta yuborishda bu xabarni bazadan o'chirib
    // bo'lmasdi (id vaqtinchalik bo'lgani uchun) va xabar ikki marta qolib ketardi.
    addMessage(sessionId, "user", text)
      .then((saved) =>
        setActiveMsgs(sessionId, (m) => m.map((x) => (x.id === um.id ? { ...x, id: saved.id } : x)))
      )
      .catch(() => {});

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

    pendingRef.current = setTimeout(() => respond(sessionId, text, history), 150);
  };

  const stop = () => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (pendingRef.current) clearTimeout(pendingRef.current);
    if (abortRef.current) { abortRef.current.abort(); abortRef.current = null; }
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
    pendingRef.current = setTimeout(() => respond(activeId, lastUser, history), 150);
  };

  // Sahifa javob kutilayotganda yangilansa (refresh) — foydalanuvchi xabari DB'da
  // qoladi-yu, javob hech qachon saqlanmaydi (chunki u faqat "typing" animatsiyasi
  // tugagach saqlanadi). Natijada oxirgi xabar "user" bo'lib qolib ketadi va javob
  // kelmaydi. Bu funksiya o'sha holatda so'rovni qayta yuboradi.
  const resendLast = () => {
    if (generating || !activeId) return;
    const msgs = chats.find((c) => c.id === activeId)?.messages || [];
    const last = msgs[msgs.length - 1];
    if (!last || last.role !== "user") return;
    const history = msgs.slice(0, -1).filter((m) => m.text).map((m) => ({ role: m.role, content: m.text }));
    setThinking(true); setGenerating(true);
    pendingRef.current = setTimeout(() => respond(activeId, last.text, history), 400);
  };

  // Foydalanuvchi o'z xabarini tahrirlab qayta yuboradi: shu xabardan keyingi
  // hamma narsa (eski javob) o'chiriladi va tahrirlangan matn yangi so'rov sifatida
  // yuboriladi. Bazada ham eski xabar+javoblar o'chirilib, yangisi qo'shiladi.
  const editAndResend = (messageId: string, newText: string) => {
    const text = newText.trim();
    if (generating || !activeId || !text) return;
    const msgs = chats.find((c) => c.id === activeId)?.messages || [];
    const idx = msgs.findIndex((m) => m.id === messageId);
    if (idx === -1 || msgs[idx].role !== "user") return;

    // Shu xabardan boshlab (eski user + undan keyingi javoblar) bazadan o'chiramiz
    for (const m of msgs.slice(idx)) {
      if (isPersistedId(m.id)) deleteMessage(activeId, m.id).catch(() => {});
    }

    const history = msgs.slice(0, idx).filter((m) => m.text).map((m) => ({ role: m.role, content: m.text }));
    const now = new Date().toISOString();
    const newId = "u" + Date.now();
    setActiveMsgs(activeId, (m) => [...m.slice(0, idx), { id: newId, role: "user", text, time: now }]);
    // Vaqtinchalik id'ni haqiqiy DB id'ga almashtiramiz — keyingi tahrir/qayta
    // yuborishda bu xabar ham bazadan o'chirilishi mumkin bo'lsin (dublikat bo'lmasin).
    addMessage(activeId, "user", text)
      .then((saved) =>
        setActiveMsgs(activeId, (m) => m.map((x) => (x.id === newId ? { ...x, id: saved.id } : x)))
      )
      .catch(() => {});
    setThinking(true); setGenerating(true);
    pendingRef.current = setTimeout(() => respond(activeId, text, history), 150);
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
    draft, setDraft, thinking, generating, newChat, removeChat, togglePin, renameChat, send, stop, regenerate, resendLast, editAndResend, voteMsg,
  };
}
