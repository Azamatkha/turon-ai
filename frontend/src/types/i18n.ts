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

// Chat interfeysining tilга bog'liq statik matnlari (til almashtirgichga ulanadi)
export interface ChatStaticStrings {
  openSidebar: string;
  newChatTitle: string;
  search: string;
  searchPlaceholder: string;
  noResults: string;
  history: string;
  support: string;
  supportNumber: string;
  supportHint: string;
  collapseSidebar: string;
  theme: string;
  adminPanel: string;
  send: string;
  stop: string;
  copy: string;
  copied: string;
  regenerate: string;
  goodResponse: string;
  badResponse: string;
  close: string;
  fullName: string;
  fullNamePh: string;
  username: string;
  usernamePh: string;
  newPassword: string;
  newPasswordPh: string;
  taken: string;
  saved: string;
  saveChanges: string;
  logOut: string;
  removeChat: string;
}
