// clients/mobile/utils/verdict.ts
import type { Verdict } from "../components/VerdictCard";

export type ScanResult = {
  recalls_found?: number;
  key_flags?: string[];          // e.g. ["contains_peanuts","soft_cheese"]
  one_line_reason?: string;      // server-provided short reason if available
};

export type VerdictMapped = {
  verdict: Verdict;
  oneLine: string;
  flags: string[];
};

export function mapScanToVerdict(scan: ScanResult): VerdictMapped {
  const recalls = scan.recalls_found ?? 0;
  const flags = scan.key_flags ?? [];
  const hasCautionFlag = flags.length > 0;

  if (recalls > 0) {
    return {
      verdict: "recall",
      oneLine: scan.one_line_reason || "This product matches an active recall. Review recall details and stop use.",
      flags,
    };
  }
  if (hasCautionFlag) {
    return {
      verdict: "caution",
      oneLine: scan.one_line_reason || "No recalls found, but check the label and use with care.",
      flags,
    };
  }
  return {
    verdict: "safe",
    oneLine: scan.one_line_reason || "No recalls found. Nothing concerning detected in our checks.",
    flags,
  };
}
