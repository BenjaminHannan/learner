# Scorer-consistency audit (reasoning line) — 2026-09-23

Question: did any registered verdict besides 138n's M7 compare arms scored by different runners or scorers?
Method: READ-ONLY. No agent code changes, no panel runs, no training, CPU only.
Every file named below was read from `origin/main` (`git show`), never checked out/merged/pushed.
Panel item text was never opened and nothing is quoted: ids, flags and counts only.
Runners/scorers identified from each piece's RESULTS.md deviations + PASSMARKS.md + SEAL.sha256.txt + script docstrings.
Counts rechecked from saved rows/score JSONs (flags only) with `uv run --offline` python; no re-runs.

Background: `design/v3/30-modes/138nb-inverse-diagnosis.md` proves 138n's M7 on tablepanel221
compared 138n rows scored by the plain runner `scripts/fable_fix221_panel.py`
against 221's registered rows scored by `scripts/fable_fix221_panelmap.py`
(which splits multi-answer gold "A; B" on "; " and requires ALL parts).
That mismatch alone made 3 correct answers count as wrong.

## Verdict first

**Only one mismatch in the whole set: 138n M7 / tablepanel221 (the known one).**
Base scorer `fable_fix221_panelmap.py`, new-arm scorer `fable_fix221_panel.py` → NOT the same.
Under one consistent scorer (the registered panelmap scorer, per the 138nb recount:
fresh 221 arm 66 right / 0 wrong matching registered 91/91; 138n 79 right / 0 wrong),
the M7 bars `lost_to_wrong` (2) and `new_wrong` (3) both go to 0.
So the tablepanel221 M7 FAIL would flip to PASS on those bars if rescored consistently.
Per the rules the registered FAIL stays FAIL on the record; 138nb is its diagnosis.

**Every other comparison audited uses the same runner and scorer on both arms.
No other verdict could flip on scorer-consistency grounds. Integer counts below.**

## Audit table

| experiment | panel / comparison | base (registered) scorer | new-arm scorer | same? | could it flip a verdict? |
|---|---|---|---|---|---|
| 138n | tablepanel221 (M7) | `scripts/fable_fix221_panelmap.py` (registered 221 rows `artifacts/claude-tableask221-20260922/p1panel/rows.jsonl`; splits "; ", ALL parts required) | `scripts/fable_fix221_panel.py` via `scripts/claude_138n_m7.py run221` (plain runner, literal "A; B" match) | n | **y** — ids `p221-059#2`, `p221-066#2`, `p221-070#2`. Saved-row flags: registered 66 right / 0 wrong; 138n-as-scored 77 right / 3 wrong (`lost_to_wrong` 2, `new_wrong` 3). Consistent-scorer recount (138nb): 138n 79 right / 0 wrong, 0 new wrong. Bars go 2,3 → 0,0. |
| 138n | tablepanel221b (M7) | `scripts/claude_qnorm221c_run.py` one sealed scorer, arm `221c` in `artifacts/claude-qnorm221c-20260922/panel/rows.jsonl` | same `scripts/claude_qnorm221c_run.py`, arms `n`/`m` in `run/tablepanel221b/out` | y | n — m7 flags: registered 54/0, 138n 85/0, 0 new wrong, 0 writes. |
| 138n | teachpanel229 (M7) | `scripts/claude_teach229_run.py score`, registered `runs/panel-score.json` col `229` | same script+base (`runs/panel-138i.jsonl`), cols `229` in `score-n/score-m.json` | y | n — registered wrong 7, 138n wrong 6 (subset), 0 new wrong, 0 new wrong-writes. |
| 138n | namepanel232c (M7) | `scripts/claude_fullname232c_score.py`, registered `registered/panel-score.json` | same script+base (`panel-138i-A.jsonl`, `base138i.jsonl`, counts 36/36/8/4) | y | n — 80/80 right both arms, 0 moves of any kind. |
| 138n | firstnamepanel236 (M7) | `scripts/claude_firstname236_score.py`, registered `panel-score.json` | same script+base (`panel-rows221.jsonl`) | y | n — 60/60 right both arms, 0 moves. |
| 138n | aliaspanel237 (M7) | `scripts/claude_table237_score.py` + `fieldmap.json`, registered `m1panel/score237.json` | same runner `claude_table237_run.py` + same scorer + same `base221.jsonl`/`fieldmap.json` | y | n — registered 65/1, 138n 68/1 (same 1 wrong item), gained 3 miss→right, 0 new wrong. |
| 138k | frozen suites vs 138j (K3) | `fable_suitediff218` + `claude_merge138k_score.py` / `rt143nogate` / probe, base = 138j sealed rows | same tools on 138k rows | y | n — 0 moves everywhere (rt136 0, rt143 0, sessions152 0, bench 800 0, marks123 0), GATE clean, bench×3 4/4 identical. Filename-only issues none. |
| 138l | pieces' cases (L1) + suites vs 138k (L2) | `scripts/claude_138l_l1.py` + `claude_138l_score.py` applied to own/138k/138l arms identically; suites same `fable_suitediff218` | same | y | n — L1 76 predicted exact, 0 unpredicted; L2 moves (rt136 13, bench 25, marks123 27, rt143-nogate 4) all predicted, exceptions proven identical 13/13 + 25/25 to 222's rows. rt136 dual-compare deviation is label-source only, direct row check agrees (C019–C031). |
| 138m | pieces' cases (M1) + suites vs 138l (M2) | `scripts/claude_138m_l1.py` + `claude_138m_score.py`, all arms identically; suites same suitediff | same | y | n — M1 208 predicted exact, 990/990 sealed rows reproduced; M2 all moves predicted (sessions152 11, bench 5, marks123 6, rt136 15, rt143-nogate 37 reply-only, 0 verdict flips on rt143 except 5 MISSED→OK/S5 noted with 0 bad); exceptions identical 63/63 field-by-field (seconds excluded, declared). |
| 252c | corrtail258 (M1) + dev + corrpanel252 (M4) | `scripts/claude_merge252c_score.py` (imports `claude_bound259_score.py` rules) on 252b/258/259/252c rows identically | same | y | n — M1: 0 lost (every item right on 258 or 259 right on 252c; 54 total), 1 known new-wrong `t258-026` is a predicted merge-behaviour gap, not a scorer gap; M4: 1 move `c252-022` exactly per sealed rule. |
| 258 | corrtail258 (M1, blind, 80) | `scripts/claude_comment258_score.py` panel mode on mine + in-session base252b rows; keep/control identity vs writer `base252b.jsonl` | same scorer both arms | y | n — 23 diffs all toward right-or-same (16 became right), 0 new wrong/junk/false; keep 8/8 + control 16/16 identical. |
| 259 | corrtail258 (M1, blind, 80) | `scripts/claude_bound259_score.py` panel mode, both arms | same | y | n — newly right `t258-002/010/011/035`, 0 newly wrong; M3 `c252-022` move is a declared scorer/fix wording gap ("anymore"), not a cross-arm scorer gap. |
| 260 | openpanel260 (M1, blind, 80) | `scripts/claude_260_panel.sh` + `scripts/claude_openers260_score.py`, arms 260 + 138m in same pass; fidelity vs writer `base138m.jsonl` 80/80 | same | y | n — 260 right 80/80 vs 138m 38/80; 42 moves all toward right, 0 against, 0 junk/question writes. |
| 237 | aliaspanel237 (M1, 80) | `scripts/claude_table237_run.py` + `scripts/claude_table237_score.py` + `m1panel/fieldmap.json` (names only); base = writer `base221.jsonl`; suite base = byte copies in `base221rows/` (shas sealed) | same runner/scorer for 237 + fresh 221 arms | y | n — copies are byte-for-byte (sealed shas); trap item `a237-070` gives same reply on `base221.jsonl` and fresh 221 arm (stack behaviour, not scorer gap). |
| 237b | aliaspanel237b (M1, 80) | same 237 runner (hash sealed, unchanged) + `scripts/claude_table237b_score.py`; 221 arm reproduces base221 80/80 | same | y | n — 0 wrong added, 0 writes; 15 gained miss→right; 22 misses all abstains. |
| 236 | firstnamepanel236 (M1, 60) | runner `scripts/claude_fullname232_run.py` + `scripts/claude_firstname236_score.py`, arms 236 + fresh 221; writer `base221.jsonl` cross-checked | same | y | n — fresh 221 agrees with writer base 60/60 replies + 60/60 stored; M1a–g all pass. Suite base copies renamed only (tool filename search), bytes sealed. |
| 232c | namepanel232c (84) | runner `scripts/claude_fullname232_run.py` + `scripts/claude_fullname232c_score.py` + `base138i.jsonl` + counts 36/36/8/4; cross-check writer `base138i.jsonl` vs own 138i-A 84/84 | same | y | n — 36/36 multi right vs 138i 0/36; reruns 0 diffs. M3 route deviation (`--base 138i` + declared 232 move set because `--base-dir 232` skips rt136/rt143 on filenames) uses the same suitediff scorer; sessions152+bench vs 232's rows 0 moves. No flip. |
| 229 | teachpanel229 (100) | `scripts/claude_teach229_run.py run+score`, arms 138i + 229 same pass | same | y | n — 23 newly RIGHT + 2 direction-mismatch WRONG (`t229-009`, `t229-011`, canonical-direction vs gold-direction, declared); suites 1 predicted reply-only move (C115). |
| 221b | fresh panel221b (120) | `scripts/claude_221b_run.py` ONE sealed scorer, arms 138i+221+221b same pass | same | y | n — +23 (62 vs 39), 0 wrong, 0 writes, 0 lost; M3 1 known-flake move `bench132-4hop-160` (correct→abstain, 5/5 correct on rerun), counted as FAIL per rule, not a scorer gap. Yes/no-"no" scorer flaw disclosed, affects no bar (replies byte-identical). |
| 221c | panel221b reuse (120) | `scripts/claude_qnorm221c_run.py` ONE sealed scorer, arms 138i+221+221c interleaved per item; suite base copies sha-equal (`base221-copy.sha256.txt`) | same | y | n — 7 normaliser fires (5 fixed + 2 still-miss), 0 wrong, 0 writes, 0 lost; suites 0 moves. |

## What it means (plain high-school English)

- Think of each test as graded by one answer key. For 14 of the 15 experiments, both the old
  version and the new version were graded with the same answer key, so the score comparison is fair.
- The only unfair comparison is 138n's tablepanel221 check: the old 221 answers were graded with
  the fixed answer key (knows "A; B" means both names needed), while the new 138n answers were
  graded with the unfixed key (looks for the exact text "A; B"). Three right answers got marked wrong.
- With the fixed key on both sides, those 3 become right, and that one FAIL becomes a PASS on its bars.
  The official FAIL label still stays in the record book (rules), with this note as the explanation.

## What it doesn't mean

- It does not mean 138n is perfect: the same recount confirms 8 more items went from right to silent
  (4 backwards-questions missing the "(worked out backwards)" label, 4 self-questions changed on purpose
  by the identity layer). Those are real behaviour gaps for the 138nb follow-up, not grading errors.
- It does not mean any other PASS/FAIL flips: every other bar was graded with one key on both arms,
  and the saved-row flags confirm the published counts. Filename renames (rt136/rt143 copies) are
  byte-identical copies, not different keys.
- It does not mean the panels were re-read or re-run: no panel ran here, no item text was opened,
  and this audit changes no verdict except explaining the one known mismatch.

## Deviations / notes

1. PUSH: the task says "PUSH: artifacts/claude-scoreraudit-20260923" but OPUS-RULES (which the task
   says applies in full) says "No git commits, PRs or pushes." So nothing was committed or pushed;
   `artifacts/claude-scoreraudit-20260923/AUDIT.md` is left as a new uncommitted file in this worktree.
2. Additive-only kept: one new directory + one new file; no existing file edited or deleted.
3. Machine: 1-min load ~56 at start (limit 60 applies to heavy runs; this task is read-only —
   `git show` + flag-counting python only, one at a time). Free disk 16–17 GB (stop bar 3 GB, OK).
4. Worktree already contained other agents' uncommitted changes (e.g. modified
   `artifacts/fable-predictions-ledger.md`); they were not touched.
5. TEST-ONLY panels: never read item by item, never tuned on, never quoted. Row/score files were
   read for flag/count fields only (ids, right/wrong booleans, family labels, bars).
