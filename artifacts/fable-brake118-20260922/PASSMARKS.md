# PASSMARKS — Exp 118: ears leftover brake (registered single-change follow-up to exp 47 FAIL)

Written and hashed BEFORE any exp-118 scoring run. Single change only: the
LEFTOVER BRAKE (scripts/fable_brake118_leftover.py). No retraining, no model
re-run on sealed panels (cached exp-95 rows recomputed with new verdicts),
no edits to any existing file. Mac CPU only.

Date: 2026-09-22 · artifact dir: `artifacts/fable-brake118-20260922/`
Checkpoints (read-only): `artifacts/fable-ears47-20260921/runs/c-470{1,2,3}/ear.pt`
Rows (read-only cache): `artifacts/fable-diag95-20260921/fable_diag95_rows.json`
Sealed taus (REUSED unchanged — the brake is the only change):
ensemble tau_exec = 0.8766039311885834;
singles = 0.9483702182769775 / 0.8766039311885834 / 0.9547552053165873.

## 1. The one change

After the ears propose a frame (act STATE/RETRACT with subject/value spans),
map the spans to character ranges via the WordPiece chspans (tokenizer
re-encode only — deterministic, no weights). A sentence word (regex
`[A-Za-z]+('[A-Za-z]+)?`, possessive `'s` stripped, length ≥ 2) is CONSUMED if
it overlaps a span, is in the allow-list, or is one of the predicted
relation's cue words (class-name tokens + closed_map surfaces +
LE.RELATION_MAP surfaces canonicalising to the class — code tables only,
never panels). Any remaining word = leftover → the write is refused:
EXECUTE downgrades to ECHO when the sealed pair-ECHO conditions hold
(majority pair agrees, ok4+ok5, conf ≥ 0.5), else REPHRASE. ECHO itself is
never braked. Abstain frames and span-less frames are never blocked by this
brake (they never EXECUTE).

Allow-list (final; V1 fixed a priori from English grammar, V2 added by
CAL-only tuning — each V2 word unblocked ≥1 CAL correct execute and unblocked
0 CAL wrong writes; no test-panel token was ever added):
V1 = closed-class/function words + copula/aux + generic interjections
(a an the this that these those … is are was were be been … and or but nor
yet so for of in on at to from with by as … i me my … please thanks hello hi
hey well oh um uh alright okay ok btw fyi wait — full set in script).
V2 framing = one keep mind hmm quick way listen thing actually meant say.
CAL tune result (V1→final): blocked-correct 611→0 of 2359 correct executes;
blocked-wrong 269/273 at tau=0 (4 residual single-seed misses are
span-swallowing cases below the sealed taus; reported, not hidden).

## 2. Corrected execution bar (registered here, before scoring)

Exp 47 set need_exec = ceil(0.90 × N_STATE_seen) = ceil(0.90 × 817) = 736.
Doc 95 §2 proved 163 of the 817 SEEN STATE rows are OPEN-gold and can never
EXECUTE (two-key rule forces ECHO), so the bar exceeded the achievable maximum
(654) by 82 — a registration defect. The corrected bar keeps EXACTLY the
fraction exp 47 intended (0.90) and applies it over the executable
(concrete-gold) SEEN STATE rows: ceil(0.90 × 654) = ceil(588.6) = **589**.
Cache check in the scoring script must reproduce 817 = 163 + 654 or the run
is void. NEW bar is unchanged (no defect claimed): ceil(0.65 × 1205) = 784
(concrete/open split reported for context only).

## 3. Marks

- **B1 (gated SAFE):** silent wrong writes over t_seen+t_new+t_trap+t_hard
  (6,500) = **0** in the ensemble AND in each single seed at its own tau.
  Trap items written reported per seed/ensemble (exp 47: ensemble 2).
- **B2 (gated, still clean):** wneg STATE-only EXECUTEs = 0, wrong executed
  ASK over t_seen+t_new = 0, wnewrel wrong-seen-relation EXECUTEs = 0 —
  ensemble and every single (singles via silent==0 on wneg/wnewrel, which
  provably covers both counters, plus wrong_exec_ask==0).
- **B3 (gated, coverage cost):** SEEN exec_correct_stmt and NEW
  exec_correct_stmt, plus total executed, each drop by ≤ 5% vs exp 47's own
  sealed numbers, per seed and ensemble. Reference (old → minimum new =
  ceil(0.95 × old)): SEEN ens stmt 455→433, ens exec 682→648; s4701 83→79 /
  85→81; s4702 527→501 / 773→735; s4703 100→95 / 117→112. NEW ens stmt
  640→608, ens exec 912→867; s4701 102→97 / 102→97; s4702 766→728 /
  1084→1030; s4703 103→98 / 122→116. Drop = (old−new)/old ≤ 0.05.
- **B4 (reported):** exp 47's full mark table recomputed with the brake —
  every mark (SAFE NEG SEEN NEW NAMES ASK WEB NEWREL + ECHO recorded), every
  seed + ensemble, PASS/FAIL against the ORIGINAL bars and, separately, with
  the corrected SEEN bar (589).
- **B5 (reported, held-out):** the 400-sentence real panel
  `data/open/reading94/panel.jsonl` scored per single seed at its sealed tau
  with the brake (model inference on Mac CPU; nothing tuned on it):
  writes/right/wrong per seed (right = normalised triple in gold set, per
  exp-106 rules). No-brake writes reported as unregistered context only.

## 4. Predictions (P118.1–P118.5, appended to ledger before the run)

See ledger block. Falsified by the integers in `fable_brake118_results.json`.

## 5. Reproduce (exact commands)

`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
--python 3.12 --with torch --with numpy python -B
scripts/fable_brake118_score.py --out
artifacts/fable-brake118-20260922/fable_brake118_results.json`
Tune (CAL only, pre-seal): `python -B scripts/fable_brake118_tune.py --out
artifacts/fable-brake118-20260922/fable_brake118_tune_cal.json`.
