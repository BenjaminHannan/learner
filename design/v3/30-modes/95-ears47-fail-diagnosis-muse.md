# 95 — Ears rung-2 FAIL diagnosis (exp 95, muse, 2026-09-22)

**Result: the FAIL decomposes into three separable problems, and one mark was
unreachable by construction.** Read-only Mac-CPU inference (3 seeds × 10
panels) reproduces all 9 sealed panels exactly; no retraining, no exp-47 file
touched (PASSMARKS sealed pre-run, ledger P95.1–P95.6 scored 3/6 TRUE).
Artifact: `artifacts/fable-diag95-20260921/` (RESULTS.md, rows, tables).

## 1. WEB: not an unseen family — a confidence collapse

`webred.pos` sentences were never in the pool (pool = 60,000 synth +
80,903 WebRED-train rows; 0 dev sentences), but 1508/1806 wpos relations ARE
train classes (298 are heldout: operator 57, owned by 50, owner of 47, …);
wclosed is 46/46 train-seen, and doc 83 shows 813/1806 wpos triples were
trained. Yet the ensemble executes 0/46 and REPHRASEs 1791/1806 — because
confidence is ~zero, not because the relations are unknown: top act is STATE
on 4369/5418 wpos seed-rows but rel==gold only 1693/4369 (38.8%), ensemble
conf < 0.3 on 1494/1806, ≥ tau on 1/1806 (first-10 rows: 7/30 STATE+gold-rel,
so P95.1 FALSE). Mechanism on the table: wpos sentences are ~4× longer than
anything calibrated (median 134 vs 35 chars; MAX_LEN 96 truncates), so pointers
diffuse and the min-of-heads score floors. wclosed agrees: 39/46 3-way STATE
but max conf 0.569, median 0.000.

## 2. Execution rate: the SEEN bar was unreachable; the rest is low confidence

SEEN STATE-gold rows number 817 = 163 OPEN-gold + 654 concrete. OPEN-gold rows
can never EXECUTE (two-key rule forces ECHO), so the need_exec bar of 736
exceeds the achievable maximum of 654 by 82 — a registration defect, not a
model defect. On executable rows the model executes 455/654 (69.6%); NEW does
640/1038 (61.7%, bar 784 reachable). Of SEEN's 362 non-executions: 199 pure
low-conf, 138 forced-echo-OPEN (every one OPEN-gold, i.e. correct ECHOs), 25
both — seed disagreement 0/362. NEW's 565: 334 low-conf, 142 forced-echo (all
OPEN-gold), 68 disagreeing (12.0%). Combined near-miss band [0.5, tau): 463/927
= 49.9% (P95.2 FALSE by one row); disagreement 68/927 = 7.3% (P95.3 FALSE).

The exp-76-style LTT grid on CAL certifies tau-hat = 0.0887 (2337 candidates,
34 CAL errors, 15/15 points accept; P95.4 TRUE) — and applying it is
catastrophic off-distribution: t_seen 992 exec/+0 silent, t_new 1406/+3,
t_hard 223/+0, wclosed 4/+0, but t_trap 99/+13, t_far 266/+38, wneg 38/+38,
wpos 318/+198 (only 120 exact), wnewrel 58/+58. A CAL-only certificate does not
transfer to WebRED panels; it would trade two coverage FAILs for a SAFE
catastrophe and still leave WEB at 4/46.

## 3. The 2 SAFE writes: all brakes passed, margins ≤ 0.016

`t_trap #259 "Fertelovic aside, …"` (ens 0.8922; seeds 0.9542/0.8922/0.9411)
and `#751 "… lisvannov aside, …"` (ens 0.8827; 0.8827/0.8881/0.9109): 3/3
identical STATE frames, ok4 = ok5 = True, forced_echo = False (P95.5 TRUE).
Brake 4 inspects only `[UNK]` wordpieces ("aside" is known); no brake watches
leftover phrasing (flags = neg/hypo/reported only); brake 5 validates the
adapted teach/correct item, which each sentence supports. At 4701/4703 taus
(0.9484/0.9548) neither executes.

## 4. Tau drivers: one seed, one CAL item — not temperature

Ensemble tau0 (0.7532) equals seed-4702's tau0 to the row: CAL #4994
trap.leftover, per-seed confs 0.7686/0.7532/0.8666 (min = 4702). Singles tau0:
0.8967/0.7532/0.9095; wrong-at-tau-0: 34 ensemble vs 69/97/73 singles. ECE on
CAL candidates: 0.1186/0.1234/0.1075 (spread 0.0159, P95.6 TRUE); temperatures
near-identical across seeds (act ≈ 2.0–2.2, dir ≈ 0.22 all seeds). Temperature
is exonerated; the high tau is 4702's worst CAL leftover, inherited verbatim
by the ensemble min.

## 5. Ranked single changes for a registered 47b (SAFE held at 0)

1. **Redefine need_exec over executable (concrete-gold) STATE rows** —
   unblocks SEEN-exec by registration (654 < 736); zero SAFE cost. Evidence §2.
2. **Add "aside"-style leftover negatives to the pool** — SAFE writes beat CAL's
   worst leftover by 0.13+ on ≤ 0.016 margins; CAL holds only 148 leftovers.
   Evidence §§3–4.
3. **WebRED length/distribution coverage** (window > 96 or WebRED-style synth) —
   the only real WEB mover (1494/1806 conf < 0.3); pair with #2 since more
   executes raise SAFE exposure. Evidence §1.
4. **Stratified (Mondrian) LTT, never a single CAL grid** — principled lower
   tau only with a WebRED calibration stratum. Evidence §2-LTT.
5. **Do not swap in the plain exp-76 grid; do not refit temperatures** —
   evidence: +198/+58/+38 test silents with WEB still 4/46; ECE spread 0.0159.

## What this diagnosis does NOT show

It does not show any ranked change will pass (all are untested predictions, no
retraining ran); it does not certify a safe threshold (the LTT number above is
a counter-demonstration, and CAL-distribution-only per docs 76/78); it does not
blame the encoder (borrowed vs from-scratch is untested here); it does not
cover papers (no panel exists); and pool-family counts are by construction rule
plus JSON overlap, not a rebuilt pool.
