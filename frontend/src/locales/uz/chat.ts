import type { ChatStrings } from "../../types/i18n";

// Til almashtirgich orqali boshqariladigan matnlar
export const chat: ChatStrings = {
  newChat: "Yangi suhbat",
  sub: "Istalgan narsani so‘rang, g‘oya o‘ylab toping yoki quyidan boshlang.",
  placeholder: "Turon AI’ga yozing…",
  disclaimer: "Turon AI xato qilishi mumkin. Muhim ma’lumotlarni tekshiring.",
  today: "Bugun",
  yest: "Kecha",
  prev: "Oxirgi 7 kun",
  sugg: ["Mijozga xat loyihasini tuz", "Bank mahsulotini tushuntir", "Hujjatni qisqacha bayon qil", "Operatsiya bo‘yicha yordam"],
  greeting: (n: string) => `Qanday yordam beraman, ${n}?`,
};

// Hozircha til almashtirgichga ulanmagan matnlar (profil modali, maslahat sarlavhalari).
// Bular ilgari ham doim o'zbekcha bo'lgan — shu holatni saqlab qolamiz.
export const chatStatic = {
  openSidebar: "Ochish",
  newChatTitle: "Yangi suhbat",
  search: "Qidirish",
  searchPlaceholder: "Suhbatlardan qidirish…",
  noResults: "Hech narsa topilmadi",
  history: "Tarix",
  support: "Qo‘llab-quvvatlash",
  supportNumber: "1234",
  supportHint: "Yordam markazi raqami",
  collapseSidebar: "Yig'ish",
  theme: "Mavzu",
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
} as const;
