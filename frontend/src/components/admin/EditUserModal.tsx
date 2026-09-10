import { useState } from "react";
import HButton from "../common/HButton";
import FilterSelect from "./FilterSelect";
import { DEPARTMENTS, DEFAULT_DEPARTMENT, deptLabel } from "../../services/departments";
import type { AdminUserUpdate } from "../../services/adminService";
import type { AdminUser } from "../../types/admin";
import type { AdminStrings } from "../../types/i18n";
import type { Lang } from "../../types/lang";
import styles from "./AddUserModal.module.css";

interface Props {
  user: AdminUser;
  onClose: () => void;
  onSubmit: (input: AdminUserUpdate) => Promise<void>;
  t: AdminStrings;
  lang: Lang;
}

// Foydalanuvchini tahrirlash: ism, login, departament, (ixtiyoriy) yangi parol
// va verifikatsiya ma'lumotlari — xodim Face-ID'dan o'tolmasa admin ularni
// qo'lda to'ldirib, userni tasdiqlaydi.
export default function EditUserModal({ user, onClose, onSubmit, t: admin, lang }: Props) {
  const [name, setName] = useState(user.name);
  const [username, setUsername] = useState(user.handle.replace(/^@/, ""));
  // Bo'lim bo'sh qolmasin — eski yozuvlarda "—" bo'lsa ham "Boshqa" tanlanadi.
  const [dept, setDept] = useState(
    user.dept === "—" || !user.dept ? DEFAULT_DEPARTMENT : user.dept,
  );
  const [pass, setPass] = useState("");
  const [verified, setVerified] = useState(user.verified);
  const [pnfl, setPnfl] = useState(user.pnfl ?? "");
  const [patronym, setPatronym] = useState(user.patronym ?? "");
  const [docSeria, setDocSeria] = useState(user.docSeria ?? "");
  const [docNumber, setDocNumber] = useState(user.docNumber ?? "");
  const [birthDate, setBirthDate] = useState(user.birthDate ?? "");
  const [position, setPosition] = useState(user.position ?? "");
  const [branch, setBranch] = useState(user.branch ?? "");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState("");

  // Xodimlar bazasidan kelgan bo'lim ro'yxatda bo'lmasligi mumkin — uni ham ko'rsatamiz
  const deptOptions = DEPARTMENTS.map((d) => ({ value: d.uz, label: deptLabel(d, lang) }));
  if (dept && !deptOptions.some((o) => o.value === dept)) {
    deptOptions.unshift({ value: dept, label: dept });
  }

  const submit = async () => {
    if (!name.trim() || !username.trim()) {
      setErr(admin.nameLoginRequired);
      return;
    }
    if (pass && pass.length < 4) {
      setErr(admin.passTooShort);
      return;
    }
    if (pnfl.trim() && !/^\d{14}$/.test(pnfl.trim())) {
      setErr(admin.pnflInvalid);
      return;
    }
    setSaving(true);
    setErr("");
    try {
      await onSubmit({
        full_name: name.trim(),
        username: username.trim(),
        department: dept.trim() || DEFAULT_DEPARTMENT,
        password: pass || undefined,
        is_verified: verified,
        pnfl: pnfl.trim(),
        patronym: patronym.trim(),
        doc_seria: docSeria.trim().toUpperCase(),
        doc_number: docNumber.trim(),
        birth_date: birthDate || undefined,
        position: position.trim(),
        branch: branch.trim(),
      });
      onClose();
    } catch (e) {
      setErr(e instanceof Error ? e.message : admin.saveFailed);
      setSaving(false);
    }
  };

  return (
    <div onClick={onClose} className={styles.overlay}>
      <div
        onClick={(e) => e.stopPropagation()}
        className={styles.modal}
        style={{ maxWidth: 760, maxHeight: "calc(100vh - 48px)", overflowY: "auto" }}
      >
        <div className={styles.head}>
          <div className={styles.title}>{admin.editUserModalTitle}</div>
          <HButton onClick={onClose} className={styles.closeBtn} baseStyle={{}} hoverStyle={{ background: "var(--adm-border)", color: "var(--adm-text-strong)" }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="6" y1="6" x2="18" y2="18" /><line x1="18" y1="6" x2="6" y2="18" /></svg>
          </HButton>
        </div>
        <div className={styles.sub}>{admin.editUserModalSub}</div>

        {err && (
          <div style={{ margin: "0 0 14px", padding: "10px 13px", borderRadius: 10, background: "var(--adm-danger-bg)", border: "1px solid var(--adm-danger-border)", color: "var(--adm-danger)", fontSize: 14 }}>{err}</div>
        )}

        <div className={styles.fields}>
          <div className={styles.gridTwo}>
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
          </div>
          <div className={styles.gridTwo}>
            <div>
              <label className={styles.fieldLabel}>{admin.newPassword}</label>
              <input value={pass} onChange={(e) => setPass(e.target.value)} type="password" className={styles.input} placeholder={admin.newPasswordPh} autoComplete="new-password" />
            </div>
            <div>
              <label className={styles.fieldLabel}>{admin.dept}</label>
              <FilterSelect value={dept} onChange={setDept} fullWidth placeholder={admin.deptPh} options={deptOptions} />
            </div>
          </div>

          {/* Verifikatsiya ma'lumotlari — mobil Face-ID o'rniga admin qo'lda kiritadi */}
          <div style={{ marginTop: 6, paddingTop: 16, borderTop: "1px solid var(--adm-border)", fontSize: 15, fontWeight: 700, color: "var(--adm-text-strong)" }}>
            {admin.verificationSection}
          </div>
          <div className={styles.gridTwo}>
            <div>
              <label className={styles.fieldLabel}>{admin.pnflLabel}</label>
              <input value={pnfl} onChange={(e) => setPnfl(e.target.value.replace(/\D/g, "").slice(0, 14))} inputMode="numeric" className={styles.input} placeholder="12345678901234" />
            </div>
            <div>
              <label className={styles.fieldLabel}>{admin.birthDateLabel}</label>
              <input value={birthDate} onChange={(e) => setBirthDate(e.target.value)} type="date" className={styles.input} />
            </div>
          </div>
          <div className={styles.gridTwo}>
            <div>
              <label className={styles.fieldLabel}>{admin.docSeriaLabel}</label>
              <input value={docSeria} onChange={(e) => setDocSeria(e.target.value.toUpperCase().slice(0, 10))} className={styles.input} placeholder="AA" />
            </div>
            <div>
              <label className={styles.fieldLabel}>{admin.docNumberLabel}</label>
              <input value={docNumber} onChange={(e) => setDocNumber(e.target.value.slice(0, 20))} className={styles.input} placeholder="1234567" />
            </div>
          </div>
          <div className={styles.gridTwo}>
            <div>
              <label className={styles.fieldLabel}>{admin.patronymLabel}</label>
              <input value={patronym} onChange={(e) => setPatronym(e.target.value)} className={styles.input} />
            </div>
            <div>
              <label className={styles.fieldLabel}>{admin.branchLabel}</label>
              <input value={branch} onChange={(e) => setBranch(e.target.value)} className={styles.input} />
            </div>
          </div>
          <div>
            <label className={styles.fieldLabel}>{admin.positionLabel}</label>
            <input value={position} onChange={(e) => setPosition(e.target.value)} className={styles.input} />
          </div>
          <label style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 14.5, fontWeight: 600, color: "var(--adm-text-strong)", cursor: "pointer" }}>
            <input type="checkbox" checked={verified} onChange={(e) => setVerified(e.target.checked)} style={{ width: 18, height: 18, accentColor: "#4059BE" }} />
            {admin.verifiedLabel}
          </label>
        </div>

        <HButton onClick={submit} className={`${styles.submitBtn} tu-shiny`} baseStyle={{}} hoverStyle={{ transform: "translateY(-2px)", boxShadow: "0 10px 24px rgba(25, 48, 112,.28)" }}>
          {saving ? <span className={styles.spinner} /> : <span>{admin.save}</span>}
        </HButton>
      </div>
    </div>
  );
}
