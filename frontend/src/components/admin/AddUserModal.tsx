import HButton from "../common/HButton";
import FilterSelect from "./FilterSelect";
import { DEPARTMENTS, deptLabel } from "../../services/departments";
import type { AdminRole } from "../../types/admin";
import type { AdminStrings } from "../../types/i18n";
import type { Lang } from "../../types/lang";
import styles from "./AddUserModal.module.css";

const ROLES: AdminRole[] = ["Xodim", "Admin"];

interface AddUserModalProps {
  fName: string;
  setFName: (v: string) => void;
  fUser: string;
  setFUser: (v: string) => void;
  fDept: string;
  setFDept: (v: string) => void;
  fPass: string;
  setFPass: (v: string) => void;
  fRole: AdminRole;
  setFRole: (r: AdminRole) => void;
  adding: boolean;
  userTaken: boolean;
  error?: string;
  onClose: () => void;
  onSubmit: () => void;
  t: AdminStrings;
  lang: Lang;
}

export default function AddUserModal({
  fName, setFName, fUser, setFUser, fDept, setFDept, fPass, setFPass, fRole, setFRole, adding, userTaken, error, onClose, onSubmit, t: admin, lang,
}: AddUserModalProps) {
  return (
    <div onClick={onClose} className={styles.overlay}>
      <div onClick={(e) => e.stopPropagation()} className={styles.modal}>
        <div className={styles.head}>
          <div className={styles.title}>{admin.addUserModalTitle}</div>
          <HButton onClick={onClose} className={styles.closeBtn} baseStyle={{}} hoverStyle={{ background: "var(--adm-border)", color: "var(--adm-text-strong)" }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="6" y1="6" x2="18" y2="18" /><line x1="18" y1="6" x2="6" y2="18" /></svg>
          </HButton>
        </div>
        <div className={styles.sub}>{admin.addUserModalSub}</div>

        {error && (
          <div style={{ margin: "0 0 14px", padding: "10px 13px", borderRadius: 10, background: "var(--adm-danger-bg)", border: "1px solid var(--adm-danger-border)", color: "var(--adm-danger)", fontSize: 13 }}>{error}</div>
        )}

        <div className={styles.fields}>
          <div>
            <label className={styles.fieldLabel}>{admin.fullName}</label>
            <input value={fName} onChange={(e) => setFName(e.target.value)} className={styles.input} placeholder={admin.fullNamePh} />
          </div>
          <div>
            <label className={styles.fieldLabel}>{admin.username}</label>
            <div className={styles.usernameField}>
              <span className={styles.usernamePrefix}>@</span>
              <input value={fUser} onChange={(e) => setFUser(e.target.value.toLowerCase().replace(/[^a-z0-9._]/g, ""))} placeholder={admin.usernamePh} autoCapitalize="none" className={styles.usernameInput} />
              {userTaken && <span className={styles.takenLabel}>{admin.taken}</span>}
            </div>
          </div>
          <div>
            <label className={styles.fieldLabel}>{admin.password}</label>
            <input value={fPass} onChange={(e) => setFPass(e.target.value)} type="password" className={styles.input} placeholder="••••••••" autoComplete="new-password" />
          </div>
          {/* Departament nomlari uzun — alohida to'liq qatorda, Rol esa ostida */}
          <div>
            <label className={styles.fieldLabel}>{admin.dept}</label>
            <FilterSelect
              value={fDept}
              onChange={setFDept}
              fullWidth
              placeholder={admin.deptPh}
              options={DEPARTMENTS.map((d) => ({ value: d.uz, label: deptLabel(d, lang) }))}
            />
          </div>
          <div>
            <label className={styles.fieldLabel}>{admin.role}</label>
            <div className={styles.roleRow}>
              {ROLES.map((r) => (
                <button key={r} onClick={() => setFRole(r)} className={`${styles.roleBtn} ${fRole === r ? styles.roleBtnActive : styles.roleBtnInactive}`}>{admin.roleLabel[r]}</button>
              ))}
            </div>
          </div>
        </div>

        <HButton onClick={onSubmit} className={styles.submitBtn} baseStyle={{}} hoverStyle={{ transform: "translateY(-2px)", boxShadow: "0 10px 24px rgba(23, 63, 115,.28)" }}>
          {adding ? <span className={styles.spinner} /> : <span>{admin.create}</span>}
        </HButton>
      </div>
    </div>
  );
}
