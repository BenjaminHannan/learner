# Exp 147 PASSMARKS — mention-walk alignment (sealed BEFORE any registered run)

Director-confirmed bug (doc 143; every lineage since loop102, incl. the
integration base loop134): after teaching "Joren Hale is married to Petra
Voss" + "Petra Voss is a citizen of Litora", "Who is Joren Hale married
to?" and "Who is the spouse of Joren Hale?" get "I didn't understand
that" (possessive "Who is Joren Hale's spouse?" works). Cause: the N-hop
composer walks to the chain's sink and its coverage gate only checks
walked-subset-of-mentioned (`scripts/fable_bench92_english_arm.py:198-240`,
2-hop sibling in `fable_bench73_english_arm.py`); the same one-sided gate
produces class-3 prefix answers and class-4 cue-stem mismatches.

THE ONE CHANGE (question side only; teach path and everything else
byte-identical, wrapped never edited): walk only while the next hop's
relation is one the question mentions, stop at the first unmentioned hop,
and answer only when the walked prefix is fully mentioned, the wh-word's
answer class fits the terminal hop, and no extra mentioned relation is
live (full rule + mention-definition deltas in
`scripts/fable_align147_compose.py`, new, prefix-owned); otherwise None
and the existing fallback/abstain path acts. Mixin on loop134
(`scripts/fable_loop147_agent.py` + `loop147-config.json`), same mixin on
loop113e (`scripts/fable_loop147_agent113e.py`) and loop132
(`scripts/fable_loop147_agent132.py`). No existing file is edited.

## Frozen modules (sha256 at freeze, before this seal)

(listed in SEAL.sha256.txt alongside PASSMARKS.md, the A2 case file and
the three configs)

## Registered runs (Mac CPU, offline, `export OMP_NUM_THREADS=1
MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with
torch --with numpy python -B ...`)

- A1: sealed 143 cases re-run on the loop132 variant by importing
  `scripts/fable_redteam143_run.py` read-only with its ART output path
  redirected to this artifact dir (case file + judge unchanged).
- A2: `scripts/fable_align147_a2.py --variant all` on the sealed
  `fable_align147_a2_cases.json` (48 dialogues: 23 answer / 25 abstain).
- A3: `scripts/fable_align147_bench.py --variant all` (bench121-new,
  bench121-old, fable-edit-200, s2fresh-4hop, bench132-new; base + variant
  per item, scorer v2).
- A4: `scripts/fable_marks123_all.py --agent <variant> --config <config>
  --out <this-dir>/marks-<v> --workers 4` per variant.
- A5: every registered run < 1500 s wall-clock; daemon wrappers take
  --idle-seconds (30.0 in-process default here).

## Scorer (unchanged everywhere)

143 judge (abstain markers + extracted-value match) from the sealed runner;
A2 same markers + v2 extraction; benches scorer v2; marks123 judges
unchanged. Every seed/case reported, never averaged.

## Marks (integer counts, every case reported)

| Mark | Pass condition |
|---|---|
| A1 143 on loop147-132 | every class-3 (A1/U1-U5/K8/S4/T4/L4) and class-4 (K6/K10) case abstains; every sub-walk-suffix MISSED case (P1/P2/Q1/Q2/D2) answers its sealed value; 0 cases that were OK get worse |
| A2 new probe (48) | 23 suffix answers + 25 short-chain abstains on all three variants; 0 wrong answers |
| A3 bench per-item vs base | 0 new wrong on every (variant, split); correct lost only for items predicted below |
| A4 marks123 vs base | every suite identical to the same base's sealed report except items predicted below |
| A5 timing | every registered run < 1500 s |

## Predictions (written before the registered runs; dev-calibrated)

- P147.1: A1 meets its bar exactly (17 fixed, 0 worse). 0.85.
- P147.2: A2 48/48 OK on all three variants with 0 wrong. 0.90.
- P147.3: A3 has 0 new wrong on all 15 (variant, split) pairs. 0.80.
- P147.4: A3 correct-lost is EMPTY on all 15 pairs. 0.85.
- P147.5: A4 moves vs sealed bases are exactly the lists below. 0.80.
- P147.6: every registered run < 1500 s (dev slowest: marks123 ~500 s
  under shared-machine load). 0.90.

## Dev-calibrated move lists (frozen before seal; registered must match)

A3 correct-lost (base correct -> variant non-correct; 0 wrong): NONE on
any of the 15 (variant x split) pairs (dev: 3000/3000 items, 0 new
wrong, 0 lost, 0 fixed).

A4 suite moves vs sealed base reports (per-case verdict level):
- P2 loop147 (134-base) and loop147-132 (132-base): 0 OK->BUG, 0
  still-BUG (the 4 sealed bugs B7/D8 ok_to_bug and B7/C2/C5/D8 still_bug
  all become OK). P2 loop147-113e: 0/0 identical to its clean base.
- P3/P4/q1/bench/rt81/sleep/soak/q4: per-case identical to each base,
  with exactly these predicted differences: q4 on loop147-132 leaks
  exactly the base leak set plus `capital_in_2019` (D8 qualifier reply
  "I don't know Poland's capital_in_2019", an abstain); rt110/soak may
  show mailbox-race signatures seen in dev ("I didn't catch anything"
  on P5/L3 empty/long turns; one lost teach pair under kill-9 on soak)
  -- if a registered rt110/soak shows ONLY such a race signature with
  0 wrong writes, that suite is re-run once in the open and both runs
  are reported (precedent: exp 135 D1, exp 138c brief).
- rt81: 61 OK / 0 BUG / 13 UNCLEAR wording-drift on all three variants,
  per-case identical to the sealed loop134 pattern (version-pinned
  expectations, per exp 123).
- sleep: SKIP with printed reason on all three (no sleep path).
- soak base expectation: 0 lost / 0 wrong / 0 doubled.
- q1 loop147: F5+M5 OK (as base); q1 loop147-113e/132: F5+M5 FAIL
  (as their bases: no please-space/shouted fixes on those lineages).

A registered FAIL is recorded as FAIL, never re-run into a pass.
One diagnosis note is kept in RESULTS.md.
