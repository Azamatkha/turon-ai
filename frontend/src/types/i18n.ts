// Tilga bog'liq lug'atlar uchun umumiy shakllar (uz/ru bir xil interfeysga mos kelishi kerak)
export interface LoginStrings {
  badge: string;
  headline: string;
  sub: string;
  sso: string;
  signIn: string;
  welcome: string;
  invalid: string;
  login: string;
  password: string;
  loginPh: string;
  remember: string;
  help: string;
  monitored: string;
  label: string;
  online: string;
  pvUser: string;
  pvAI: string;
  statLabel: string;
}

export interface ChatStrings {
  newChat: string;
  sub: string;
  placeholder: string;
  disclaimer: string;
  today: string;
  yest: string;
  prev: string;
  sugg: string[];
  greeting: (name: string) => string;
}
