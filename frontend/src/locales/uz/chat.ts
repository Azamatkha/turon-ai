import type { ChatStrings, ChatStaticStrings } from "../../types/i18n";

// Til almashtirgich orqali boshqariladigan matnlar
export const chat: ChatStrings = {
  newChat: "Yangi suhbat",
  sub: "Bank mahsulotlari bo‘yicha savolingizni yozing — mavjud ma’lumotlar asosida javob beraman.",
  placeholder: "Turon AI’ga yozing…",
  disclaimer: "Yangi qatorga o‘tish uchun Shift+Enter · javoblar biroz kechikishi mumkin.",
  today: "Bugun",
  yest: "Kecha",
  prev: "Oxirgi 7 kun",
  sugg: ["Kredit turlari", "Bank kartalari", "Omonatlar", "Tariflar va komissiyalar"],
  greeting: (n: string) => `Assalom aleykum, ${n}!\nSizga qanday yordam beraman?`,
};

// Hozircha til almashtirgichga ulanmagan matnlar (profil modali, maslahat sarlavhalari).
// Bular ilgari ham doim o'zbekcha bo'lgan — shu holatni saqlab qolamiz.
export const chatStatic: ChatStaticStrings = {
  openSidebar: "Panelni ochish",
  newChatTitle: "Yangi suhbat",
  search: "Qidirish",
  searchPlaceholder: "Suhbatlardan qidirish…",
  noResults: "Hech narsa topilmadi",
  history: "Tarix",
  support: "Qo‘llab-quvvatlash",
  supportNumber: "1234",
  supportHint: "Yordam markazi raqami",
  collapseSidebar: "Panelni yig'ish",
  theme: "Rejim",
  adminPanel: "Admin panel",
  send: "Yuborish",
  stop: "To‘xtatish",
  copy: "Nusxalash",
  copied: "Nusxalandi",
  regenerate: "Qayta yaratish",
  goodResponse: "Yaxshi javob",
  badResponse: "Yomon javob",
  close: "Yopish",
  fullName: "To‘liq ism",
  fullNamePh: "Ismingiz",
  username: "Foydalanuvchi nomi",
  usernamePh: "username",
  newPassword: "Yangi parol",
  newPasswordPh: "Bo‘sh qoldirsangiz — o‘zgarmaydi",
  taken: "Band",
  saved: "Saqlandi",
  saveChanges: "O‘zgarishlarni saqlash",
  logOut: "Chiqish",
  removeChat: "Suhbatni o‘chirish",
};
