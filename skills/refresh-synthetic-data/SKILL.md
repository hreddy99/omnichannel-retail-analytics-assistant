---
name: refresh-synthetic-data
description: Regenerate and validate the synthetic retail dataset. Use when changing the
  data generator, seeded scenarios, or trend ramp, or before a demo.
---
# Refresh Synthetic Data

Fully synthetic, fixed-seed retail data (no PII) with seeded demo scenarios and a gentle
multi-day operational ramp.

## Instructions
1. Regenerate and inspect row counts: `python -m data.generator`
2. Validate (must all pass — conversion drop in 15–25%, baseline stable, scenarios present):
   `python -m evals.validation`
3. Or run the bundled helper: `python skills/refresh-synthetic-data/scripts/refresh.py`
4. If you changed scenario magnitudes, keep the conversion baseline stable (CV < 0.25) so
   the validation checks still pass.

Generator lives in `data/generator.py`; checks in `evals/validation.py`.
