# 54 — Mode scheduler + 10-minute demo — RESULTS

**Registered runs 21 Sep 2026. PASSMARKS sealed before any run. SCORE: PASS (S1–S5, D1–D6).**

## Frozen sources (sha256)

```
ce7516146385fe91635b60ebadbb5f06f1a95c0a8ee5d0d9301b0b87b89f54ba  scripts/fable_modes54_scheduler.py
de80e7bca8fc7bc84e88308da4985427f19edb68fbf5a96654c397a019441333  scripts/fable_modes54_demo.py
```

PASSMARKS seal: `1c56ecf9d3f45a153d39b36a5856716a1652bab8241326a7a479cc1caab72384`.

Exact commands (Mac CPU, no install):

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 python -B scripts/fable_modes54_scheduler.py --selftest
uv run --offline --no-project --python 3.12 --with torch --with numpy \
  python -B scripts/fable_modes54_demo.py --out artifacts/fable-modes54-20260921
```

## Part A — scheduler conformance (registered `--selftest`)

| # | mark | threshold | result |
|---|---|---|---|
| S1 | ours passes suite | ≥ 34/34 | **PASS — 34/34** |
| S2 | naive always-THINKING fails | ≥ 12/34 | **PASS — fails 30/34** |
| S3 | mode log fields + counts | 100% | **PASS — 0 / 0** |
| S4 | CREATIVE exits / ask-once | 0 violations | **PASS — 0 / 0 / 0** |
| S5 | SLEEP entry + no commit-after-abort | 0 violations | **PASS — 0 / 0** |

Naive passed only the four scenarios that never leave idle THINKING (s01, s19, s30, s31).

## Part B — demo (registered run, one clean invocation)

Notebook side deterministic; baseline seeds 5401 / 5402 / 5403 reported separately.

### Marks

| # | mark | result |
|---|---|---|
| D1 | notebook Q1, Q2, Q3 | **PASS — 3/3** |
| D2 | notebook abstentions Q4, Q5, Q6 | **PASS — 3/3** |
| D3 | Q9 cites ≥3 source tags and ≥3 mode-log entries | **PASS — 4 tags, 8 log lines** |
| D4 | baseline completes 3/3 seeds with 9 integers each | **PASS — 3/3** (104,832 params each) |
| D5 | teaching lines byte-identical to baseline story | **PASS — True** |
| D6 | all five modes in demo mode log | **PASS — CREATIVE, LISTENING, SLEEP, THINKING, WORK** |

### Outcome integers (never averaged)

| qid | gold | notebook | base5401 | base5402 | base5403 |
|---|---|---|---|---|---|
| Q1 | Ana | 1 | 1 Ana | 1 Ana | 1 Ana |
| Q2 | Porto | 1 | 1 Porto | 1 Porto | 1 Porto |
| Q3 | Paris | 1 | 1 Paris | 1 Paris | 1 Paris |
| Q4 | ABSTAIN | 1 | 1 | 1 | 1 |
| Q5 | ABSTAIN | 1 | 1 | 1 | 1 |
| Q6 | ABSTAIN | 1 | 1 | 1 | 1 |
| Q7 | Paris | 1 | 1 Paris | 1 Paris | 1 Paris |
| Q8 | green | **0** | **1 green** | **1 green** | **1 green** |
| Q9 | self-report | **1** | 0 | 0 | 0 |
| **total** | | **8/9** | **8/9** (loss 0.0007) | **8/9** (0.0008) | **8/9** (0.0007) |

Q8 is the designed place the text model wins: the notebook still refuses (two Miras + relation taught as `colour`, not `favourite`) while the drilled transformer emits `green`. Q9 is the designed place only the notebook can score (source tags + mode log). Totals tie at 8/9; neither side sweeps.

Mode log of the demo (8 transitions): start THINKING → LISTENING (turns) → CREATIVE/WORK (J-show FOUND round 2, wrote one `proposed`) → CREATIVE/THINKING (J-stuck GIVE-UP at round 11, one ASK_BEN) → SLEEP (memory-full) → THINKING (commit, memory 0). Parked question: `Q-J-stuck`.

### What it means

- This rule-based scheduler conforms to its own 34 frozen scenarios and cleanly discriminates from an always-THINKING foil (30/34 fails).
- On this fixed script the notebook answers 1-hop/2-hop/correction/alias, refuses hearsay and ambiguity, and produces a structured self-report from real source tags; the plain transformer, trained on the same eight pairs, matches on content and wins only Q8.

### What it does not mean

- Not learned switching, not long-run stability, not broad English, not GPU-scale training. Golden transcripts vs a same-author script are conformance, not competence. One demo script; no claim beyond these runs.

## Deviations from PASSMARKS / plan

1. **Per-question story prefix, not one identical story blob for every item.** PASSMARKS said the baseline sees “the same story text for every item”; Q3 (`Where does Mira live?` → Paris, after `correct`) and Q6 (same English, ambiguous) cannot share one prefix. Each item uses `BEN_LINES[:prefix]` cut at the correct script offset; prefixes are byte-prefixes of the one master story. D5 still asserts notebook-heard lines == `BEN_LINES`.
2. **Q8 notebook line is `ask Mira favourite` (frozen in PASSMARKS).** After the second `person Mira` the name is still ambiguous at Q8, so the notebook’s Q8 reply is AMBIGUOUS rather than MISSING_FACT on the paraphrase key; gold stays `green`, mark stays 0. The designed baseline win is unaffected.
3. No other intentional deviations. A registered FAIL would have been reported as FAIL (none occurred).

## Predictions (ledger P210–P213, written before the runs)

- P210 scheduler ≥34/34 and naive ≥12 fails → **TRUE** (34/34; 30 fails).
- P211 notebook Q1–Q7 7/7 and Q9 ≥3 tags + ≥3 log lines → **TRUE** (7/7; 4 tags, 8 log lines).
- P212 baseline wins ≥1 question in ≥2/3 seeds → **TRUE** (Q8, 3/3 seeds).
- P213 baseline total below notebook in ≥2/3 seeds → **FALSE** (tie 8/9 on all three seeds).

## Files

- `PASSMARKS.md`, `SEAL.sha256.txt` — sealed marks and procedure
- `registered-selftest.txt`, `registered-demo.txt` — verbatim registered stdout
- `demo-results.json`, `mode-log-demo.json`, `demo-transcript.txt`
- `DEMO-SCRIPT.md` — one-page script for Ben’s uncle-and-dad run
- Design: `design/v3/30-modes/54-modes-and-demo-opus.md`

## Questions for Ben

None blocking. One optional follow-up: after J-stuck’s ASK_BEN, do you want the demo to show `resolve_question` re-queueing the job, or leave the parked question visible for the live Q&A?
