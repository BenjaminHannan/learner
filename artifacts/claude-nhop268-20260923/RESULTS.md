# Exp 268 results: n-hop direction guard on 138m

## Result first

**FAIL** — on M1 only, and on one clause of M1: `reverse_chain` is 10/24
right on 268 (bar: >= 22/24). Every other clause of every mark passes.
The panel contains no item exhibiting the diagnosed bug: 138m's baseline
on the panel is already 0 wrong, 268's 70 rows are byte-identical to
138m's, and the guard (which only suppresses forward-walked nhop frames)
correctly fires nowhere. One diagnosis note below; no silent re-runs
(one run per arm; no re-seal; sealed files unchanged, seal re-checked OK
after all runs).

## Marks table (integer counts; 138m's number beside every figure)

| mark | 138m | 268 | bar | verdict |
|---|---|---|---|---|
| M1 reverse_chain right /24 | 10 | 10 | >= 22 | **FAIL** |
| M1 reverse_chain wrong /24 | 0 | 0 | 0 | pass |
| M1 reverse_nochain right kept (of 4 right on 138m) | 4 | 4 | keep all | pass |
| M1 reverse_nochain wrong /10 | 0 | 0 | — (0 overall) | pass |
| M1 uncued_reverse identical /8 | 8 | 8 | 8/8 identical | pass |
| M1 forward_chain identical /12 | 12 | 12 | 12/12 identical | pass |
| M1 forward_1hop identical /10 | 9 right + 1 miss | same 9 + same 1 | identical | pass |
| M1 abstain identical /6 | 3 right + 3 miss | same 3 + same 3 | identical | pass |
| M1 wrong over all 70 | 0 | 0 | 0 | pass |
| M1 question writes over all 70 | 0 | 0 | 0 | pass |
| M1 per-item rows identical /70 | — | 70 | — | pass |
| DEV moves 138m→268 (predicted list) | — | 21/21 exact | exactly predicted | pass |
| SUPP moves 138m→268 (predicted list) | — | 3/3 exact | exactly predicted | pass |
| DEV+SUPP teach/triple changes | — | 0 | 0 | pass |
| DEV+SUPP new wrong values | — | 0 | 0 | pass |
| M2 sessions152/bench/marks123 moves | — | 0/0/0 | 0 | pass |
| M2 rt136 labels | — | C019–C031 + C076 + C079 (15) | exactly | pass |
| M2 rt136 direct rows vs 138m (145) | — | 0 moved | [] | pass |
| M2 rt143 moves / flips (124) | — | 0 / 0 | 0 | pass |
| M2 63 inherited 222 rows identical | — | yes | yes | pass |
| M2 forward n-hop moves | — | 0 | 0 | pass |
| M3 restart probes rows equal (5 files) | — | 5/5 | 5/5 | pass |
| M3 verifier probes diff (98) | — | [] | [] | pass |
| M3 verifier supp diff (12) | — | [] | [] | pass |
| M3 ghost answers / dup fails / write changes | — | 0 / 0 / 0 | 0 | pass |
| M4 median(268) − median(138m) | — | −0.003 ms | <= +5 ms | pass |

Panel per-item right ids (identical on both arms; ids only, no text):
- reverse_chain right (10): n268-001, n268-003, n268-013, n268-015,
  n268-017, n268-018, n268-019, n268-022, n268-023, n268-024.
- reverse_nochain right (4): n268-025, n268-029, n268-030, n268-031.
- uncued_reverse right (8): n268-035 … n268-042 (all 8).
- forward_chain right (12): n268-043 … n268-054 (all 12).
- forward_1hop right (9): n268-055, n268-056, n268-057, n268-058,
  n268-059, n268-061, n268-062, n268-063, n268-064 (miss: n268-060).
- abstain right (3): n268-065, n268-069, n268-070
  (miss: n268-066, n268-067, n268-068).
- wrong ids on either arm: none. question_wrote ids: none.

## Every move (dev + supp; panel: none)

21 dev question-turn moves, all reverse-shaped, 0 teach changes
(stage 138m → 268; wording class only):
- to 190 gold (4): d01-anchor-spouse-whose#t2, d03-spouse-whose#t2,
  d29-spouse-3link#t3, o02-spouse-who-has-as#t2.
- to "Was that a question?" (2): d02-anchor-spouse-married#t2,
  d04-spouse-married#t2 (no layer parses married-to).
- to 190 honest decline (3): d05-spouse-husband#t2, d06-spouse-wife#t2,
  o04-spouse-partner#t2 (stored key is "spouse").
- to honest abstain (7): d11-anchor-author-whatwritten#t2,
  d12-author-whatwritten#t2, d16-founder-whatfound#t2,
  o01-spouse-was-married#t2, o20-author-3link-whatwritten#t3,
  o28-spouse-whose-was#t2, o29-author-past-perfect#t2.
- to true 153-wording fact naming the gold subject (5):
  d33-author-whose#t2, d34-founder-whose#t2, o09-author-whose#t2,
  o15-employer-whose#t2, o18-child-whose#t2.
3 supp moves: p01-founder-whatfound#t2 (→ abstain),
p02-founder-whose#t2 (→ 153-wording), p04-founder-what-has-founded#t2
(→ abstain). p03/p06/p07 forward gold identical; p05 no-chain identical.
184/205 other dev turns byte-identical, including all teaches, all
forward/uncued/2-subject controls, and the d13/d17 forward over-walks
(unchanged, as designed: not in 268).
Panel: 0 moves (70/70 rows byte-identical 138m vs 268).
M2/M3/M4: exactly the predicted empty sets (see table).

## The one diagnosis note (why M1 bar 1 fails)

Stage census on the panel (both arms, from the sealed scorer output):
reverse_chain items sit at loop153-reverse (8 right), loop190-reverse
(2 right), none (12 miss), bench73 (2 miss) — **zero** at loop138-nhop.
The diagnosed bug needs a same-relation cued chain that the composer can
walk forward from the asked value; the panel's chains never present such
a frame (they branch, mix relations, name two subjects, or use cue-less
relations — the composer returns None and 190/153 answer or abstain).
With no forward-walked frame anywhere, a frame-suppressing guard is
provably a no-op: 268 == 138m on all 70 items, so reverse_chain stays at
the baseline 10/24 instead of reaching 22/24. The guard itself works
exactly as specified where the bug exists (dev: 21/21 reverse framings
blocked, 0 forward n-hop changes, 0 new wrong values, 0 write changes).
Fixing the 14 panel misses would need answering layers (wider 190
relation set, married-to parsing), which is a different change from the
specified one-change fall-through, so it was not built.

## Deviations

- D1 (post-seal driver addition, reported with purpose; sealed files
  untouched, seal re-verified OK): `scripts/claude_268_panelrun.py`
  (new file) runs panel items once per arm into `run/panel-rows*.jsonl`,
  mirroring the panel's own `run_base.py` row-for-row; the sealed
  `score_panel.py` was used unchanged for both arms. Necessitated by the
  panel arriving after the seal; the task orders the panel run post-seal.
- D2 (pre-seal, in PASSMARKS): o11/o13/o25 teaches used an unparsable
  "The founder of X is Y." shape (empty notebook); kept as RECORD, and
  repeated with parsable phrasing as p01–p07 supplementals.
- D3 (pre-seal, in PASSMARKS): the design doc's "12/12 dev WRONGs flip to
  gold" (proposed on 138n, never built) does not hold on the 138m base:
  measured fall-through gives gold only for 190-answerable shapes (4/12);
  the rest become honest non-answers or true 153-wording facts. Stated
  before the seal, not hidden.
- No re-runs of any registered run; no re-seal; no panel item quoted;
  panel files copied unchanged (seal OK before and after).

## Falsifiers (none triggered)

- No reverse_chain item answered with V's own forward fact (wrong = 0).
- No forward n-hop reply change (dev controls + M2 bench + panel
  forward families all identical).
- No new wrong value anywhere (dev, suites, probes, panel).

## What it means (plain high-school English)

- Means: the safety switch works where the bug lives. On 70 practice
  dialogs, every backwards question that used to get a wrong forward
  answer now gets either the right answer or an honest "I don't know" —
  never a wrong answer. And it never changes a forward question, a
  stored fact, or any frozen test.
- Doesn't mean: the switch helped on the blind 70-question test — that
  test happened to contain zero questions with the bug (the base already
  made zero mistakes there), so the switch changed nothing and the
  22-out-of-24 target was missed (10 out of 24). It also doesn't mean
  every backwards wording now gets the right answer: some wordings still
  get an honest non-answer because the layers underneath can't say them.

## Files (left in the worktree for the director; no push per OPUS-RULES)

- `artifacts/claude-nhop268-20260923/` (PASSMARKS, config, predictions,
  SEAL.sha256.txt, run/ with dev, suites, probes, latency, panel rows +
  both sealed scores, RESULTS.md)
- `artifacts/claude-nhoppanel268-20260923/` (panel copy, seal OK)
- `scripts/claude_fix268_nhopdir.py`, `scripts/claude_loop268_agent.py`,
  `scripts/claude_268_devrepro.py`, `scripts/claude_268_supp.py`,
  `scripts/claude_268_runall.sh`, `scripts/claude_268_score.py`,
  `scripts/claude_268_panelrun.py`
- `artifacts/fable-predictions-ledger.md` (P268.1–P268.7 appended only)
