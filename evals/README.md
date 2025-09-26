# BabyShield Chat Evaluation Harness

## Overview

This directory contains the offline evaluation system for the BabyShield chat synthesizer. It validates that the AI-powered explanation system correctly identifies safety concerns, provides appropriate checks, and maintains consistent quality across different scenarios.

## Structure

```
evals/
├── golden/
│   └── cases.jsonl          # Golden test cases
├── README.md               # This file
└── scripts/
    └── run_synth_eval.py   # Evaluation runner
```

## Golden Test Cases

The `golden/cases.jsonl` file contains curated test cases covering key safety scenarios:

- **Soft cheese safety** - Pregnancy-related pasteurisation checks
- **Allergy detection** - Peanut and allergen identification
- **Button battery risks** - Small parts and ingestion hazards
- **Product recalls** - Recall detection and evidence citing
- **Age appropriateness** - Newborn and infant safety
- **Sleep safety** - Safe sleep surface guidelines
- **Label verification** - Batch/lot/expiry checking

Each case includes:
- `id`: Unique test case identifier
- `jurisdiction`: Region context (EU, US, etc.)
- `scan_data`: Input product data
- `expect`: Validation criteria (required checks, flags, reasons, evidence)

## Running Evaluations

### CI-Safe Mode (Deterministic)
```bash
python scripts/evals/run_synth_eval.py --dummy
```
- Uses deterministic dummy LLM
- 100% pass rate required
- No API tokens needed
- Fast execution for CI/CD

### Live Mode (Real LLM)
```bash
python scripts/evals/run_synth_eval.py
```
- Uses actual LLM client
- ≥90% pass rate required (allows for LLM variance)
- Requires OpenAI API access
- Tests real-world performance

### Options
- `--cases path/to/cases.jsonl` - Custom test cases file
- `--max N` - Limit to first N cases
- `--dummy` - Use deterministic dummy LLM

## Validation Criteria

The evaluator checks:

### Schema Compliance
- Required fields: `summary`, `disclaimer`, `reasons`, `checks`, `flags`
- Optional fields: `jurisdiction`, `evidence`

### Content Validation
- **must_checks**: Required substrings in checks array
- **must_checks_any**: At least one of the specified substrings in checks
- **must_flags**: Required exact flags
- **must_flags_any**: At least one of the specified flags
- **must_reasons**: Required substrings in reasons array
- **must_reasons_any**: At least one of the specified substrings in reasons
- **must_evidence**: Required evidence type (recall, regulation, etc.)

### Performance
- Per-case latency measurement
- Total execution time tracking
- Pass/fail reporting with detailed errors

## Exit Codes
- `0`: All tests passed
- `1`: Tests failed (below threshold)

## Example Output

```
[OK  ] cheese_brief_pasteurised_unknown  (45 ms)
[FAIL] peanut_allergy_bar  (67 ms)  -> ['missing flag: contains_peanuts']
[OK  ] button_battery_toy  (52 ms)
[OK  ] recalled_rocker  (78 ms)

Summary: 3/4 passed  (242 ms total)
Exit non-zero: threshold 4 not met.
```

## Integration

### CI/CD Pipeline
Add to your CI workflow:
```yaml
- name: Run Chat Evaluations
  run: python scripts/evals/run_synth_eval.py --dummy
```

### Development Testing
Run before deploying chat changes:
```bash
python scripts/evals/run_synth_eval.py --max 10
```

### Performance Monitoring
Track latency trends over time:
```bash
python scripts/evals/run_synth_eval.py | grep "ms total"
```

## Adding Test Cases

1. Identify a new safety scenario
2. Create the input `scan_data` 
3. Define expected outputs in `expect`
4. Add to `cases.jsonl` as a new line
5. Run `--dummy` mode to verify deterministic behavior
6. Test with live LLM to ensure realistic expectations

## Troubleshooting

**All tests failing in live mode:**
- Check OpenAI API key configuration
- Verify `infra.openai_client` module exists
- Try `--dummy` mode to isolate LLM issues

**Inconsistent live mode results:**
- LLM responses can vary; adjust expectations
- Consider lowering pass threshold for flaky cases
- Use more specific validation criteria

**Slow execution:**
- Use `--max N` to limit test cases
- Check network connectivity for live mode
- Optimize LLM timeout settings
