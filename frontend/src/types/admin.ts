export type AdminRole = "Xodim" | "Admin";
// Holat ustuni endi onlayn/oflayn ko'rsatadi (avval hamma "Faol" edi)
export type AdminStatus = "Online" | "Offline";
export type AdminView = "dashboard" | "users" | "reports" | "knowledgeList" | "pdfUpload" | "apiDocs";

export interface AdminUser {
  id: string;
  name: string;
  handle: string;
  dept: string;
  role: AdminRole;
  status: AdminStatus;
  // Mobil ilovada Face-ID verifikatsiyasidan o'tganmi (admin qo'lda ham tasdiqlay oladi)
  verified: boolean;
  // Verifikatsiya ma'lumotlari — admin tahrirlash oynasi uchun
  pnfl?: string;
  patronym?: string;
  docSeria?: string;
  docNumber?: string;
  birthDate?: string;
  position?: string;
  branch?: string;
}
