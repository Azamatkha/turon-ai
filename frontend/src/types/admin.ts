export type AdminRole = "Xodim" | "Admin";
// Holat ustuni endi onlayn/oflayn ko'rsatadi (avval hamma "Faol" edi)
export type AdminStatus = "Online" | "Offline";
export type AdminView = "dashboard" | "users" | "knowledgeList" | "pdfUpload" | "apiDocs";

export interface AdminUser {
  id: string;
  name: string;
  handle: string;
  dept: string;
  role: AdminRole;
  status: AdminStatus;
}
