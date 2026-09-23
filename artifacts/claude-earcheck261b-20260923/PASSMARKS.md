# Exp 261b PASSMARKS: 261's arm A plus the mixed-case span guard (builder, 2026-09-23)

Registered arm A: 261's sealed arm A (v4.1 ear + speaker canonicaliser + brake +
entailment checker at sealed theta 0.25, prompt B, unchanged) PLUS the mixed-case
span guard applied after the checker. 261 stays FAIL; this is the one
diagnosis-driven follow-up (design/v3/30-modes/261b-decision.md).

## Frozen config

- Ear: v4.1 checkpoint on BensPC `C:\Users\benja\smolear235\out_v41\smolear235.safetensors`,
  sha256 `55284dec92ea3e6d5d9d99c5afa99ae80a73eafaf644a0c2ca268dcb9fad0bd2`
  (verified by hash on BensPC before dev waves; inference asserts it).
  Same inference, brake, relation table v2, canonicaliser, checker prompt B and
  theta 0.25 as 261, imported read-only. Nothing else changes.
- Guard (the ONE change; `scripts/claude_earcheck261b_guard.py`, fixed before the
  seal from table v2 + general knowledge): a checker-saved TEACH frame whose
  subject or value span mixes a Capitalised word with a lowercase non-particle
  word is held back as UNSURE (`why=GUARD_UNSURE`, reason subject_mix/value_mix/
  both_mix). The guard only holds back; it never adds, edits or reorders, so
  every A frame is byte-identical in A261 (M6 by construction, verified).
  ASK frames never guarded. Per-word edge punctuation stripped; words with no
  cased letters ignored; all-lowercase and all-Capitalised spans pass.
- PARTICLES (decision note): de, da, van, von, der, la, le, del, di, bin, al.
- VALUE_EXEMPT_KINDS (table v2 value_kinds whose values are common nouns, not
  proper names): literal (occupation, pet, hobby, sport, ...), thing
  (instrument, favourite foods, ...), work (notable_work titles carry articles),
  date, number. Checked kinds (proper-name values): person, pet, place,
  organization, language. Subjects always checked (names or "me").
- Scorer (`scripts/claude_earcheck261b_scoremain.py`): 261's sealed scorer called
  unchanged, plus Ruling 1 only: a frame whose relation is in the gold
  relation's table-v2 "narrower" list counts as a hit (table map sealed in the
  scorer output: parent->{mother,father}, sibling->{sister,brother},
  spouse->{wife,husband}, child->{son,daughter}, grandchild->{grandson,
  granddaughter}, pet->{dog,cat}). Subject/value matching untouched.
- Arms: A (registered: A261 + guard), A261 (261's A exactly: brake -> canon ->
  checker 0.25), A_brake (canon + brake), B (138i + 228, statement fams).
- Compute: BensPC RTX 5070 Ti; llama-server started by this builder
  (Qwen3.8-27B-UD-IQ4_XS, --host 127.0.0.1 --port 8081 -ngl 99 -fa 1 q8_0 KV
  cache, --parallel 1 -t 6 -c 4096); /completion shape verified. VRAM with both
  resident ~13.7/16.3 GB, no spill. Server stopped by exact PID at the end.

## Dev (before the seal)

- Step 1 (reproduction): 261's sealed theta sweep rerun from its sealed files
  (257 dev split + dev_checker.jsonl + GPU preds + prompt-B pYES): byte-equal to
  sealed theta.json (sweep, at_choice, latency all equal; theta 0.25, recall
  1085/1180 = 91.9%, wrong 13, unsure 109). Pipeline matches.
- Step 2a (guard on 261's dev): 1098 checker-saved TEACH frames -> guard holds 8
  (0.7%), all subject_mix on tag base, all 8 RIGHT (false holds). All 8 share one
  category: title-style subjects with a lowercase "of" ("X of Y" pattern, not in
  the particle list). No value_mix holds; no holds on any D_* tag. Known cost,
  reported, not tuned.
- Step 2b (own dev, `dev_261b.jsonl`, generator sealed): 24 typo turns (misspelt
  everyday word next to a name, clean-span gold; 20 TEACH + 4 check-style NONE)
  + 24 all-lowercase turns (lowercase names, lowercase-span gold). GPU ear preds
  (median 187 ms, ckpt sha ok, 46/48 beamed) + prompt-B pYES (56 queries,
  0 fallbacks, median 282 ms): checker saved 53 (D_typo 29, D_lower 24); guard
  held 0, false holds 0. Observed (report only): the ear glued a typo word into
  a span on 2 typo turns -- once capitalised (all-Capitalised span, guard passes
  by design; checker-approved wrong save, known residual) and twice as garbage
  relations the checker held; all 24 lowercase turns saved with 0 holds.
- Ear+checker+guard latency on dev (both models resident): 261 dev n=1740 median
  340.3 ms; new 48-turn dev ear 187 ms + checker 282 ms medians.
- Pre-seal plumbing pilot (synthetic 150-line 261b-schema fixture in /tmp only):
  turns 150 -> qbuild panel 170 checks (prompt B); scoremain --no-sha scores
  (Ruling 1 pet/parent hits counted, 2 value_mix frames held at pYES 1.0, A M2
  0 wrong vs A261 M2 2 wrong, M6 exact, 21-point curves for A and A261, per-tag
  table, details ok); bad fixture (149 lines) -> SCHEMA-MISMATCH exit 3 ok.

## Marks, arm A (same bars as 261)

| Mark | Bar | Prediction |
|---|---|---|
| M1 | no_save saves <= 1 | 0-1 saves; PASS ~70% (P261b.1) |
| M2 | wrong saves (statement fams + no_save) <= 1 | 0-2 wrong; PASS ~60% (P261b.2). 261's 9 wrongs: ~6 pet-narrower become hits (Ruling 1), ~2 typo-mix held by guard if case-mixed; residual: so-check style, capitalised-glued typos, R10/R11 splits |
| M3 | exact TEACH recall >= 85% and >= B + 30 | 80-90%; PASS ~55% (P261b.3). 261 77.9% + Ruling-1 hits - guard false holds (~1%); R10 plural splits still cap; B expected 10-20% |
| M3b | UNSURE <= 12% of gold TEACH | 4-10%; PASS ~80% (P261b.4). 261 checker 4.9% + guard ~1-3% |
| M4 | exact ASK recall >= 90% | 90-100%; PASS ~75% (P261b.5). ASK untouched by guard |
| M5 | median ear+checker+guard ms/turn <= 800 | 300-600 ms; PASS ~90% (P261b.6) |
| M6 | every A frame byte-identical in A261 | exact; PASS ~99% (P261b.7) |
| ALL | overall registered PASS | ~30% (P261b.8) |

Guard behaviour (no bar): holds 1-8 frames on the panel, mostly good holds;
false holds 0-3, all one category (title-style "X of Y" subjects) (P261b.9).

Also reported (no bars): A vs A261 on M1-M4; A_brake and B M1-M4; per family;
per tag R1-R14; panel theta curves (A and A261); each guard-held frame with
category only.

## Deviations / notes (carried into RESULTS)

- D1 (inherited from 261): the checker question is prompt variant B, rewording
  the brief's literal text and adding two NO clauses. Dev A/B in 261: literal
  prompt reaches <= 1% wrong only at theta 0.9 (recall ~51%); B gives 91.9%
  recall at 0.95% wrong. Sealing the literal text would fail M3 by design.
- D2: the blind panel (artifacts/claude-earpanel261b-20260923/) is never opened
  before this seal -- no listing, no hashes, no line counts. After this seal:
  poll for its SEAL.sha256.txt every 2 minutes up to 90 minutes, `shasum -c`
  from the repo root, strict schema check, then every arm ONCE. Never run
  earpanel257 or earpanel261.
- Known guard limits (dev-measured, not tuned): lowercase-"of" title subjects
  are false-held (8/1098 on 261 dev); a glued typo the ear capitalises passes
  the guard (1 seen on new dev); "so ..."-style checks with no case mix pass
  (261's residual). All reported with counts.

## Seal

Sealed files (new 261b code, PASSMARKS, dev files; 261's sealed files reused
read-only, never re-sealed):
scripts/claude_earcheck261b_guard.py, scripts/claude_earcheck261b_arms.py,
scripts/claude_earcheck261b_panel.py, scripts/claude_earcheck261b_turns.py,
scripts/claude_earcheck261b_armb.py, scripts/claude_earcheck261b_scoremain.py,
scripts/claude_earcheck261b_guarddev.py, scripts/claude_earcheck261b_devset5.py,
artifacts/claude-earcheck261b-20260923/PASSMARKS.md,
artifacts/claude-earcheck261b-20260923/dev_261b.jsonl,
artifacts/claude-earcheck261b-20260923/dev261b_earpreds.json,
artifacts/claude-earcheck261b-20260923/dev261b_pyes.json,
artifacts/claude-earcheck261b-20260923/dev261b_manifest.json,
artifacts/claude-earcheck261b-20260923/guarddev_261dev.json,
artifacts/claude-earcheck261b-20260923/guarddev_261bdev.json
