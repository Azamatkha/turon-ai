import { useState } from "react";
import HButton from "../common/HButton";
import type { AdminUser } from "../../types/admin";
import { admin } from "../../locales";
import styles from "./AddUserModal.module.css";

interface Props {
  user: AdminUser;
  onClose: () => void;
  onSubmit: (input: { username?: string; full_name?: string; department?: string; password?: string }) => Promise<void>;
}

// Foydalanuvchini tahrirlash: ism, login, bo'lim va (ixtiyoriy) yangi parol.
export default function EditUserModal({ user, onClose, onSubmit }: Props) {
  const [name, setName] = useState(user.name);
  const [username, setUsername] = useState(user.handle.replace(/^@/, ""));
  const [dept, setDept] = useState(user.dept === "—" ? "" : user.dept);
  const [pass, setPass] = useState("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  const submit = async () => {
    if (!name.trim() || !username.trim()) {
      setErr("Ism va login bo‘sh bo‘lmasligi kerak.");
      return;
    }
    if (pass && pass.length < 4) {
      setErr("Parol kamida 4 ta belgidan iborat bo‘lsin.");
      return;
    }
    setSaving(true);
    setErr("");
    try {
      await onSubmit({
        full_name: name.trim(),
        username: username.trim(),
        department: dept.trim(),
        password: pass || undefined,
      });
      onClose();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Saqlanmadi");
      setSaving(false);
    }
  };

  return (
    <div onClick={onClose} className={styles.overlay}>
      <div onClick={(e) => e.stopPropagation()} className={styles.modal}>
        <div className={styles.head}>
          <div className={styles.title}>{admin.editUserModalTitle}</div>
          <HButton onClick={onClose} className={styles.closeBtn} baseStyle={{}} hoverStyle={{ background: "#e6eae3", color: "#173f73" }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="6" y1="6" x2="18" y2="18" /><line x1="18" y1="6" x2="6" y2="18" /></svg>
          </HButton>
        </div>
        <div className={styles.sub}>{admin.editUserModalSub}</div>

        {err && (
          <div style={{ margin: "0 0 14px", padding: "10px 13px", borderRadius: 10, background: "#fdeceb", border: "1px solid #f6c9c5", color: "#c0392b", fontSize: 13 }}>{err}</div>
        )}

        <div className={styles.fields}>
          <div>
            <label className={styles.fieldLabel}>{admin.fullName}</label>
            <input value={name} onChange={(e) => setName(e.target.value)} className={styles.input} placeholder={admin.fullNamePh} />
          </div>
          <div>
            <label className={styles.fieldLabel}>{admin.username}</label>
            <div className={styles.usernameField}>
              <span className={styles.usernamePrefix}>@</span>
              <input value={username} onChange={(e) => setUsername(e.target.value.toLowerCase().replace(/[^a-z0-9._]/g, ""))} placeholder={admin.usernamePh} autoCapitalize="none" className={styles.usernameInput} />
            </div>
          </div>
          <div>
            <label className={styles.fieldLabel}>{admin.newPassword}</label>
            <input value={pass} onChange={(e) => setPass(e.target.value)} type="password" className={styles.input} placeholder={admin.newPasswordPh} autoComplete="new-password" />
          </div>
          <div>
            <label className={styles.fieldLabel}>{admin.dept}</label>
            <input value={dept} onChange={(e) => setDept(e.target.value)} className={styles.input} placeholder={admin.deptPh} />
          </div>
        </div>

        <HButton onClick={submit} className={styles.submitBtn} baseStyle={{}} hoverStyle={{ transform: "translateY(-2px)", boxShadow: "0 10px 24px rgba(23, 63, 115,.28)" }}>
          {saving ? <span className={styles.spinner} /> : <span>{admin.save}</span>}
        </HButton>
      </div>
    </div>
  );
}
