Fixing casual called/named misses — building the 281b follow-up from 281's fail.
Loaded the spec and 281's sealed design. Now setting up the work plan.
The 281 RESULTS tail is literally truncated in the file itself — noted, moving on. Now checking the driver interface for step 1 probes.
Interface confirmed. Writing the step-1 probe (casual forms on 281) in /tmp.
Step 1 done: 7 of 8 casual forms fail on 281 (only lowercase+`?` works). Now checking opener-splitting and triple-reading helpers for the fix design.
Design is clear. Checking 281's seal contents and run-dir files to mirror the layout.
Now validating two design assumptions with quick `--once` probes on the base arms.
Assumptions verified (never-taught no-apostrophe questions clarify/abstain honestly; `What's...called?` is unhandled by 281). Writing the one-change mixin now.
Now the 281b agent module mirroring 281's structure.
Now the 56-dialog dev set generator (step 2).
Load is 100 — too high to run anything now. Writing the remaining scripts while waiting for it to drop.
The runall content went to the wrong path — creating the missing `claude_281b_runall.sh` now.
All scripts in place. Doing a no-import syntax check while load is high.
Load dropped below 60. Smoke-testing the 281b build first.
Build works. Running dev pilot on both arms.
55/56 pilot. Inspecting the one miss (no panel text involved — my own dev).
Found it: `_fix_tok281b` returns early on the s-strip miss and never reaches exact-recase; also s-final subjects (`Nils`) need `'s` appended. Fixing pre-seal.
56/56 dev. Getting the exact move list for predictions.
Non-moves fully explained (281 already handles `?`-terminated lowercase/doyoucall/whats-nameof shapes). Checking 281's runtime precedent, then launching the pilot suite run.
Fast precedent (~100s). Launching pilot M2+probes vs 281's rows.
Pilot M2+probes PASS (0 moves, GATE clean, rt136 labels identical to 281's, probes 0/0). Marking progress and checking ledger numbering.
Now the mock-panel end-to-end test (exact schema + `user`-key variant).
`user_text` path verified. Now the `user`-key variant.
Gates verified. Writing predictions file and PASSMARKS.
Sealed 17/17, and the blind panel directory already exists. Checking only its seal (never its rows).
Panel seal OK — no wait needed. Appending ledger predictions, then the registered runs.
Registered M2+probes PASS. Running the blind panel once per arm.
M1 ran clean (seal OK, schema OK, teach 10/10 → panel valid). Result needs mechanical analysis — checking move counts first, text-free.
Zero moves — all 25 stored replies byte-identical. Running a text-free shape diagnosis (ids + boolean features only, never text/gold).
Diagnosis is solid at category level. Re-verifying the seal (post-run integrity), then writing RESULTS.
Fixing a stray non-English token I introduced in RESULTS.
**Verdict: FAIL** — M1 stored bar 9/25 (bar ≥ 23/25). Every other bar passes. One change worked exactly as designed; the panel's misses sit outside the briefed dimensions.

## Marks table (integer counts, 281's number beside every figure)

| bar | 281b | 281 | verdict |
|---|---|---|---|
| stored exact over denominator (25/25, 0 excluded) | 9/25 | 9/25 | FAIL (bar ≥ 23) |
| stored wrong answers | 0 | 0 | PASS |
| notstored abstain | 10/10 | 10/10 | PASS |
| ambiguous same as 281 | 10/10 | — | PASS |
| control same as 281 (5/5 right both) | 5/5 | — | PASS |
| teach stored (panel VALID, ≤ 2 fail) | 10/10 | 10/10 | VALID |
| M3 store diffs, all 60 turns | 0 | — | PASS |
| M3 question writes | 0 | 0 | PASS |
| M2 sessions152 / bench 4×200 / rt136 / rt143 | 0 / 0 / 0 / 0 moves, GATE clean | — | PASS |
| probes vp 98 / supp 12 vs 281 rows | 0 / 0 changes | — | PASS |

## Every move, every miss

- **Moves 281→281b on the panel: none.** 25/25 stored replies byte-identical; the 9 right ids are the same 9 on both arms → 0 abstain-ward flips, no 5× follow-ups needed.
- **Right (9):** d01#2, d02#1, d03#2, d04#1, d05#3, d06#1, d07#2, d09#2, d10#1 — all formal `?` wordings 281 already handles.
- **Miss (16, all abstain, 0 wrong):** d01#1, d01#3, d02#2, d02#3, d03#1, d03#3, d04#2, d04#3, d05#1, d05#2, d06#2, d07#1, d08#1, d08#2, d09#1, d10#2.
- **Diagnosis (shape categories only, panel never read item by item, nothing quoted):** 5 misses formalise fine (known-entity restore, 281 shape match) yet resolve to no stored triple — wording beyond casual typing. 11 match no called shape at all (2 carry no called cue whatever; rest keep a cue word in non-trailing/embedded wordings). None of the 16 is a briefed-dimension casual typing (case, apostrophe, whats, missing `?`) of a sealed shape — those all work (dev 34/34 stored, mock panel, 9 formal panel items).
- **Deviations:** none after the seal. 17/17 seal OK before and after all runs; panel seal OK; each command ran once per arm; schema gate + `user`-key path verified end-to-end on a mock panel pre-seal (missing-gold/bad-category mocks exit 3). Ledger P281b.1–P281b.4 appended (P281b.1 wrong on the stored figure only; P281b.2 right; no falsifier tripped).

## What it means / doesn't mean (plain high-school English)

- **Means:** casual typing of the covered questions now works (lowercase, no apostrophe, "whats", no `?`), with zero side effects — no guesses, no writes, suites/probes identical to 281. The panel fails because its missed questions reword the question itself, a different job than this experiment's one change.
- **Doesn't mean:** 281b is worse anywhere — every panel figure is equal-or-better, and it broke nothing. It also doesn't mean casual typing is solved in general (pronouns, multi-word subjects, embedded clauses stay out of scope by design), nor that stores are at risk (0 writes on all 60 turns).

**PUSH deliverables** (in place in the worktree, uncommitted — rules forbid commits/pushes): `artifacts/claude-called281b-20260923` (PASSMARKS, RESULTS, config, devcases, predicted_moves, SEAL 17/17, pilot, run), `scripts/claude_fix281b_casual.py`, `scripts/claude_loop281b_agent.py`, `scripts/claude_called281b_*` (devcases, run, score, regscore, panelrun, panelscore), `scripts/claude_281b_*` (runall, panel), `artifacts/fable-predictions-ledger.md` (+P281b.1–.4). Disk 11 GB free; load was respected throughout (waited out the 100+ spike before heavy steps).
