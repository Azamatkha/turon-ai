import type { Chat } from "../types/chat";
import type { AdminUser } from "../types/admin";

export const seedChats: Chat[] = [
  { id: "c1", pinned: false, lastMessageAt: "2026-07-14T09:00:00Z", title: "", messages: [] },
  { id: "c2", pinned: false, lastMessageAt: "2026-07-14T08:00:00Z", title: "Mijozga kechikkan to‘lov xati", messages: [] },
  { id: "c3", pinned: false, lastMessageAt: "2026-07-13T08:00:00Z", title: "Ipoteka refinansirovkasi shartlari", messages: [] },
  { id: "c4", pinned: false, lastMessageAt: "2026-07-13T07:00:00Z", title: "KYC onboarding siyosati xulosasi", messages: [] },
  { id: "c5", pinned: false, lastMessageAt: "2026-07-10T08:00:00Z", title: "Karta nizosi javob shabloni", messages: [] },
  { id: "c6", pinned: false, lastMessageAt: "2026-07-09T08:00:00Z", title: "Korporativ depozit stavkalari", messages: [] },
  { id: "c7", pinned: false, lastMessageAt: "2026-07-08T08:00:00Z", title: "AML xavf belgilari ro‘yxati", messages: [] },
];

export const TAKEN_USERNAMES = ["admin", "root", "m.usmonov", "d.tashkentov", "s.rahimova"];

export const seedAdminUsers: AdminUser[] = [
  { id: "1", name: "Aziz Karimov", handle: "@a.karimov", dept: "Chakana", role: "Xodim", status: "Offline" },
  { id: "2", name: "Malika Yusupova", handle: "@m.yusupova", dept: "IT", role: "Admin", status: "Offline" },
  { id: "3", name: "Dilshod Tashkentov", handle: "@d.tashkentov", dept: "Korporativ", role: "Xodim", status: "Offline" },
];
