export type AdminRole = "Xodim" | "Admin";
export type AdminStatus = "Active" | "Suspended";
export type AdminView = "dashboard" | "users";

export interface AdminUser {
  id: string;
  name: string;
  handle: string;
  dept: string;
  role: AdminRole;
  status: AdminStatus;
}
