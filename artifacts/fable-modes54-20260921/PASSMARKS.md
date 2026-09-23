# 54 — Modes scheduler + demo — PASS MARKS (sealed BEFORE any registered run)

Written 21 Sep 2026 before any registered run of `scripts/fable_modes54_scheduler.py`
(`--selftest`) or `scripts/fable_modes54_demo.py`. Hashed in `SEAL.sha256.txt`.

Procedure: development runs may happen while writing the code; the REGISTERED run of
each script is the single clean run recorded in RESULTS.md, executed after the source
files are frozen (sha256 recorded in RESULTS.md). A registered FAIL is reported as FAIL
and is never re-run into a pass. Every seed is reported separately, never averaged.

## Part A — Scheduler conformance (`fable_modes54_scheduler.py --selftest`)

Suite: 34 scripted scenarios, frozen in the source before the registered run. Two
schedulers are run over the identical scenarios: ours (rule scheduler per docs 31/32/33)
and a naive baseline that is ALWAYS in THINKING (ignores inbox, jobs, memory — the
discriminating foil the brief requires).

| # | mark | threshold |
|---|---|---|
| S1 | our scheduler passes the suite | >= 34/34 scenarios |
| S2 | naive always-THINKING fails the suite | >= 12/34 scenarios failed |
| S3 | mode log: every applied transition appears exactly once with (from, to, reason); every entry has all three fields | 100% in our scheduler |
| S4 | CREATIVE: per job rounds <= 11 (the toy's KEEP_FIXED_N); every CREATIVE entry exits FOUND (resume WORK) or GIVE-UP (park job + exactly one question for Ben); 0 jobs silently dropped | 0 violations |
| S5 | SLEEP: entered only when inbox empty AND no runnable job; a pre-empted SLEEP never commits (memory unchanged on abort); 0 spends of memory after abort | 0 violations |

Registered run = one invocation of `--selftest`; both schedulers' integer counts go into
RESULTS.md verbatim.

## Part B — Demo (`fable_modes54_demo.py`)

One fixed script (teachings, questions, mode show-piece) executed once per registered
run. The notebook side is deterministic. The baseline side runs 3 seeds (5401, 5402,
5403), reported per seed, never averaged.

### The 9 frozen questions (both systems; gold fixed now)

| id | notebook line | english (baseline) | gold |
|---|---|---|---|
| Q1 | ask Mira mother | Who is Mira's mother? | Ana (1-hop) |
| Q2 | ask Mira mother city | Where does Mira's mother live? | Porto (2-hop) |
| Q3 | ask Mira city (after `correct ... Paris`) | Where does Mira live? | Paris (post-correction) |
| Q4 | ask Tom city (only hearsay exists, never taught) | Where does Tom live? | ABSTAIN |
| Q5 | ask Mira job (never taught) | What is Mira's job? | ABSTAIN |
| Q6 | ask Mira city (two Miras) | Where does Mira live? (ambiguous) | ABSTAIN |
| Q7 | ask Mira1 city (alias to first Mira) | Where does Mira1 live? | Paris |
| Q8 | ask Mira favourite (paraphrase; taught as relation `colour`) | What is Mira's favourite colour? | green |
| Q9 | self-report (know / how know / unsure) | — (baseline has no notebook or mode log) | structured self-report |

ABSTAIN = the system must decline to assert a value (notebook: MISSING_FACT or
AMBIGUOUS; baseline: the literal token `<ABSTAIN>`).

### Baseline protocol (frozen)

Minimal decoder-only transformer written inside the demo file (2 layers, d_model 64,
4 heads, word-level vocab, ~50k–200k params), plain PyTorch, CPU only. It is trained on
the SAME teaching lines (rendered as the same story text for every item) plus Q1–Q8 with
the golds above (Q8 gold = green; Q4–Q6 gold = `<ABSTAIN>`), full-batch Adam, lr 1e-3,
600 fixed updates, seeds 5401/5402/5403, greedy decode, max 8 answer tokens. Q9 is not
trainable for it (no notebook, no mode log) and scores 0 by construction, stated as such.
No seed is dropped or averaged. Training loss is not a score; only exact-match on the
9 questions counts.

| # | mark | threshold |
|---|---|---|
| D1 | notebook correct on Q1, Q2, Q3 (content answers) | 3/3 |
| D2 | notebook correct abstentions on Q4, Q5, Q6 | 3/3 |
| D3 | notebook self-report (Q9) cites >= 3 distinct notebook source tags AND >= 3 mode-log entries (t, from, to, reason) | pass |
| D4 | baseline runs all 3 seeds to completion and reports integers for all 9 questions per seed | 3/3 seeds |
| D5 | the teaching lines fed to the notebook are byte-identical to the story text fed to the baseline (assert in code) | pass |
| D6 | mode log of the demo run contains >= 1 entry each for LISTENING, WORK, CREATIVE, SLEEP, THINKING | pass |

Outcome marks (described, no threshold — reported as integers whatever happens):
notebook total correct /9; baseline total correct /9 per seed; per-question winner
table including any baseline win (Q8 is the designed place a text model can beat a
key-value notebook).

### What the marks can and cannot support

- S1–S5 support: "this rule-based scheduler conforms to its own 34 scripted scenarios
  and discriminates from an always-THINKING foil." Nothing about learned switching,
  usefulness, or long-run stability.
- D1–D6 support: "on this fixed script the notebook side behaves as designed and both
  sides' integers are on record." Nothing about broad English, GPU training, or any
  claim beyond these runs.
