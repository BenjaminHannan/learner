# RESULTS — Exp 95 diagnosis of the registered exp-47 FAIL (rung-2 ears)

**Result: diagnosis complete, no retraining.** CPU inference on the Mac (3 seeds ×
10 panels, 18.5 min) reproduces every sealed number exactly (9/9 panels:
executed/correct/silent match `runs/report.json` to the integer). Five
mechanisms explain the FAIL; the SEEN-exec bar was unreachable by construction.

## 1. What ran

Read-only inference with the sealed scorer (`fable_ears47_score` decode/verdict
functions, `use_temp=True`) over cal/t_seen/t_new/t_far/t_trap/t_hard/wneg/wpos/
wclosed/wnewrel × seeds 4701/4702/4703, plus JSON-only pool/panel counts.
PASSMARKS sealed (`SEAL.sha256.txt`) and ledger P95.1–P95.6 appended before the run.

## 2. Findings (integers; per-seed reported, never averaged)

| # | finding | integers |
|---|---|---|
| WEB-1 | `webred.pos` sentences never in pool, but 1508/1806 wpos relations ARE train classes (298 heldout: operator 57, owned by 50, owner of 47, …); wclosed 46/46 train-seen; doc 83: 813/1806 wpos triples in train | 1508/1806; 46/46; 813/1806 |
| WEB-2 | On wpos the head says STATE (4369/5418 seed-rows) but wrong-rel (1693/4369 = 38.8%) at ~zero confidence (1494/1806 ens conf < 0.3; 1/1806 ≥ tau); wpos is 4× longer than CAL (med 134 vs 35 chars; MAX_LEN 96) | 1494/1806 < 0.3 |
| EXEC-1 | SEEN STATE 817 = 163 OPEN-gold (can never EXECUTE) + 654 concrete; executed 455/654. Bar 736 > max achievable 654 → unreachable by 82 | 455/654; bar miss −82 |
| EXEC-2 | SEEN nonexec 362: low-conf 199, forced-echo-OPEN 138 (all OPEN-gold correct ECHOs), both 25; disagreement 0/362. NEW nonexec 565: low-conf 334, forced-echo 142 (all OPEN-gold), disagree 68/565 | disagree 68/927 |
| LTT | CAL candidates at tau=0: 2337, 34 wrong; 15/15 grid points accept → tau-hat 0.0887. Applied: t_seen 992 exec/+0 silent, t_new 1406/+3, t_hard 223/+0, wclosed 4/+0, t_trap 99/+13, t_far 266/+38, wneg 38/+38, wpos 318/+198 (120 exact), wnewrel 58/+58 | +198/+58/+38 test silents |
| SAFE | #259 ens conf 0.8922 (seeds 0.9542/0.8922/0.9411), #751 ens 0.8827 (0.8827/0.8881/0.9109); margins above tau 0.0156/0.0061; 3/3 identical STATE, ok4=ok5=True, forced=False both | 2 writes, margins ≤ 0.016 |
| TAU | Ensemble tau0 = 4702's tau0 = CAL #4994 trap.leftover "Cavish's book is rice, Wenenkodel too." (seeds 0.7686/0.7532/0.8666; min = 4702). Singles tau0 0.8967/0.7532/0.9095; wrong-at-0: 34 ens, 69/97/73 singles. ECE 0.1186/0.1234/0.1075 (spread 0.0159); temps act ≈ 2.0–2.2, dir ≈ 0.22–0.23 all seeds | 1 seed + 1 item drive tau |

Why the trap brake did not fire: brake 4 checks only `[UNK]` wordpieces outside
spans ("aside" is a known wordpiece); no brake looks for leftover phrasing
(flags cover neg/hypo/reported only); brake 5 validates the adapted
teach/correct item, which the sentence supports. At 4701/4703 taus
(0.9484/0.9548) neither write executes — 4702's low tau is the enabler.

## 3. Ranked single changes for a registered 47b (SAFE held at 0)

1. **Redefine need_exec over executable (concrete-gold) STATE rows** — fixes an
   unreachable bar (654 < 736); zero SAFE cost. Evidence: EXEC-1.
2. **Add "aside"-style leftover negatives to the pool** — both SAFE writes beat
   the CAL worst-leftover by 0.13+ with ≤ 0.016 margin; CAL has only 148
   leftovers. Evidence: SAFE + TAU.
3. **WebRED length/distribution coverage** (window > 96 or WebRED-style synth) —
   only real WEB mover (conf < 0.3 on 1494/1806; rel-match 38.8%). Needs #2
   alongside (more executes = more SAFE exposure). Evidence: WEB-2.
4. **Stratified (Mondrian) LTT, never a single CAL grid** — the plain grid adds
   198+58+38+38+13+3 silents and still executes 4/46 wclosed. Evidence: LTT.
5. **Do not swap in the plain exp-76 grid; do not refit temperatures**
   (ECE spread 0.0159, temps near-identical — no evidence). Evidence: LTT + TAU.

## 4. What it means / what it does not mean

What it means: the FAIL is three separable problems — an unreachable SEEN-exec
bar, a confidence collapse on long WebRED sentences, and a tau set by one seed
on one CAL leftover that two test leftovers outscored.

What it does not mean: it does not show a new threshold would be safe (the LTT
grid is catastrophically unsafe off-distribution here), that the ears cannot
read WebRED (813/1806 triples were trained; the failure is confidence, not
ignorance), or that any ranked change will pass — all are untested predictions.

Deviations: none (plan followed; full-panel inference replaced the sampled
subset plan within one < 30-min wave). Reproduce: `export OMP_NUM_THREADS=1
MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch
--with numpy python -B scripts/fable_diag95_infer.py --out
artifacts/fable-diag95-20260921/fable_diag95_rows.json` then `python -B
scripts/fable_diag95_analyze.py --rows … --out …/fable_diag95_tables.json`.
Ledger P95.1–P95.6: 3/6 TRUE. Doc-83 read 2026-09-22.
