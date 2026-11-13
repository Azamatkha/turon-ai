import { describe, expect, it } from "vitest";
import { fmt2, fmtDate, scheduleFromDto } from "./paymentSchedule";

describe("paymentSchedule", () => {
  it("summani bo'shliq bilan guruhlaydi", () => {
    expect(fmt2(1234567.891)).toBe("1 234 567.89");
    expect(fmt2(0)).toBe("0.00");
    expect(fmt2(-1500)).toBe("-1 500.00");
  });

  it("DTO sanasini MAHALLIY kun sifatida o'qiydi (UTC surilishisiz)", () => {
    const res = scheduleFromDto({
      rows: [
        { k: 1, date: "2026-08-14", balance: 100, principal: 10, interest: 2, total: 12, days: 30 },
      ],
      total_principal: 10,
      total_interest: 2,
      total_paid: 12,
      insurance: 0,
      full_cost: 12,
    });
    expect(fmtDate(res.rows[0].date)).toBe("14.08.2026");
    expect(res.totalPaid).toBe(12);
    expect(res.fullCost).toBe(12);
  });
});
