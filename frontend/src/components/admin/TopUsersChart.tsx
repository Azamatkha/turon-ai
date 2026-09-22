import type { TopUserStat } from "../../services/adminService";
import type { AdminStrings } from "../../types/i18n";
import styles from "./TopUsersChart.module.css";

interface TopUsersChartProps {
  users: TopUserStat[];
  mounted: boolean;
  t: AdminStrings;
}

/**
 * Eng faol xodimlar — so'nggi 30 kunda eng ko'p savol bergan 5 kishi,
 * gorizontal ustunlarda.
 *
 * Ilgari shu joyda "Faollik tarkibi" turardi (so'nggi 10 ta login/logout
 * hodisasining ulushi) — undan xulosa chiqarib bo'lmasdi. Bu diagramma esa
 * botdan kim ko'proq foydalanayotganini ko'rsatadi.
 *
 * Ustun uzunligi ENG FAOL xodimga nisbatan (u doim 100%) — foizlar yig'indisi
 * emas, chunki bu "ulush" emas, solishtirish.
 */
export default function TopUsersChart({ users, mounted, t: admin }: TopUsersChartProps) {
  const max = Math.max(1, ...users.map((u) => u.count));

  return (
    <div className={styles.card}>
      <div className={styles.title}>{admin.topUsersTitle}</div>
      <div className={styles.sub}>{admin.topUsersSub}</div>

      {users.length === 0 ? (
        <div className={styles.empty}>{admin.chartNoData}</div>
      ) : (
        <ol className={styles.list}>
          {users.map((u, i) => (
            <li key={u.username} className={styles.row}>
              <span className={styles.rank} aria-hidden="true">{i + 1}</span>
              <div className={styles.body}>
                <div className={styles.top}>
                  <span className={styles.name} title={u.department ? `${u.name} — ${u.department}` : u.name}>
                    {u.name}
                    {u.department && <span className={styles.dept}> · {u.department}</span>}
                  </span>
                  <span className={styles.count}>{admin.topUsersCount(u.count)}</span>
                </div>
                <div className={styles.track}>
                  <div
                    className={styles.bar}
                    style={{
                      width: mounted ? `${(u.count / max) * 100}%` : "0%",
                      transitionDelay: `${i * 0.06}s`,
                      // Birinchi o'rin to'q, qolganlari och — ko'z darhol yetakchini topadi
                      opacity: i === 0 ? 1 : 0.62,
                    }}
                  />
                </div>
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
