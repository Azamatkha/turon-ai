export type Role = "user" | "assistant";

export interface Msg {
  id: string;
  role: Role;
  text: string;
}

export interface Chat {
  id: string;
  group: string;
  title: string;
  messages: Msg[];
}

// ChatPage'da mavzu (light/dark) bo'yicha hisoblanadigan rang tokenlari
export interface ThemeTokens {
  bg: string;
  headBg: string;
  headBorder: string;
  strong: string;
  muted: string;
  card: string;
  cardBorder: string;
  input: string;
  disc: string;
  chipShadow: string;
}

export interface SideTokens {
  bg: string;
  fg: string;
  sub: string;
  active: string;
  border: string;
  logo: string;
  btn: string;
}
