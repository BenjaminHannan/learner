# 382b: the one follow-up to 382. Marks fixed 2026-09-25 ~21:25 UTC, before any run

Why: 382's precondition failed (bm-395: store top 10 +1.66 over BM25's top 10, mark +3.0). In the same run, report
only, the store's top 20 scored 29.85: +4.67 [+3.24, +6.08] over BM25's top 10 and above the plain 1B reading the
whole chat (27.50). k = 20 was seen on LoCoMo practice, so LoCoMo can no longer judge it: **every LoCoMo number for
382b is labelled "k chosen on LoCoMo practice" and is a dev number, not a mark.** The memory row is judged on bank C
and chatpanel382, which nobody building 382b has seen. Benchmarks' recommendation (21:12 UTC) was this same choice;
Ben asked for no questions until ~23:40 UTC, so the month-end thread decided.

## The one change (vs 382)
E = scripts/claude_e2e382.py:build_382b: identical to build_382 except recall()'s k = 20. Controls G and T as in
PASSMARKS-382.md. No precondition.

## Marks
Exactly PASSMARKS-382.md's table, applied to build_382b, except:
- Y1 (LoCoMo E − Rb) is report-only (dev), for the reason above.
- The memory row is judged on Y2 alone (bank C, answerable asks right, E − G ≥ +10 points).
Judging protocol and the proved-wrong clause as in PASSMARKS-382.md.
