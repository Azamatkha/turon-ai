import type { ChatStrings } from "../../types/i18n";

// O'zbekcha (kirill yozuvi) — lotin "uz" lug'atining transliteratsiyasi
export const chat: ChatStrings = {
  newChat: "Янги суҳбат",
  sub: "Истаган нарсани сўранг, ғоя ўйлаб топинг ёки қуйидан бошланг.",
  placeholder: "Turon AI'га ёзинг…",
  disclaimer: "Turon AI хато қилиши мумкин. Муҳим маълумотларни текширинг.",
  today: "Бугун",
  yest: "Кеча",
  prev: "Охирги 7 кун",
  sugg: ["Мижозга хат лойиҳасини туз", "Банк маҳсулотини тушунтир", "Ҳужжатни қисқача баён қил", "Операция бўйича ёрдам"],
  greeting: (n: string) => `Қандай ёрдам бераман, ${n}?`,
};
