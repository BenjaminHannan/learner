# vread blind recount (separate subagent, 2026-09-28, after scoring)

The subagent read only PASSMARKS.md, bar.json and scores/{lora,vector}_{main,hist}.json. It did not see verdict.json,
RESULTS.md or any script, and edited nothing. It recomputed every share from the raw family counts. Its report, as
returned:

**Verdict: FAIL.** The run is valid and was not proved wrong. V1 passes. V2 misses by 1 turn. V3 misses on backref
by 0.15 points.

**Bars and rules match PASSMARKS.**
- LoRA is at 0.995 in both of its files, and the vector reader is at 0.97 in both of its files, which equals bar.json.
- The 0.97 pick checks out: at 0.95, wrong saves are 6 of 982 (0.61%), above 0.5%; at 0.97 they are 3 of 961 (0.31%).
- The rule labels are correct.

| Mark | Vector | LoRA | Bar | Met? (margin) |
|---|---|---|---|---|
| Validity | - | 924 | LoRA ≥ 615 | yes (+309; 75.1% of 1230) |
| V1 right saves | 1098 | 924 | ≥ 0.95×924 = 877.8 | yes (+220.2; ratio 1.188) |
| V2 wrong turns | 4 | 1 | ≤ 1+2 = 3 | NO (over by 1) |
| V3 corrections | 59.54% | 44.51% | ≥ 39.51% | yes (+20.03 pts) |
| V3 former | 95.35% | 63.95% | ≥ 58.95% | yes (+36.40 pts) |
| V3 backref (hist) | 59.56% | 64.71% | ≥ 59.71% | NO (−0.15 pts; needed 82 of 136) |
| V3 look-alike | 0.37% | 0.00% | ≤ 5.00% | yes (4.63 pts under) |
| Proved wrong | 1098 | 924 | < 0.80×924 = 739.2 | no |

**Consistency checks, all passed:**
- The family denominators match PASSMARKS: 173, 136, 86 and 269.
- saves = right + wrong in every file.
- The per-family wrong turns add up to the totals.
- Every family_share_pct matches the recount to 2 decimals.
- Backref right saves are 0 under the main rule for both arms.

**Flags raised, and the answers:**
1. *The vector card breakdown adds up to 1,313, but cards_at_bar is 1,312.* The "not a whole-word span" count is a tag
   that overlaps the other categories (claude_vread_score.py counts it before the owner/value comparison). The
   exclusive categories add up: 1,302 right + 8 owner wrong + 0 value wrong + 2 with no gold card of the same
   relation and state = 1,312. Report only; no mark uses it.
2. *PASSMARKS does not say how to round.* The shares are exact ratios: 81/136 = 59.56% against 88/136 − 5 = 59.71%,
   so the mark is missed. It would only flip if shares were rounded to whole percents first, and the sealed rule does
   not round. The verdict stays FAIL.
3. *The score files cannot check the "117 of 173 corrections can be saved" figure.* It comes from DATA.md, where the
   gold is scored as a read (main rule). Neither arm exceeds it (103 and 77).
4. *The vector rounds_mean is 1.0.* Noted in RESULTS.md: the learned stop always halted after the first round.
