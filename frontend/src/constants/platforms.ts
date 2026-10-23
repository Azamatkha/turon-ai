// Sidebar pastidagi "Platformalar" tugmasi ochadigan ro'yxat — bankning
// boshqa AI platformalari. Yangi platforma qo'shish = shu ro'yxatga bitta
// yozuv. Havola yangi oynada ochiladi.
//
// Ro'yxat bo'sh bo'lsa, tugma baribir ko'rinadi va "tez orada" yozuvini
// ko'rsatadi.

export interface Platform {
  id: string;
  /** Platforma nomi — brend nomi, tarjima qilinmaydi */
  name: string;
  url: string;
}

export const PLATFORMS: Platform[] = [];
