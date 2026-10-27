# Exp 261 PASSMARKS: the ear with an entailment checker (builder, 2026-09-22)

Registered arm A: v4.1 ear + speaker canonicaliser + brake + entailment checker (theta).
Replaces 257's margin gate (tau 9.3). 257 stays FAIL; this is the one follow-up.

## Frozen config

- Ear: v4.1 checkpoint on BensPC `C:\Users\benja\smolear235\out_v41\smolear235.safetensors`,
  sha256 `55284dec92ea3e6d5d9d99c5afa99ae80a73eafaf644a0c2ca268dcb9fad0bd2`
  (verified by hash on BensPC before the seal; inference also asserts it).
  Same inference, brake, relation table v2, loader and scorer as 257, imported read-only.
- Canonicaliser (brief section 1): TEACH/ASK subjects mapping to "me" (case-insensitive):
  i, me, my, myself, mine, we, us, our, ours, ourselves. Runs AFTER the brake
  (piloted: the unchanged brake needs the literal span, so canon-before-brake would
  drop "Our"-subject frames as subject_not_in_turn). Nothing else changes.
- Claim renderer (fixed before seal, from table-v2 names only): default
  "<S>'s <relation words> is <V>." ("me" -> "the speaker"); nicer templates:
  city -> "{S} lives in {V}.", occupation -> "{S} works as {V}.",
  employer -> "{S} works for {V}.", school -> "{S} goes to {V}.",
  language -> "{S} speaks {V}.".
- Checker question (fixed before seal): `promptB.build_prompt_b` (prompt variant B;
  see Deviation D1). Temperature 0, thinking off (`/no_think` + closed `<think>` block
  in the Qwen3 chat template), one token, p(YES) = pYES/(pYES+pNO) from first-token
  logprobs over YES/NO spelling variants. Fallback: no YES/NO variant -> greedy text
  YES=1.0 / NO=0.0 / else 0.0 (hold back); fallbacks counted (0 on dev).
- Checker rule: TEACH saved iff p(YES) >= theta, else UNSURE (where 257's gate put
  UNSURE). Checker only keeps/holds back; never adds, edits or reorders. ASK unchecked.
- theta = 0.25 by 257's sealed rule (max recall at wrong_rate <= 1%; ties -> smallest;
  else lowest wrong rate), no fallback. A/B result: prompt A reaches <= 1% only at
  theta 0.9 (recall ~51%); prompt B qualifies from 0.25 up (see curve).
- Arms: A (registered), A_gate (canon+brake+margin gate tau 9.3), A_brake (canon+brake),
  A_raw (canon only), A_nocanon (brake+checker, no canon), B (138i+228, statement fams).
- Compute: BensPC RTX 5070 Ti; llama-server already running (PID 13444, port 8081,
  Qwen3.8-27B-UD-IQ4_XS, -c 4096, -ngl 99, -fa 1, q8_0 KV cache); /health ok 2026-09-22.
  Reused, never restarted. VRAM at seal time ~13.7/16.3 GB, idle 0%, no spill seen.
  Ear checkpoint streamed/used on BensPC only; Mac stays above its disk floor.

## Dev (what theta was picked on)

- 257's dev split, 1530 rows (`dev_tau.jsonl`, excludes R3_indist) with v4.1
  `v41_preds.json`, kept frames recomputed locally: exact 257 A_brake reproduction
  (step 1): 967/1009 hit/gold with 38 wrong (257 sealed 1027/1069 incl. R3_indist's
  60/60; base 428/434, C1 59/63, C2 51/51 all match exactly).
- NEW checker dev set, own wording, 210 rows (`dev_checker.jsonl`, generator
  `scripts/claude_earcheck261_devset4.py`): D_pre 30 (gold none), D_plan 30
  (15 pure none + 15 plan clause + one real fact), D_checkq 30 (gold none),
  D_apos 30 (two gold frames each, pronoun = B), D_our 30 (gold subject "me"),
  D_plain 60 (gold TEACH). Qwen wrote no dev sentences (builder wrote all turns).
- GPU ear preds for the 210 (`devcheck_earpreds.json`, cuda, ckpt sha ok, tau 9.3
  recorded for gate comparison only): median 158 ms. Checker pYES for all
  1207 kept TEACH frames (1005 dev257 + 202 devcheck) with prompt B, 0 fallbacks
  (`devcheck_pyesB.json`; superseded prompt-A run `devcheck_pyes.json` not sealed).
- Theta sweep (prompt B; full curve in `theta.json`):

| theta | recall | wrong | wrong_rate | unsure |
|---|---|---|---|---|
| 0.00 | 93.6% | 103 | 7.53% | 0 |
| 0.10 | 93.6% | 40 | 2.92% | 63 |
| 0.20 | 92.6% | 20 | 1.46% | 94 |
| 0.25 | 91.9% | 13 | 0.95% | 109 |
| 0.30 | 91.0% | 11 | 0.80% | 122 |
| 0.55 | 83.0% | 9 | 0.66% | 219 |
| 0.90 | 51.3% | 5 | 0.37% | 597 |

- At theta 0.25 by tag: base 411/434 (5 wrong), R1 143/155 (1), R2 0 wrong (7 unsure),
  R2s 19/20, C1 59/63 (1), C2 51/51 (0), C3 121/136 (1), C4 49/50 (1), C5 24/24 (0),
  C6 71/76 (1), D_pre 0 wrong (5 unsure), D_plan 10/15 (0 wrong, 18 unsure),
  D_checkq 0 wrong (13 unsure), D_apos 31/60 (3 wrong, 26 unsure),
  D_our 36/36 (0), D_plain 60/60 (0).
- Ear+checker latency on dev (both models resident): n=1740, median 340.3 ms,
  p90 650.6 ms, max 1091.3 ms.
- Pre-seal plumbing pilot (synthetic 150-line fixture in 261 schema, /tmp only):
  qbuild panel (prompt B) 150 turns -> checks ok; scoremain --no-sha scores
  (M3 85/85, M4 40/40, M6 exact, 21-point theta curve, per-tag table, details ok);
  bad fixture (149 lines) -> SCHEMA-MISMATCH exit 3 ok.

## Marks, arm A (bars are 257's, plus M6)

| Mark | Bar | Prediction |
|---|---|---|
| M1 | no_save saves <= 1 | 0-1 saves; PASS ~70% (P261.1) |
| M2 | wrong saves (statement fams + no_save) <= 1 | 0-3 wrong; PASS ~55% (P261.2). Risk: R10/R11/R12 splits the dev set never saw (D_apos still 3 wrong at 0.25) |
| M3 | exact TEACH recall >= 85% and >= B + 30 | 85-93%; PASS ~65% (P261.3). B expected 10-20% |
| M3b | UNSURE <= 12% of gold TEACH | 5-12%; PASS ~60% (P261.4) |
| M4 | exact ASK recall >= 90% | 90-100%; PASS ~75% (P261.5). Canon maps ASK subjects too |
| M5 | median ear+checker ms/turn <= 800 | 300-600 ms; PASS ~90% (P261.6) |
| M6 | every A frame byte-identical in A_brake | exact; PASS ~99% (P261.7) |
| ALL | overall registered PASS | ~25% (P261.8) |

Also reported (no bars): every arm's M1-M4; panel theta curve; per-tag R1-R12 table;
each A held-back/wrong frame (category, p(YES), claim with names blanked); after the
registered run only, arm A on earpanel257 once, next to 257's A / A_brake / gate.

## Deviations / notes (carried into RESULTS)

- D1: sealed question is prompt variant B, not the brief's literal text. B keeps every
  required element (message line, claim line, real-current-fact question, the full NO
  list incl. tag/"so"-checks, pretend, plans, denied, wrong-person, one-word YES/NO)
  but rewords the question ("telling, not checking/pretending/planning") and adds two
  NO clauses (other confirmations like "isn't it"/"yeah?"; filler words leaking into
  the fact). Chosen by a dev A/B before the seal: prompt A cannot reach <= 1% wrong
  below theta 0.9 (recall ~51% there); prompt B gives 91.9% recall at 0.95% wrong.
  Sealing the literal text would fail M3 by design.
- D2: pre-seal, the builder listed the panel directory, verified its hashes and
  counted lines (150, matching the spec) but never read any item text, turn or gold.
  Formal `shasum -c` check from the repo root happens after this seal.
- The panel was already sealed before this seal, so the 60-minute wait ends at once.
- Previous builder (killed 20:40 by an app restart, no task problem) left theta.json
  and dev pyes; the resume builder verified theta.json byte-for-byte by rerunning the
  sealed sweep on prompt-B pyes (sweep/at_choice/latency all equal), and reproduced
  257's A_brake exactly. Nothing was re-tuned; no ledger prediction was duplicated.

## Seal

Sealed files (agent code, prompt, theta, dev files, scorer; superseded drafts
checks/pchecks/qwen/score/devset/devset2/devset3/devturns and prompt-A pyes NOT sealed):
scripts/claude_earcheck261_canon.py, scripts/claude_earcheck261_arms.py,
scripts/claude_earcheck261_checker.py, scripts/claude_earcheck261_qbuild.py,
scripts/claude_earcheck261_promptB.py, scripts/claude_earcheck261_theta.py,
scripts/claude_earcheck261_panel.py, scripts/claude_earcheck261_turns.py,
scripts/claude_earcheck261_armb.py, scripts/claude_earcheck261_scoremain.py,
scripts/claude_earcheck261_devset4.py,
artifacts/claude-earcheck261-20260922/PASSMARKS.md,
artifacts/claude-earcheck261-20260922/theta.json,
artifacts/claude-earcheck261-20260922/dev_checker.jsonl,
artifacts/claude-earcheck261-20260922/dev257_manifest.json,
artifacts/claude-earcheck261-20260922/devcheck_manifest.json,
artifacts/claude-earcheck261-20260922/devcheck_earpreds.json,
artifacts/claude-earcheck261-20260922/devcheck_pyesB.json
