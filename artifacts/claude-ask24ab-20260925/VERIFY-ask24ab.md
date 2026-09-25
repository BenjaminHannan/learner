# ask-24ab result: PROVED WRONG (for this answer-format change) — registered 19:36:16 UTC, run 19:36-19:42 UTC

Marks: PASSMARKS-ask24ab.md (main dafc3dd1d, committed before the run started; the output folder was created
10 s later). Run: CPU in the creative thread's container, frozen MiniCPM5-1B, 5.9 minutes. Summary: cpu/ask24ab_summary.json.

| Format | Impossible hands called impossible (of 120) | Solvable hands called impossible (of 120) | Balanced accuracy |
|---|---|---|---|
| original (expression or "none") | 120 | 120 | 50% |
| AB1 (A = yes, B = no) | 0 | 0 | 50% |
| AB2 (A = no, B = yes) | 0 | 0 | 50% |

- The two mappings disagree on 0 of 240 hands. In AB1 the model picked A on 240 of 240 hands, and in AB2 it picked A
  on 0 of 240. So it follows the MEANING, not the letter: it answers "yes, it can be done" on every hand.
- The letters hold 0.80 (AB1) and 0.77 (AB2) of the next-token probability, and are the top token on all 480 prompts,
  so the model did answer in the format.
- The original format made 0 correct expressions on the 120 solvable hands.

Verdict against the marks:
- PASS needed 84/120 or more impossible hands called impossible under both mappings; it got 0 and 0. Not met.
- Proved wrong: balanced accuracy 55% or less under both mappings; it got 50% and 50%. MET.

What it means (shown, puzzles only): the frozen 1B does not tell solvable 24-hands from impossible ones through
either answer format. Its bias just follows the format: "none" on everything when none is offered as a way out, and
"yes" on everything when asked yes/no. So the "none on everything" surprise is not only a format problem.
Suggested: telling them apart has to be learned (ask-24's sleep arm N tests exactly that) or come from a separate
judge (feas-24 tests a cheap one on partial states). Untested: prompts with worked examples or reasoning.
Checks: the letter counts (240 / 0) with swapped meanings, and the 0 flips, agree with the impossible counts. The
panel's labels are exact (selftest: 458 impossible of 1,820; every pair proved by search).
