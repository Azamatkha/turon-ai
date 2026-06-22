import type { ChatStrings } from "../../types/i18n";

export const chat: ChatStrings = {
  newChat: "Новый чат",
  sub: "Спросите что угодно, придумайте идеи или начните ниже.",
  placeholder: "Напишите Turon AI…",
  disclaimer: "Turon AI может ошибаться. Проверяйте важное.",
  today: "Сегодня",
  yest: "Вчера",
  prev: "Последние 7 дней",
  sugg: ["Составь письмо клиенту", "Объясни банковский продукт", "Кратко изложи документ", "Помощь по операции"],
  greeting: (n: string) => `Чем помочь, ${n}?`,
};
