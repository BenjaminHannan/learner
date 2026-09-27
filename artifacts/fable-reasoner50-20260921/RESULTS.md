# Experiment 50 — results (2026-09-21): the reasoner on the REAL notebook contract

**PASS, all five registered marks, no v2 needed.** Marks were written and hashed
(`SEAL.sha256.txt`, sealed 2026-09-22T01:00:18Z) before the registered wave; development
used throwaway seed 9999 and sampling tag `dev` only.  Sleep seeds **4131 / 4132 / 4133**,
one wave, no retuning; parity/scale deterministic, one run (tag `reg`).

## Marks (integer counts, every seed reported, never averaged)

| Mark | need | 4131 | 4132 | 4133 | single run |
|---|---|---|---|---|---|
| **S1** parity vs `Notebook.ask` (status AND every field) | 2700/2700, all 5 statuses in all 9 cells | — | — | — | **PASS 2700/2700**, all-5 present 9/9 cells |
| **S2** unknown-relation frames = MISSING_FACT, nothing invented | 90/90 | — | — | — | **PASS 90/90** |
| **D1** words installed by the Exp-46 gate | 9/9 | PASS 3/3 | PASS 3/3 | PASS 3/3 | — |
| **D2** 60-start audit vs true walk, wrong answers | 0 of 540 | PASS 0/180 | PASS 0/180 | PASS 0/180 | — |
| **D3** dense Exp-44 path vs protocol `answer()` disagreements | 0 of 540 | PASS 0/180 | PASS 0/180 | PASS 0/180 | — |

Also every seed: base probe **unchanged** after each install, weights-only **reload
identical**, base accuracy **1.000**, reuse **1.000 / 1.000 / 1.000** (120 frames/seed).

## The parity run (one run, 9 cells, 300 frames each)

Notebooks were built as contract `events.jsonl` files with valid hash chains and loaded
through the contract's own loader — up to 2 539 218 facts, 3 290 908 facts in total, one
file 919 MB.  Every frame was answered by both the reasoner and `Notebook.ask`:
| entities × relations | facts | agree | reasoner ms/q | contract ms/q | index build s | cache |
|---|---|---|---|---|---|---|
| 60 × 8 | 354 | 300/300 | 0.0021 | 0.021 | 0.001 | 0.02 MB |
| 60 × 80 | 4 057 | 300/300 | 0.0044 | 0.251 | 0.022 | 0.4 MB |
| 60 × 500 | 25 406 | 300/300 | 0.012 | 4.27 | 0.097 | 2.2 MB |
| 600 × 8 | 2 996 | 300/300 | 0.0040 | 0.165 | 0.016 | 0.2 MB |
| 600 × 80 | 39 746 | 300/300 | 0.014 | 6.94 | 0.28 | 5.2 MB |
| 600 × 500 | 253 521 | 300/300 | 0.016 | 45.8 | 0.997 | 21 MB |
| 6000 × 8 | 29 076 | 300/300 | 0.012 | 4.49 | 0.184 | 3.5 MB |
| 6000 × 80 | 396 534 | 300/300 | 0.017 | 74.4 | 2.88 | 51 MB |
| 6000 × 500 | 2 539 218 | 300/300 | 0.024 | 478 | 12.1 | 204 MB |

The contract scans every fact per hop (`current()` is O(facts)); the reasoner's lazy
per-relation views are a dict lookup.  Process peak RSS 7.64 GB (dominated by the
contract-side notebook).  Every cell contained all five statuses (6000×500: OK 164,
MISSING 67, BROKEN 25, AMBIGUOUS 20, UNKNOWN 24).

## Sleep (the real notebook, 20 taught episodes per word)

All nine installs passed the gate: OOF exact match 1.000 at the chosen checkpoint (100
updates for `maternal_grandmother`, 50 for the others), refit agreement 1.000, seen 1.000,
20 distinct people each.  Routed chains (all seeds; `keep` in the unused slot):
`maternal_grandmother` = mother→mother, `boss_of_spouse` = spouse→boss,
`doctor_of_mothers_friend` = mother→best_friend→doctor.  Wall-clock 6.4 / 6.7 / 6.4 s.

## Prediction outcomes (ledger P219–P223, written before the wave)

P219 **TRUE** (2700/2700, all-5 in 9/9).  P220 **TRUE** (9/9, 0/540).  P221 **TRUE**
(90/90).  P222 **FALSE** — times TRUE (reasoner 0.024 ms, contract 478 ms at 6000×500)
but cache 204.1 MB ≥ predicted < 200 MB.  P223 **TRUE** (0/540, reuse 1.000).  **4/5.**

## What this means

- The Exp-44 reasoner — skills as runtime lookups, hard-coded hop loop, 0.9 threshold,
  learned words as 27-number routers — **translates to the real contract unchanged**:
  on 2 700 deliberately nasty frames it is indistinguishable from the contract's own hop
  loop, field for field (broken chains, ambiguity, literals, multi-valued rows,
  corrections, retractions, quarantined sources).
- The open relation set is handled by construction, not training: identity routing plus
  lazy views keeps per-question time flat at tens of microseconds from 8 to 500 relations
  and 60 to 6 000 entities, while the reference degrades linearly (478 ms at the biggest).
- Sleep installs three new composite words from 20 raw taught episodes on a real
  notebook, gradient arithmetic on 27 numbers each, zero wrong installs in 540 audit
  checks — and the words then work inside longer chains.

## What this does NOT mean

- **Parity is shared-code evidence, not independence.** The view builder deliberately
  reuses the contract's `ANSWERING_SOURCES`, `active()` and sort order; the hop loop was
  re-implemented and could have diverged — that is what S1 tests — but a bug common to
  both would pass silently.  The contract's own 32-case selftest (run, unchanged, green)
  covers that layer.
- **Abstention is structural, not learned.** Unknown relations and sub-threshold mass
  hard-code MISSING_FACT; source filtering drops quarantined rows because the view shares
  the contract's filter, not because anything decided to.
- **No English, no ears, no mouth here** — frames arrive already parsed.
- **No baseline** of any kind; nothing here beats any alternative.
- **Sleep saw only clean episodes** (noise controls belong to Exp 45/46); words are exact
  2–3 hop chains of existing skills — no disjunctions, no new primitives.
- The audit's "true walk" reads the same view as the reasoner, so a shared view bug could
  hide; D3 (an independently built dense path) agreeing 540/540 makes that unlikely.

## Given by hand (not learned)

Hop loop and statuses; 0.9 threshold and abstention; view construction (sharing contract
semantics); identity routing for base relations (Exp 44's learned identity inherited as a
given, no base training); word shape (3 stages × [keep + 8 core skills]); the three words
and their chains; episodes only from resolvable people; gate constants, ε=0.10,
harden ±30 (Exp 45/46); grid generator and category mix; seeds.
**Learned:** only the 27 routing numbers per word, from final answers alone.

## Deviations

1. **Source tags:** tasking said "sleep-derived never answers"; the shipped contract
   includes `sleep-derived` and `web-verified` in `ANSWERING_SOURCES`.  Parity is against
   the contract, so the reasoner follows it (flagged in PASSMARKS before the run).
2. A display-name-vs-E-id bug in the D3 check was fixed in dev, before the seal; no
   registered code changed after sealing (seal verified).
3. No wrong-episode/random-episode sleep controls (not registered; Exp 46 covers them).
4. Parity candidates are filtered to their category by the reasoner's own status (fast
   sampling); a systematic reasoner bug would still show as a contract disagreement on the
   same frames — which is what S1 measures.

## Reproduce

```bash
cd /Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27
shasum -a 256 -c <(head -3 artifacts/fable-reasoner50-20260921/SEAL.sha256.txt)   # check the seal
bash artifacts/fable-reasoner50-20260921/wave.sh    # selftest + scale + 3 sleeps + score
```

## Files

`scripts/fable_reasoner50.py` (`--stage selftest|scale|sleep|score`);
`artifacts/fable-reasoner50-20260921/` — `PASSMARKS.md`, `SEAL.sha256.txt`, `wave.sh`,
`runs/`, `logs/`, `dev/`, this `RESULTS.md`, `RESULTS-SEAL.sha256.txt`; design doc
`design/v3/30-modes/50-reasoner-on-notebook-opus.md`.
