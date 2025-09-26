// clients/mobile/utils/verdict.test.ts
import { mapScanToVerdict } from "./verdict";

test("maps recall > 0 to recall", () => {
  const out = mapScanToVerdict({ recalls_found: 1, key_flags: [] });
  expect(out.verdict).toBe("recall");
  expect(out.oneLine).toContain("active recall");
});

test("maps flags to caution", () => {
  const out = mapScanToVerdict({ recalls_found: 0, key_flags: ["soft_cheese"] });
  expect(out.verdict).toBe("caution");
  expect(out.flags).toEqual(["soft_cheese"]);
});

test("maps clean to safe", () => {
  const out = mapScanToVerdict({ recalls_found: 0, key_flags: [] });
  expect(out.verdict).toBe("safe");
  expect(out.oneLine).toContain("No recalls found");
});

test("uses custom one_line_reason when provided", () => {
  const customReason = "Custom safety message from server";
  const out = mapScanToVerdict({ 
    recalls_found: 0, 
    key_flags: [], 
    one_line_reason: customReason 
  });
  expect(out.oneLine).toBe(customReason);
});

test("handles multiple flags", () => {
  const flags = ["contains_peanuts", "soft_cheese", "high_sodium"];
  const out = mapScanToVerdict({ recalls_found: 0, key_flags: flags });
  expect(out.verdict).toBe("caution");
  expect(out.flags).toEqual(flags);
});

test("recall verdict overrides flags", () => {
  const out = mapScanToVerdict({ 
    recalls_found: 2, 
    key_flags: ["contains_peanuts"] 
  });
  expect(out.verdict).toBe("recall");
  expect(out.flags).toEqual(["contains_peanuts"]);
});
