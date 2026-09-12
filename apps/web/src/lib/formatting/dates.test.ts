import { expect, test } from "vite-plus/test";

import { formatRelativeDays, isBeforeToday, isoToWallClock, wallClockToIso } from "./dates";

test("wall-clock time in a zone round-trips through an ISO instant", () => {
  expect(wallClockToIso("2026-09-07T14:30", "Europe/Belgrade")).toBe("2026-09-07T12:30:00.000Z");
  expect(wallClockToIso("2026-01-07T14:30", "Europe/Belgrade")).toBe("2026-01-07T13:30:00.000Z");
  expect(wallClockToIso("2026-09-07T14:30", "UTC")).toBe("2026-09-07T14:30:00.000Z");
  expect(isoToWallClock("2026-09-07T12:30:00Z", "Europe/Belgrade")).toBe("2026-09-07T14:30");
  expect(isoToWallClock(null, "UTC")).toBe("");
});

test("rejects values that are not a datetime-local string", () => {
  expect(wallClockToIso("tomorrow", "UTC")).toBeNull();
  expect(wallClockToIso("2026-09-07", "UTC")).toBeNull();
});

test("relative days follow the zone's calendar, not UTC's", () => {
  const now = Date.parse("2026-09-07T23:30:00Z"); // 01:30 on the 8th in Belgrade, still the 7th in UTC
  expect(formatRelativeDays("2026-09-07T21:00:00Z", "UTC", now)).toBe("today");
  expect(formatRelativeDays("2026-09-07T21:00:00Z", "Europe/Belgrade", now)).toBe("yesterday");
  expect(formatRelativeDays("2026-09-10T08:00:00Z", "UTC", now)).toBe("in 3 days");
  expect(isBeforeToday("2026-09-07T21:00:00Z", "Europe/Belgrade", now)).toBe(true);
  expect(isBeforeToday("2026-09-07T21:00:00Z", "UTC", now)).toBe(false);
});
