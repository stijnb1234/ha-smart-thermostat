# 13: Gas savings report

**What to build:** A weekly report shows gas m3 per heating-degree-day against last year, heated hours per Room, and issues.

**Blocked by:** 04

**Status:** resolved

- [x] Gas meter entity configurable
- [x] Weekly report delivered as notification or dashboard card
- [x] Comparison against last year's heating-degree-days

Parent spec: `.scratch/smart-heating/spec.md`

## Answer

Pure `report.py` (HDD, m3/HDD, heated hours from state samples, formatted text, missing last year handled), tested in `tests/report/`. Options flow gained "Gas report settings" (gas meter entity, outdoor temperature entity, HDD base, default 18 degC). `report_glue.py` gathers recorder statistics (week vs 52 weeks earlier) and TRV history, and posts a persistent notification Mondays 08:00. Glue is unverified in a real HA.
