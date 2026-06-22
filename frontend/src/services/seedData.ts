import type { Chat } from "../types/chat";
import type { AdminUser } from "../types/admin";

export const seedChats: Chat[] = [
  { id: "c1", group: "Today", title: "", messages: [] },
  { id: "c2", group: "Today", title: "Mijozga kechikkan to‘lov xati", messages: [] },
  { id: "c3", group: "Yesterday", title: "Ipoteka refinansirovkasi shartlari", messages: [] },
  { id: "c4", group: "Yesterday", title: "KYC onboarding siyosati xulosasi", messages: [] },
  { id: "c5", group: "Previous 7 Days", title: "Karta nizosi javob shabloni", messages: [] },
  { id: "c6", group: "Previous 7 Days", title: "Korporativ depozit stavkalari", messages: [] },
  { id: "c7", group: "Previous 7 Days", title: "AML xavf belgilari ro‘yxati", messages: [] },
];

export const TAKEN_USERNAMES = ["admin", "root", "m.usmonov", "d.tashkentov", "s.rahimova"];

export const seedAdminUsers: AdminUser[] = [
  { id: 1, name: "Aziz Karimov", handle: "@a.karimov", dept: "Chakana", role: "Agent", status: "Active" },
  { id: 2, name: "Malika Yusupova", handle: "@m.yusupova", dept: "IT", role: "Admin", status: "Active" },
  { id: 3, name: "Dilshod Tashkentov", handle: "@d.tashkentov", dept: "Korporativ", role: "Agent", status: "Active" },
  { id: 4, name: "Sevara Rahimova", handle: "@s.rahimova", dept: "Komplayens", role: "Manager", status: "Active" },
  { id: 5, name: "Bobur Aliyev", handle: "@b.aliyev", dept: "G‘aznachilik", role: "Agent", status: "Invited" },
  { id: 6, name: "Nigora Usmonova", handle: "@n.usmonova", dept: "Chakana", role: "Agent", status: "Suspended" },
  { id: 7, name: "Jasur Komilov", handle: "@j.komilov", dept: "Risk", role: "Manager", status: "Active" },
];
