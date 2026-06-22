export type AdminRole = "Agent" | "Manager" | "Admin";
export type AdminStatus = "Active" | "Invited" | "Suspended";
export type AdminView = "dashboard" | "users";

export interface AdminUser {
  id: number;
  name: string;
  handle: string;
  dept: string;
  role: AdminRole;
  status: AdminStatus;
}
