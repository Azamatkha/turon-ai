import type { Lang } from "../types/lang";
import type { LoginStrings, ChatStrings } from "../types/i18n";
import { login as loginUz } from "./uz/login";
import { login as loginUzCyrl } from "./uz_cyrl/login";
import { login as loginRu } from "./ru/login";
import { chat as chatUz } from "./uz/chat";
import { chat as chatUzCyrl } from "./uz_cyrl/chat";
import { chat as chatRu } from "./ru/chat";

// Til kodi -> tarjima lug'ati. Yangi til qo'shilganda shu yerga bir qator qo'shiladi.
export const loginDict: Record<Lang, LoginStrings> = { uz: loginUz, uz_cyrl: loginUzCyrl, ru: loginRu };
export const chatDict: Record<Lang, ChatStrings> = { uz: chatUz, uz_cyrl: chatUzCyrl, ru: chatRu };

export { chatStatic } from "./uz/chat";
export { admin } from "./uz/admin";
