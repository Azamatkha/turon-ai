import { useState, useEffect, CSSProperties, ButtonHTMLAttributes, ReactNode } from "react";
import { useNavigate } from "react-router-dom";

// Turon AI logotipi
const Logo = ({ size = 30 }: { size?: number }) => (
  <svg viewBox="0 0 300 304" width={size} height={size} style={{ display: "block" }}>
    <path
      d="M255.855 103.421L151.944 0L0 151.229L151.944 303.571L237.084 217.934L236.596 217.741C218.796 215.674 196.967 200.887 174.025 194.767C153.234 190.031 117.854 192.284 113.738 189.784C210.706 153.869 208.725 193.015 261.188 193.69L300 154.651C205.217 202.737 227.309 139.389 112.627 146.032C208.968 101.141 220.332 165.106 297.139 144.51L273.803 121.284L273.564 121.289C209.821 145.798 215.563 94.5428 113.183 100.88C195.18 63.1381 219.363 100.88 255.774 103.395L255.855 103.421Z"
      fill="currentColor"
    />
  </svg>
);

// Hover stilini qo'llab-quvvatlovchi tugma
type HBProps = ButtonHTMLAttributes<HTMLButtonElement> & { baseStyle: CSSProperties; hoverStyle?: CSSProperties; children?: ReactNode };
function HButton({ baseStyle, hoverStyle, ...props }: HBProps) {
  const [h, setH] = useState(false);
  return <button {...props} onMouseEnter={() => setH(true)} onMouseLeave={() => setH(false)} style={{ ...baseStyle, ...(h && hoverStyle ? hoverStyle : {}) }} />;
}

type Role = "Agent" | "Manager" | "Admin";
type Status = "Active" | "Invited" | "Suspended";
interface User { id: number; name: string; handle: string; dept: string; role: Role; status: Status; }
type View = "dashboard" | "users";

const roleLabel: Record<Role, string> = { Agent: "Agent", Manager: "Menejer", Admin: "Admin" };
const statusLabel: Record<Status, string> = { Active: "Faol", Invited: "Taklif qilingan", Suspended: "To‘xtatilgan" };
const roleColor: Record<Role, string> = { Admin: "#16425b", Manager: "#2f6690", Agent: "#3a7ca5" };
const statusColor: Record<Status, string> = { Active: "#1f8a5b", Invited: "#b8860b", Suspended: "#c0392b" };

export default function AdminPage() {
  const navigate = useNavigate();
  const [view, setView] = useState<View>("dashboard");
  const [mounted, setMounted] = useState(false);
  const [search, setSearch] = useState("");
  const [addOpen, setAddOpen] = useState(false);
  const [adding, setAdding] = useState(false);
  const [fName, setFName] = useState("");
  const [fUser, setFUser] = useState("");
  const [fDept, setFDept] = useState("");
  const [fRole, setFRole] = useState<Role>("Agent");
  const [users, setUsers] = useState<User[]>([
    { id: 1, name: "Aziz Karimov", handle: "@a.karimov", dept: "Chakana", role: "Agent", status: "Active" },
    { id: 2, name: "Malika Yusupova", handle: "@m.yusupova", dept: "IT", role: "Admin", status: "Active" },
    { id: 3, name: "Dilshod Tashkentov", handle: "@d.tashkentov", dept: "Korporativ", role: "Agent", status: "Active" },
    { id: 4, name: "Sevara Rahimova", handle: "@s.rahimova", dept: "Komplayens", role: "Manager", status: "Active" },
    { id: 5, name: "Bobur Aliyev", handle: "@b.aliyev", dept: "G‘aznachilik", role: "Agent", status: "Invited" },
    { id: 6, name: "Nigora Usmonova", handle: "@n.usmonova", dept: "Chakana", role: "Agent", status: "Suspended" },
    { id: 7, name: "Jasur Komilov", handle: "@j.komilov", dept: "Risk", role: "Manager", status: "Active" },
  ]);

  // View almashganda grafik animatsiyasini qayta ishga tushirish
  useEffect(() => {
    setMounted(false);
    const r = requestAnimationFrame(() => setMounted(true));
    return () => cancelAnimationFrame(r);
  }, [view]);

  const onDashboard = view === "dashboard";
  const onUsers = view === "users";

  const openAdd = () => {
    setFName("");
    setFUser("");
    setFDept("");
    setFRole("Agent");
    setAdding(false);
    setAddOpen(true);
  };

  const submitAdd = () => {
    const handle = "@" + fUser.trim();
    if (!fName.trim() || !fUser.trim() || users.some((u) => u.handle === handle)) return;
    setAdding(true);
    setTimeout(() => {
      setUsers((us) => [{ id: Date.now(), name: fName.trim(), handle, dept: fDept.trim() || "—", role: fRole, status: "Invited" }, ...us]);
      setAdding(false);
      setAddOpen(false);
    }, 850);
  };

  // ---- statistik kartalar ----
  const statDefs = [
    { icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>, value: "1,284", label: "Jami foydalanuvchilar", trend: "+38", tint: "#2f6690" },
    { icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2Z" /></svg>, value: "312", label: "Bugungi faol suhbatlar", trend: "+9%", tint: "#3a7ca5" },
    { icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg>, value: "2,640", label: "Kunlik xabarlar", trend: "+12%", tint: "#16425b" },
    { icon: <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="9" /><polyline points="12 7 12 12 15 14" /></svg>, value: "1.8s", label: "O‘rtacha javob", trend: "−0.3s", tint: "#3a7ca5" },
  ];

  // ---- grafik (haftalik) ----
  const barData = [
    { day: "Du", value: 2100 }, { day: "Se", value: 2600 }, { day: "Ch", value: 2300 },
    { day: "Pa", value: 3100 }, { day: "Ju", value: 2800 }, { day: "Sh", value: 1500 }, { day: "Ya", value: 1200 },
  ];
  const max = 3200;

  // ---- bo'limlar ----
  const deptDefs = [
    { name: "Chakana banking", pct: 42, c: "#2f6690" },
    { name: "Korporativ", pct: 27, c: "#3a7ca5" },
    { name: "Komplayens", pct: 19, c: "#16425b" },
    { name: "G‘aznachilik", pct: 12, c: "#7fb3d2" },
  ];

  // ---- faollik ----
  const activity = [
    { who: "Sevara Rahimova", what: "karta nizosini hal qildi", when: "2 daq oldin", c: "#1f8a5b" },
    { who: "Bobur Aliyev", what: "ish maydoniga taklif qilindi", when: "24 daq oldin", c: "#3a7ca5" },
    { who: "Jasur Komilov", what: "AML ro‘yxatini yaratdi", when: "1 soat oldin", c: "#2f6690" },
    { who: "Nigora Usmonova", what: "akkaunti to‘xtatildi", when: "3 soat oldin", c: "#c0392b" },
  ];

  // ---- foydalanuvchilar jadvali ----
  const q = search.trim().toLowerCase();
  const filtered = users.filter((u) => !q || u.name.toLowerCase().includes(q) || u.handle.toLowerCase().includes(q) || u.dept.toLowerCase().includes(q));
  const handle = "@" + fUser.trim();
  const userTaken = !!fUser.trim() && users.some((u) => u.handle === handle);

  const navBtn = (id: View, label: string, icon: ReactNode, badge?: string) => {
    const act = view === id;
    return (
      <HButton
        key={id}
        onClick={() => setView(id)}
        baseStyle={{ display: "flex", alignItems: "center", gap: "11px", width: "100%", padding: "10px 12px", borderRadius: "10px", border: "none", cursor: "pointer", fontSize: "14px", fontWeight: 600, color: act ? "#fff" : "rgba(238,242,239,.66)", background: act ? "linear-gradient(120deg,#2f6690,#3a7ca5)" : "transparent", boxShadow: act ? "0 4px 14px rgba(47,102,144,.4)" : "none", transition: "all .18s ease" }}
        hoverStyle={act ? {} : { background: "rgba(255,255,255,.06)", color: "#fff" }}
      >
        <span style={{ width: "20px", height: "20px", flex: "0 0 auto", display: "flex", alignItems: "center", justifyContent: "center" }}>{icon}</span>
        <span style={{ flex: 1, textAlign: "left" }}>{label}</span>
        {badge && <span style={{ fontSize: "11px", fontWeight: 700, padding: "1px 8px", borderRadius: "99px", background: "rgba(127,179,210,.22)", color: "#bfe0f0" }}>{badge}</span>}
      </HButton>
    );
  };

  return (
    <div style={{ height: "100vh", width: "100%", display: "flex", overflow: "hidden", background: "#eef1ec", color: "#16425b" }}>
      {/* ===== SIDEBAR ===== */}
      <aside style={{ width: "248px", flex: "0 0 auto", background: "#16425b", color: "#eef2ef", height: "100%", display: "flex", flexDirection: "column", borderRight: "1px solid rgba(255,255,255,.08)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "11px", padding: "20px 18px", borderBottom: "1px solid rgba(255,255,255,.09)" }}>
          <div style={{ width: "30px", height: "30px", color: "#7fb3d2", flex: "0 0 auto" }}><Logo size={30} /></div>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: "16px", fontWeight: 800, letterSpacing: "-.3px", lineHeight: 1 }}>Turon<span style={{ fontWeight: 400, opacity: 0.7 }}> AI</span></div>
            <div style={{ fontSize: "10.5px", fontWeight: 600, letterSpacing: "1.2px", textTransform: "uppercase", color: "#7fb3d2", marginTop: "3px" }}>Admin panel</div>
          </div>
        </div>

        <nav style={{ flex: 1, padding: "14px 12px", display: "flex", flexDirection: "column", gap: "3px" }}>
          {navBtn("dashboard", "Boshqaruv paneli", <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="9" rx="1.5" /><rect x="14" y="3" width="7" height="5" rx="1.5" /><rect x="14" y="12" width="7" height="9" rx="1.5" /><rect x="3" y="16" width="7" height="5" rx="1.5" /></svg>)}
          {navBtn("users", "Foydalanuvchilar", <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>, String(users.length))}
        </nav>

        <div style={{ display: "flex", alignItems: "center", gap: "10px", padding: "13px 14px", borderTop: "1px solid rgba(255,255,255,.09)" }}>
          <div style={{ width: "34px", height: "34px", borderRadius: "10px", flex: "0 0 auto", background: "linear-gradient(140deg,#2f6690,#3a7ca5)", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontWeight: 700, fontSize: "14px" }}>M</div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: "13.5px", fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>Malika Yusupova</div>
            <div style={{ fontSize: "11.5px", color: "rgba(217,220,214,.55)" }}>Bosh admin</div>
          </div>
        </div>
      </aside>

      {/* ===== MAIN ===== */}
      <main style={{ flex: 1, minWidth: 0, height: "100%", display: "flex", flexDirection: "column", position: "relative" }}>
        <header style={{ height: "66px", flex: "0 0 auto", display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 28px", background: "#fff", borderBottom: "1px solid #e4e8e2" }}>
          <div>
            <div style={{ fontSize: "19px", fontWeight: 700, letterSpacing: "-.3px", color: "#16425b" }}>{onUsers ? "Foydalanuvchilar" : "Boshqaruv paneli"}</div>
            <div style={{ fontSize: "12.5px", color: "#7d909a", marginTop: "2px" }}>{onUsers ? "Turon AI’ga kimlar kira olishini boshqaring" : "Umumiy ko‘rinish · " + new Date().toLocaleDateString("uz-UZ", { weekday: "long", month: "long", day: "numeric" })}</div>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            {onUsers && (
              <div style={{ display: "flex", alignItems: "center", gap: "8px", height: "42px", padding: "0 14px", background: "#f4f6f3", border: "1px solid #e0e5df", borderRadius: "11px" }}>
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#9aafb8" strokeWidth="2" strokeLinecap="round"><circle cx="11" cy="11" r="7" /><line x1="21" y1="21" x2="16.5" y2="16.5" /></svg>
                <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Foydalanuvchi qidirish…" style={{ border: "none", outline: "none", background: "transparent", fontSize: "14px", color: "#16425b", width: "170px" }} />
              </div>
            )}
            <HButton onClick={openAdd} baseStyle={{ display: "flex", alignItems: "center", gap: "8px", height: "42px", padding: "0 16px", border: "none", borderRadius: "11px", cursor: "pointer", fontSize: "14px", fontWeight: 600, color: "#fff", background: "linear-gradient(135deg,#2f6690,#16425b)", boxShadow: "0 4px 14px rgba(22,66,91,.22)", transition: "all .18s ease" }} hoverStyle={{ transform: "translateY(-2px)", boxShadow: "0 8px 20px rgba(22,66,91,.3)" }}>
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round"><line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" /></svg>
              Foydalanuvchi qo‘shish
            </HButton>
          </div>
        </header>

        <div style={{ flex: 1, overflowY: "auto", padding: "26px 28px 40px" }}>
          {/* ===== DASHBOARD ===== */}
          {onDashboard && (
            <div style={{ display: "flex", flexDirection: "column", gap: "22px" }}>
              {/* stat kartalar */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: "16px" }}>
                {statDefs.map((s) => (
                  <div key={s.label} style={{ background: "#fff", border: "1px solid #e6eae3", borderRadius: "18px", padding: "20px", boxShadow: "0 1px 3px rgba(22,66,91,.04)" }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px" }}>
                      <div style={{ width: "40px", height: "40px", borderRadius: "12px", display: "flex", alignItems: "center", justifyContent: "center", background: s.tint + "14", color: s.tint }}>{s.icon}</div>
                      <div style={{ fontSize: "12px", fontWeight: 700, padding: "3px 9px", borderRadius: "99px", color: "#1f8a5b", background: "rgba(31,138,91,.1)" }}>{s.trend}</div>
                    </div>
                    <div style={{ fontSize: "30px", fontWeight: 800, letterSpacing: "-1px", color: "#16425b", lineHeight: 1 }}>{s.value}</div>
                    <div style={{ fontSize: "13px", color: "#7d909a", marginTop: "7px", fontWeight: 500 }}>{s.label}</div>
                  </div>
                ))}
              </div>

              {/* grafik qatori */}
              <div style={{ display: "grid", gridTemplateColumns: "1.65fr 1fr", gap: "16px" }}>
                {/* haftalik grafik */}
                <div style={{ background: "#fff", border: "1px solid #e6eae3", borderRadius: "18px", padding: "22px 24px", boxShadow: "0 1px 3px rgba(22,66,91,.04)" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "6px" }}>
                    <div>
                      <div style={{ fontSize: "15px", fontWeight: 700, color: "#16425b" }}>Shu haftadagi xabarlar</div>
                      <div style={{ fontSize: "12.5px", color: "#7d909a", marginTop: "2px" }}>Turon AI qayta ishlagan hajm</div>
                    </div>
                    <div style={{ display: "flex", alignItems: "baseline", gap: "6px" }}>
                      <span style={{ fontSize: "22px", fontWeight: 800, color: "#2f6690", letterSpacing: "-.5px" }}>18.4k</span>
                      <span style={{ fontSize: "12px", fontWeight: 600, color: "#1f8a5b" }}>+12%</span>
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "flex-end", gap: "14px", height: "180px", paddingTop: "22px" }}>
                    {barData.map((b, i) => (
                      <div key={b.day} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: "9px", height: "100%", justifyContent: "flex-end" }}>
                        <div title={b.value.toLocaleString()} style={{ width: "100%", maxWidth: "34px", borderRadius: "7px 7px 3px 3px", height: mounted ? (b.value / max) * 100 + "%" : "0%", background: i === 3 ? "linear-gradient(180deg,#2f6690,#16425b)" : "linear-gradient(180deg,#7fb3d2,#3a7ca5)", transition: `height .8s cubic-bezier(.2,.8,.3,1) ${i * 0.07}s` }} />
                        <span style={{ fontSize: "11.5px", fontWeight: 600, color: "#9aafb8" }}>{b.day}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* bo'limlar */}
                <div style={{ background: "#fff", border: "1px solid #e6eae3", borderRadius: "18px", padding: "22px 24px", boxShadow: "0 1px 3px rgba(22,66,91,.04)" }}>
                  <div style={{ fontSize: "15px", fontWeight: 700, color: "#16425b", marginBottom: "3px" }}>Bo‘limlar bo‘yicha foydalanish</div>
                  <div style={{ fontSize: "12.5px", color: "#7d909a", marginBottom: "20px" }}>Faol sessiyalar ulushi</div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "17px" }}>
                    {deptDefs.map((d, i) => (
                      <div key={d.name}>
                        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "7px" }}>
                          <span style={{ fontSize: "13px", fontWeight: 600, color: "#42565f" }}>{d.name}</span>
                          <span style={{ fontSize: "12.5px", fontWeight: 700, color: "#7d909a" }}>{d.pct}%</span>
                        </div>
                        <div style={{ height: "8px", borderRadius: "99px", background: "#eef1ec", overflow: "hidden" }}>
                          <div style={{ height: "100%", borderRadius: "99px", background: d.c, width: mounted ? d.pct + "%" : "0%", transition: `width .9s cubic-bezier(.2,.8,.3,1) ${i * 0.08 + 0.2}s` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* so'nggi faollik */}
              <div style={{ background: "#fff", border: "1px solid #e6eae3", borderRadius: "18px", padding: "22px 24px", boxShadow: "0 1px 3px rgba(22,66,91,.04)" }}>
                <div style={{ fontSize: "15px", fontWeight: 700, color: "#16425b", marginBottom: "16px" }}>So‘nggi faollik</div>
                <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                  {activity.map((a) => (
                    <div key={a.who} style={{ display: "flex", alignItems: "center", gap: "13px", padding: "11px 8px", borderRadius: "10px" }}>
                      <div style={{ width: "9px", height: "9px", borderRadius: "99px", flex: "0 0 auto", background: a.c, boxShadow: `0 0 0 3px ${a.c}22` }} />
                      <span style={{ flex: 1, fontSize: "13.5px", color: "#42565f" }}><span style={{ fontWeight: 600, color: "#16425b" }}>{a.who}</span> {a.what}</span>
                      <span style={{ fontSize: "12px", color: "#9aafb8", flex: "0 0 auto" }}>{a.when}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ===== USERS ===== */}
          {onUsers && (
            <div style={{ background: "#fff", border: "1px solid #e6eae3", borderRadius: "18px", overflow: "hidden", boxShadow: "0 1px 3px rgba(22,66,91,.04)" }}>
              <div style={{ display: "grid", gridTemplateColumns: "2.2fr 1.3fr 1fr 1fr 40px", gap: "16px", padding: "14px 22px", borderBottom: "1px solid #eef1ec", background: "#fafbf9", fontSize: "11.5px", fontWeight: 700, letterSpacing: ".5px", textTransform: "uppercase", color: "#9aafb8" }}>
                <span>Foydalanuvchi</span><span>Bo‘lim</span><span>Rol</span><span>Holat</span><span />
              </div>
              {filtered.map((u, i) => (
                <HButtonRow key={u.id} last={i === filtered.length - 1} index={i}>
                  <div style={{ display: "flex", alignItems: "center", gap: "12px", minWidth: 0 }}>
                    <div style={{ width: "36px", height: "36px", borderRadius: "10px", flex: "0 0 auto", background: "linear-gradient(140deg,#2f6690,#3a7ca5)", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontWeight: 700, fontSize: "14px" }}>{u.name.charAt(0).toUpperCase()}</div>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: "14px", fontWeight: 600, color: "#16425b", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{u.name}</div>
                      <div style={{ fontSize: "12.5px", color: "#9aafb8" }}>{u.handle}</div>
                    </div>
                  </div>
                  <span style={{ fontSize: "13.5px", color: "#42565f", alignSelf: "center" }}>{u.dept}</span>
                  <span style={{ alignSelf: "center" }}><span style={{ fontSize: "12.5px", fontWeight: 600, padding: "4px 11px", borderRadius: "8px", color: roleColor[u.role], background: roleColor[u.role] + "16" }}>{roleLabel[u.role]}</span></span>
                  <span style={{ alignSelf: "center" }}><span style={{ display: "inline-flex", alignItems: "center", gap: "7px", fontSize: "12.5px", fontWeight: 600, padding: "4px 11px 4px 9px", borderRadius: "99px", color: statusColor[u.status], background: statusColor[u.status] + "14" }}><span style={{ width: "6px", height: "6px", borderRadius: "99px", background: statusColor[u.status] }} />{statusLabel[u.status]}</span></span>
                  <button title="Ko‘proq" style={{ display: "flex", alignItems: "center", justifyContent: "center", width: "30px", height: "30px", alignSelf: "center", border: "none", borderRadius: "8px", background: "transparent", color: "#b5c1bc", cursor: "pointer" }}>
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><circle cx="5" cy="12" r="1.6" /><circle cx="12" cy="12" r="1.6" /><circle cx="19" cy="12" r="1.6" /></svg>
                  </button>
                </HButtonRow>
              ))}
              {filtered.length === 0 && <div style={{ padding: "46px", textAlign: "center", color: "#9aafb8", fontSize: "14px" }}>"{search}" bo‘yicha foydalanuvchi topilmadi.</div>}
            </div>
          )}
        </div>

        {/* ===== QO'SHISH MODALI ===== */}
        {addOpen && (
          <div onClick={() => setAddOpen(false)} style={{ position: "absolute", inset: 0, zIndex: 40, display: "flex", alignItems: "center", justifyContent: "center", padding: "24px", background: "rgba(13,33,45,.42)", backdropFilter: "blur(3px)", animation: "fadeIn .2s ease both" }}>
            <div onClick={(e) => e.stopPropagation()} style={{ width: "100%", maxWidth: "480px", background: "#fff", borderRadius: "20px", padding: "26px", boxShadow: "0 24px 70px rgba(13,33,45,.4)", animation: "popIn .32s cubic-bezier(.2,.8,.3,1) both" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "6px" }}>
                <div style={{ fontSize: "18px", fontWeight: 700, color: "#16425b", whiteSpace: "nowrap" }}>Yangi foydalanuvchi qo‘shish</div>
                <HButton onClick={() => setAddOpen(false)} baseStyle={{ display: "flex", alignItems: "center", justifyContent: "center", width: "34px", height: "34px", flex: "0 0 auto", borderRadius: "10px", border: "none", background: "#f1f4ef", color: "#5b6f78", cursor: "pointer", transition: "all .15s ease" }} hoverStyle={{ background: "#e6eae3", color: "#16425b" }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="6" y1="6" x2="18" y2="18" /><line x1="18" y1="6" x2="6" y2="18" /></svg>
                </HButton>
              </div>
              <div style={{ fontSize: "13px", color: "#7d909a", marginBottom: "22px" }}>Turon AI yordamchisiga ruxsat bering.</div>

              <div style={{ display: "flex", flexDirection: "column", gap: "15px" }}>
                <div>
                  <label style={fLabel}>To‘liq ism</label>
                  <input value={fName} onChange={(e) => setFName(e.target.value)} style={fInput} placeholder="masalan, Dilnoza Saidova" />
                </div>
                <div>
                  <label style={fLabel}>Foydalanuvchi nomi</label>
                  <div style={{ display: "flex", alignItems: "center", gap: "4px", height: "44px", border: "1.6px solid #dde2dc", borderRadius: "11px", padding: "0 13px", background: "#fbfcfa" }}>
                    <span style={{ color: "#9aafb8", fontSize: "15px", flex: "0 0 auto" }}>@</span>
                    <input value={fUser} onChange={(e) => setFUser(e.target.value.toLowerCase().replace(/[^a-z0-9._]/g, ""))} placeholder="d.saidova" autoCapitalize="none" style={{ flex: 1, minWidth: 0, border: "none", outline: "none", background: "transparent", fontSize: "14px", color: "#16425b", height: "100%" }} />
                    {userTaken && <span style={{ color: "#c0392b", fontSize: "12px", fontWeight: 600, flex: "0 0 auto" }}>Band</span>}
                  </div>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "13px" }}>
                  <div>
                    <label style={fLabel}>Bo‘lim</label>
                    <input value={fDept} onChange={(e) => setFDept(e.target.value)} style={fInput} placeholder="Chakana" />
                  </div>
                  <div>
                    <label style={fLabel}>Rol</label>
                    <div style={{ display: "flex", gap: "6px" }}>
                      {(["Agent", "Manager", "Admin"] as Role[]).map((r) => (
                        <button key={r} onClick={() => setFRole(r)} style={{ flex: 1, padding: "9px 4px", border: "1.4px solid " + (fRole === r ? "#2f6690" : "#dde2dc"), borderRadius: "9px", cursor: "pointer", fontSize: "12.5px", fontWeight: 600, color: fRole === r ? "#2f6690" : "#7d909a", background: fRole === r ? "rgba(47,102,144,.08)" : "#fff", transition: "all .15s ease" }}>{roleLabel[r]}</button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              <HButton onClick={submitAdd} baseStyle={{ width: "100%", height: "48px", marginTop: "24px", display: "flex", alignItems: "center", justifyContent: "center", border: "none", borderRadius: "12px", cursor: "pointer", background: "linear-gradient(135deg,#2f6690,#16425b)", color: "#fff", fontSize: "15px", fontWeight: 600, boxShadow: "0 6px 18px rgba(22,66,91,.2)", transition: "all .2s ease" }} hoverStyle={{ transform: "translateY(-2px)", boxShadow: "0 10px 24px rgba(22,66,91,.28)" }}>
                {adding ? <span style={{ width: "18px", height: "18px", borderRadius: "50%", border: "2.4px solid rgba(255,255,255,.35)", borderTopColor: "#fff", animation: "spin .7s linear infinite" }} /> : <span>Yaratish</span>}
              </HButton>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

const fLabel: CSSProperties = { display: "block", fontSize: "12.5px", fontWeight: 600, color: "#42565f", marginBottom: "7px" };
const fInput: CSSProperties = { width: "100%", height: "44px", border: "1.6px solid #dde2dc", borderRadius: "11px", padding: "0 13px", fontSize: "14px", color: "#16425b", outline: "none", background: "#fbfcfa" };

// Hoverlanadigan jadval qatori
function HButtonRow({ children, last, index }: { children: ReactNode; last: boolean; index: number }) {
  const [h, setH] = useState(false);
  return (
    <div
      onMouseEnter={() => setH(true)}
      onMouseLeave={() => setH(false)}
      style={{ display: "grid", gridTemplateColumns: "2.2fr 1.3fr 1fr 1fr 40px", gap: "16px", padding: "13px 22px", borderBottom: last ? "none" : "1px solid #f1f4ef", animation: `rowIn .4s ease both ${index * 0.04}s`, transition: "background .15s ease", background: h ? "#fafbf9" : "transparent" }}
    >
      {children}
    </div>
  );
}
