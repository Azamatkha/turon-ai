import type { Lang } from "../types/lang";
import type { LoginStrings, ChatStrings, ChatStaticStrings, AdminStrings } from "../types/i18n";
import { login as loginUz } from "./uz/login";
import { login as loginUzCyrl } from "./uz_cyrl/login";
import { login as loginRu } from "./ru/login";
import { chat as chatUz, chatStatic as chatStaticUz } from "./uz/chat";
import { chat as chatUzCyrl, chatStatic as chatStaticUzCyrl } from "./uz_cyrl/chat";
import { chat as chatRu, chatStatic as chatStaticRu } from "./ru/chat";
import { admin as adminUz } from "./uz/admin";
import { admin as adminUzCyrl } from "./uz_cyrl/admin";
import { admin as adminRu } from "./ru/admin";

// Til kodi -> tarjima lug'ati. Yangi til qo'shilganda shu yerga bir qator qo'shiladi.
export const loginDict: Record<Lang, LoginStrings> = { uz: loginUz, uz_cyrl: loginUzCyrl, ru: loginRu };
export const chatDict: Record<Lang, ChatStrings> = { uz: chatUz, uz_cyrl: chatUzCyrl, ru: chatRu };
export const chatStaticDict: Record<Lang, ChatStaticStrings> = {
  uz: chatStaticUz,
  uz_cyrl: chatStaticUzCyrl,
  ru: chatStaticRu,
};
export const adminDict: Record<Lang, AdminStrings> = { uz: adminUz, uz_cyrl: adminUzCyrl, ru: adminRu };

// Orqaga moslik uchun (til almashtirgichga ulanmagan joylar) — uz versiyasi
export const chatStatic = chatStaticUz;
