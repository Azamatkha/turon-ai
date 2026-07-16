// Ro'yxatdan o'tishda tanlanadigan DEPARTAMENTLAR ro'yxati.
// Foydalanuvchi nomni qo'lda yozmaydi — shu ro'yxatdan tanlaydi
// (aks holda "123456" kabi keraksiz nomlar admin statistikasiga tushib qolardi).
//
// Backendga har doim `uz` (lotincha) nom yuboriladi — statistikada bir xil
// bo'lishi uchun. Ko'rsatiladigan matn foydalanuvchi tiliga qarab tanlanadi.
//
// YANGI DEPARTAMENT QO'SHISH: shu massivga { uz, ru, uz_cyrl } qatorini qo'shing.

import type { Lang } from "../types/lang";

export interface Department {
  uz: string;
  ru: string;
  uz_cyrl: string;
}

export const DEPARTMENTS: Department[] = [
  { uz: "Ijro nazorati departamenti", ru: "Департамент контроля исполнения", uz_cyrl: "Ижро назорати департаменти" },
  { uz: "Buxgalteriya departamenti", ru: "Департамент бухгалтерии", uz_cyrl: "Бухгалтерия департаменти" },
  { uz: "Xavfsizlik departamenti", ru: "Департамент безопасности", uz_cyrl: "Хавфсизлик департаменти" },
  { uz: "Muammoli aktivlar bilan ishlash departamenti", ru: "Департамент по работе с проблемными активами", uz_cyrl: "Муаммоли активлар билан ишлаш департаменти" },
  { uz: "Axborot texnologiyalar departamenti", ru: "Департамент информационных технологий", uz_cyrl: "Ахборот технологиялар департаменти" },
  { uz: "Chakana biznes departamenti", ru: "Департамент розничного бизнеса", uz_cyrl: "Чакана бизнес департаменти" },
  { uz: "Mijozlar servisi va marketing departamenti", ru: "Департамент клиентского сервиса и маркетинга", uz_cyrl: "Мижозлар сервиси ва маркетинг департаменти" },
  { uz: "Korporativ biznes departamenti", ru: "Департамент корпоративного бизнеса", uz_cyrl: "Корпоратив бизнес департаменти" },
  { uz: "Monitoring va nazorat qilish departamenti", ru: "Департамент мониторинга и контроля", uz_cyrl: "Мониторинг ва назорат қилиш департаменти" },
  { uz: "Moliyaviy hisobotlar departamenti", ru: "Департамент финансовой отчётности", uz_cyrl: "Молиявий ҳисоботлар департаменти" },
  { uz: "Operatsion departamenti", ru: "Операционный департамент", uz_cyrl: "Операцион департаменти" },
  { uz: "Moliya bozoridagi operatsiyalar departamenti", ru: "Департамент операций на финансовом рынке", uz_cyrl: "Молия бозоридаги операциялар департаменти" },
  { uz: "Filial tarmoqlarini boshqarish departamenti", ru: "Департамент управления филиальной сетью", uz_cyrl: "Филиал тармоқларини бошқариш департаменти" },
  { uz: "Davlat dasturlari bilan ishlash departamenti", ru: "Департамент по работе с государственными программами", uz_cyrl: "Давлат дастурлари билан ишлаш департаменти" },
  { uz: "Xodimlarni boshqarish (HR) departamenti", ru: "Департамент управления персоналом (HR)", uz_cyrl: "Ходимларни бошқариш (HR) департаменти" },
  { uz: "Anderrayting departamenti", ru: "Департамент андеррайтинга", uz_cyrl: "Андеррайтинг департаменти" },
  { uz: "Bank karta tizimlarini qo'llab quvvatlash departamenti", ru: "Департамент поддержки систем банковских карт", uz_cyrl: "Банк карта тизимларини қўллаб-қувватлаш департаменти" },
  { uz: "Kichik va o'rta biznes departamenti", ru: "Департамент малого и среднего бизнеса", uz_cyrl: "Кичик ва ўрта бизнес департаменти" },
  { uz: "Risk departamenti", ru: "Департамент рисков", uz_cyrl: "Риск департаменти" },
  { uz: "Ichki audit departamenti", ru: "Департамент внутреннего аудита", uz_cyrl: "Ички аудит департаменти" },
  { uz: "Komplaens nazorat departamenti", ru: "Департамент комплаенс-контроля", uz_cyrl: "Комплаенс назорат департаменти" },
  { uz: "Boshqa", ru: "Другое", uz_cyrl: "Бошқа" },
];

// Foydalanuvchi tiliga mos ko'rsatiladigan nom (backendga baribir uz yuboriladi)
export function deptLabel(d: Department, lang: Lang): string {
  return lang === "ru" ? d.ru : lang === "uz_cyrl" ? d.uz_cyrl : d.uz;
}
