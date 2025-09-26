#!/usr/bin/env python
from __future__ import annotations
import argparse, json, sys, time, os
from typing import Any, Dict, List, Tuple

# --- Import your agent logic ---
from agents.chat.chat_agent.agent_logic import ChatAgentLogic, ExplanationResponse

# --- Try to import your real LLM client; fall back to dummy ---
def get_llm_client(dummy: bool = False):
    if dummy:
        class DummyLLM:
            def chat_json(self, *, model: str, system: str, user: str, response_schema: Dict[str, Any], timeout: float = 1.5) -> Dict[str, Any]:
                # Extremely basic deterministic synthesis from the scan_data embedded in prompt
                # Extract scan_data dict from the prompt (hacky but good enough for CI mode)
                sd_start = user.find("scan_data JSON:")
                scan_text = user[sd_start + len("scan_data JSON:"):].strip()
                # Best effort parse
                try:
                    scan_data = eval(scan_text)  # nosec - controlled CI fixture only
                except Exception:
                    scan_data = {}
                flags = list(set(scan_data.get("flags", [])))
                ingredients = [str(x).lower() for x in scan_data.get("ingredients", [])]
                reasons = []
                checks = []
                out_flags = flags.copy()
                if "soft_cheese" in flags or scan_data.get("category") == "cheese":
                    reasons.append("Soft cheeses may be risky in pregnancy unless pasteurised.")
                    checks.append("Check the label for pasteurisation.")
                if "peanut" in ingredients or "peanuts" in ingredients or ("profile" in scan_data and "peanut" in (scan_data.get("profile") or {}).get("allergies", [])):
                    reasons.append("Contains or may contain peanuts; consider allergy risk.")
                    if "contains_peanuts" not in out_flags:
                        out_flags.append("contains_peanuts")
                if scan_data.get("power_source") == "button_battery":
                    reasons.append("Button batteries are dangerous if swallowed.")
                    if "button_battery_risk" not in out_flags:
                        out_flags.append("button_battery_risk")
                if int(scan_data.get("recalls_found", 0)) > 0:
                    reasons.append("A recall was found; stop use and follow recall instructions.")
                if scan_data.get("category") in ("cosmetic","topical"):
                    checks.append("Verify batch/lot and expiry on the label.")
                checks = list(dict.fromkeys(checks))
                return {
                    "summary": f"Here's what we found about {scan_data.get('product_name','this product')}.",
                    "reasons": reasons[:6],
                    "checks": checks[:6],
                    "flags": out_flags[:10],
                    "disclaimer": "Not medical advice. For urgent issues, use Emergency Guidance.",
                    "jurisdiction": scan_data.get("jurisdiction"),
                    "evidence": [{"type":"recall","source": r.get("agency","")} for r in scan_data.get("recalls", [])][:4],
                }
        return DummyLLM()
    else:
        try:
            from infra.openai_client import OpenAILLMClient  # your adapter
            return OpenAILLMClient()
        except Exception as e:
            print("Falling back to dummy LLM (no infra.openai_client).", file=sys.stderr)
            return get_llm_client(dummy=True)

def load_cases(path: str, limit: int | None) -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line: continue
            cases.append(json.loads(line))
            if limit and len(cases) >= limit: break
    return cases

def check_case(resp: Dict[str, Any], expect: Dict[str, Any]) -> Tuple[bool, List[str]]:
    ok = True
    errors: List[str] = []

    # Schema minimal checks
    for k in ("summary","disclaimer","reasons","checks","flags"):
        if k not in resp:
            ok, errors = False, errors + [f"missing key: {k}"]

    # Must include substrings in checks
    for s in expect.get("must_checks", []):
        if not any(s.lower() in c.lower() for c in resp.get("checks", [])):
            ok, errors = False, errors + [f"missing check contains: {s}"]

    # Must include any of substrings in checks
    for s in expect.get("must_checks_any", []):
        if not any(any(x in c.lower() for x in [s.lower()]) for c in resp.get("checks", [])):
            ok, errors = False, errors + [f"missing one-of checks contains: {s}"]

    # Flags
    for fl in expect.get("must_flags", []):
        if fl not in resp.get("flags", []):
            ok, errors = False, errors + [f"missing flag: {fl}"]
    any_flags = expect.get("must_flags_any", [])
    if any_flags:
        if not any(f in resp.get("flags", []) for f in any_flags):
            ok, errors = False, errors + [f"missing any-of flags: {any_flags}"]

    # Reasons substrings
    for s in expect.get("must_reasons", []):
        if not any(s.lower() in r.lower() for r in resp.get("reasons", [])):
            ok, errors = False, errors + [f"missing reason contains: {s}"]
    any_reasons = expect.get("must_reasons_any", [])
    if any_reasons:
        if not any(any(x in r.lower() for x in [s.lower() for s in any_reasons]) for r in resp.get("reasons", [])):
            ok, errors = False, errors + [f"missing any-of reasons: {any_reasons}"]

    # Evidence presence when recalls exist
    if "must_evidence" in expect:
        mt = expect["must_evidence"].get("type")
        if mt:
            if not any(e.get("type")==mt for e in resp.get("evidence", [])):
                ok, errors = False, errors + [f"missing evidence type: {mt}"]

    return ok, errors

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", default="evals/golden/cases.jsonl")
    ap.add_argument("--max", type=int, default=0, help="limit cases")
    ap.add_argument("--dummy", action="store_true", help="use deterministic dummy LLM (CI-safe)")
    args = ap.parse_args()

    llm = get_llm_client(dummy=args.dummy)
    agent = ChatAgentLogic(llm=llm, model=os.getenv("BS_EVAL_MODEL","gpt-4o"))
    cases = load_cases(args.cases, args.max or None)

    total = len(cases)
    passed = 0
    results: List[Dict[str, Any]] = []

    t_start = time.time()
    for c in cases:
        cid = c["id"]
        scan_data = dict(c.get("scan_data", {}))
        if "jurisdiction" in c:
            scan_data["jurisdiction"] = c["jurisdiction"]

        t0 = time.time()
        try:
            resp = agent.synthesize_result(scan_data)
            elapsed_ms = int((time.time() - t0) * 1000)
            ok, errs = check_case(resp, c.get("expect", {}))
            passed += 1 if ok else 0
            results.append({"id": cid, "ok": ok, "ms": elapsed_ms, "errors": errs, "resp": resp})
            status = "OK" if ok else "FAIL"
            print(f"[{status}] {cid}  ({elapsed_ms} ms)" + ("" if ok else f"  -> {errs}"))
        except Exception as e:
            results.append({"id": cid, "ok": False, "ms": None, "errors": [str(e)]})
            print(f"[ERR ] {cid} -> {e}")

    dur = int((time.time() - t_start) * 1000)
    print(f"\nSummary: {passed}/{total} passed  ({dur} ms total)")
    # Gate on 100% in dummy mode; 90%+ in live mode (LLM can drift)
    threshold = total if args.dummy else int(total * 0.90 + 0.5)
    if passed < threshold:
        print(f"Exit non-zero: threshold {threshold} not met.", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
