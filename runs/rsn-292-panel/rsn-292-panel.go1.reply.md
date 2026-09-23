Building your blind panel — fetching files and verifying the workspace.
Spec and base located. Now studying the base agent interface to build the panel drivers.
Base files match builder-outbox exactly, so no copying needed. Disk has 13 GB free. Now I'll probe base behavior with original wordings before writing the panel.
Base probe reveals key behaviors. Now probing yes/no forms, all-single-word chains, and more backwards wordings.
Key finding: base 291 cannot do two-hop chains or yes/no questions (clarifies), but handles backwards, corrections, one-hop, and abstains cleanly. Checking one spec detail — what `loop.ears.last_stage` reports:
`loop.ears.last_stage` works directly. Now writing the panel generator with 80 original items.
Load is 150 (limit 60) — waiting before the heavy base run.
Load is 51 (< 60), disk 12 GB free. Starting the single-process base run.
All setups store as intended, zero failures. Running the sealed scorer:
All 80 items use two-word names (spec needed ≥20). Writing the category-level README:
Done. The panel folder is on disk (git-ignored like all `artifacts/`, so no commit or push per the rules).

**Verdict: PANEL COMPLETE, base 291 scored 35 right / 0 wrong / 45 miss out of 80. Zero wrong answers: every base failure is a clarify or an abstain, never a confident error.**

Marks table (integer counts, sealed scorer):

| family | n | right | wrong | miss | question writes |
|---|---|---|---|---|---|
| chain_verb | 12 | 0 | 0 | 12 | 0 |
| backwards_bug | 10 | 8 | 0 | 2 | 0 |
| yesno | 14 | 0 | 0 | 14 | 0 |
| mixed | 12 | 3 | 0 | 9 | 0 |
| broken_chain | 8 | 0 | 0 | 8 | 0 |
| forward_control | 10 | 10 | 0 | 0 | 0 |
| statement_control | 8 | 8 | 0 | 0 | 0 |
| correction_control | 6 | 6 | 0 | 0 | 0 |
| TOTAL | 80 | 35 | 0 | 45 | 0 |

Every move, category level only:
- All 12 two-hop asks miss: the base answers with a clarify, naming nobody.
- 8 of 10 backwards asks hit (whose-ask and what-did-write/compose kinds, across spouse, author, founder, parent, composer). The 2 misses are the married-asks, which come back as a non-answer; they name nobody, so miss, not wrong.
- All 14 yes/no asks miss (5 yes, 5 no, 4 unknown): the base clarifies on every yes/no form.
- Mixed: the 3 backwards-asks about chain values hit; the 3 chain yes/no, 3 two-step-after-correction, and 3 yes/no-after-correction miss (all clarifies).
- All 8 broken chains miss via clarify (the clarify carries no don't-know marker, so it is a miss, not right).
- All 10 forward controls and all 8 statement controls record base behavior identically (right by the control rule). All 6 correction controls hit.
- No question turn wrote a fact anywhere (0 writes). All 80 setups stored exactly the intended triples, corrections replaced old values, statement questions stored nothing new. Pilot storage check: 0 failures.

Deviations and notes:
- Waited for shared-Mac load to fall below 60 before the base run (about 40 minutes of waiting); ran one process at a time, CPU only. Disk stayed above 12 GB free throughout.
- The base scripts and config in this worktree were byte-identical to origin/builder-outbox, so nothing was copied; drivers import them read-only and use the module default config with a fresh temp state dir per item.
- PUSH line: the folder `artifacts/claude-mixpanel292-20260923/` (panel.jsonl, base291.jsonl, make_panel.py, run_base.py, score_panel.py, README.md, SEAL.sha256.txt, seal verified OK) is in place on disk, uncommitted, per the no-commit/no-push rule.

What it means, in plain high-school English: the base is honest but limited. It answers direct one-hop questions, most backwards questions, and corrections, and it never guesses. It cannot do two-step reasoning or yes/no questions at all yet, so this panel leaves a big, clean gap for merge 292 to close.

What it doesn't mean: it doesn't mean the base is broken or the panel is unfair. A blind panel is a measuring stick, not a test the base is supposed to pass. And the 45 misses are all "I don't understand / I don't know" style non-answers, which is exactly what you want from a base that doesn't know something.
