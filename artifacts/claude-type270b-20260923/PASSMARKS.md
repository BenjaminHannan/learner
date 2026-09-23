# Exp 270b PASSMARKS: 270's normaliser (keep-s fixed) in front of the EAR on 261b's arm A (builder, 2026-09-23)

Registered arm A: 261b's registered arm A (v4.1 ear + speaker canonicaliser +
brake + YES/NO entailment checker at sealed theta 0.25, prompt B + 261b span
guard, scorer with Ruling 1; all imported read-only, never re-sealed) PLUS
270's text normaliser outermost with the keep-s rule FIXED
(`scripts/claude_type270b_normalise.py`, THE ONE CHANGE). Arm A261b: 261b's
A exactly. Design: the 270b brief (no design file; the brief is the spec).
270 stays FAIL (loop-line base/panel mismatch); this is the one follow-up on
the ear line.

## Frozen config

- Ear: v4.1 checkpoint on BensPC
  `C:\Users\benja\smolear235\out_v41\smolear235.safetensors`, sha256
  `55284dec92ea3e6d5d9d99c5afa99ae80a73eafaf644a0c2ca268dcb9fad0bd2`
  (verified by hash on BensPC before the dev wave; inference asserts it).
  Same inference (`claude_smolear257_infer`, table v2, --tau 9.3 --k 4),
  brake, canonicaliser, checker prompt B, theta 0.25, 261b guard as 261b.
  Nothing else changes.
- Normaliser (`scripts/claude_type270b_normalise.py`, fixed before the seal;
  imports 270's `COMMON270`/`REL270`/check-tails/WH-code read-only): fires
  only when the turn has no capitals at all (reason "lowercase") or has no
  apostrophes with an "Xs <relation>" pattern (reason "possessive");
  everything else passes through byte-identical. On firing: possessive fix
  with the FIXED keep-s rule + wh-contractions, then capitalisation
  (COMMON270b words stay lowercase; seen names win).
- Keep-s fix (replaces 270's ss/us/is/os/mes/les ending heuristic, which
  kept Benos/Dilos/Hakis and stripped Thomas->Thoma's): a word keeps its s
  (word + "'s") only if its stem is not a seen (known) name and the word is
  not in the common-word list -- i.e. full word in the sealed S_NAMES270b
  list (general-knowledge real s-names: james, thomas, charles, louis,
  tess, morris, dennis, miles, ...) or in the per-item seen-names memory;
  stem in seen-names or in COMMON270b strips ("benos"+Beno seen -> "Beno's",
  "dogs" -> "dog's", "wills" -> "will's"); otherwise the s STRIPS by
  default ("belmaras" -> "Belmara's", unseen "benos" -> "Beno's", "hakis"
  -> "Haki's", "dilos" -> "Dilo's"). Residual: real s-names outside
  S_NAMES270b and unseen strip (disclosed).
- COMMON270b = 270's COMMON270 plus pet-species singulars (dog, cat, horse,
  rabbit, parrot, turtle, goat, hamster, puppy, kitten): species stay
  lowercase so "benos dog" becomes "Beno's dog" exactly and A diverges from
  A261b only where the possessive fix fires. (270 dropped animal nouns for
  the loop line's description-check; the ear line has no such check.)
- Suppression D1 (carried from 270, pre-seal): trailing check-tails
  (", right", bare "right", ", isn't it", ", don't you think", ", yeah/yep/
  yes/no", ", ok/okay", ", correct", ", you know") pass through unchanged.
  Bare "so ..."-heads are NOT suppressed (same rationale as 270 D1).
- Seen-names memory (the "known name" source on the stateless ear line):
  per-item {lower: StoredForm} from the item's setup/context capitalised
  content words, reset per item; passed as known_names. Single-turn
  s-stems with no seen name strip by default.
- Checker prompts for arm A use the NORMALISED turn text (the message the
  ear saw); A261b prompts use raw text. "Normaliser in front of the EAR":
  everything downstream (ear, brake span check, checker, guard) sees the
  normalised text on arm A.
- Scorer: sealed 235 `match` with 261b's Ruling-1 narrower patch, same
  arm path as 261b (`base_arms` -> `checker_split` 0.25 -> `apply_guard`)
  for both arms; M5 new-wrong = normalised-frame multiset difference
  (case-insensitive); M3/M5 count TEACH saves only (ASK frames never
  write; ASK extras on traps reported, not barred).
- Arms: A (registered: normaliser + 261b A), A261b (261b's A exactly).
- Compute: BensPC RTX 5070 Ti; llama-server started by this builder
  (Qwen3.8-27B-UD-IQ4_XS, --host 127.0.0.1 --port 8082 -ngl 99 -fa 1 q8_0
  KV cache, --parallel 1 -t 6 -c 4096 -m <model>; port 8082 because the
  foreign model-less stub 17056 still holds 8081); sealed 261 checker
  client (handles both wire shapes; smoke YES p=0.927 / NO p=0.004,
  0 fallbacks). Server stopped by exact PID at the end (verified gone,
  GPU idle). pythonw processes and all other BensPC processes untouched.

## Dev (before the seal; own wording, fictional names; never any panel)

`scripts/claude_type270b_devset.py` -> `dev270b.jsonl`: 148 turns
(casual 64, casual_q 16, lower_trap 24, clean 24, sname 16, seen 4).
Normalise (`claude_type270b_turns.py`): 118 rewritten; clean 0/24 fired
(M4-by-construction asserted, exit 2 otherwise). GPU ear preds on BensPC
(cuda, ckpt sha ok, n=296, median 142.7 ms, 207 beamed) + prompt-B pYES
(A 104 + A261b 103 queries, 0 fallbacks, medians 287.3/289.7 ms).
Dev score (theta 0.25; `devreport270b.json`):

| Family | A | A261b |
|---|---|---|
| casual TEACH exact (64) | 63 | 38 (margin +25) |
| sname TEACH exact (16) | 16 | 6 |
| seen TEACH exact (4) | 4 | - (raw not run; memory is A's) |
| casual_q ASK exact (16) | 16 | 3 |
| lower_trap wrong TEACH saves (24) | 3 | 6 |
| clean frames identical (24) | 24 | 24 |

- M1 misses (A): d270b-050 my-pet (ear emits relation "horse", gold "pet"
  +alias "horse": Ruling-1 covers dog/cat, not horse -- ear-convention
  residual); d270b-053 so-opener ("so ..." held by sealed prompt-B rule).
- M2: ear ASK convention on dev = ASK (questioned-name, relation)
  (e.g. ASK (Beno, mother) for "who is Beno's mother"); asker-me only for
  my-shapes. Dev gold fixed pre-seal to this convention from own dev
  evidence (was: asker-me everywhere; A was 2/16 before the fix).
- M3 (A=3): d270b-087 will-future possessive (checker approves "will be" as
  current fact -- but holds bare "will live" futures: d270b-086 held on A
  while saved raw); d270b-093 ", yeah" suppression passthrough (by design:
  identical save on both arms); d270b-102 is-a ("Zorana is a Cooper."
  approved). A261b additionally saves 086 + 2 so-heads raw (094/095: held
  on A after normalisation). ASK extras on traps (A=2, questions read as
  questions) are not saves.
- M5: 1 new wrong TEACH save (087: same will-future error as A261b, but a
  clean span vs the glued raw span, so frames differ). 102 is not new
  (identical normalised frames both arms).
- sname table (the fix's evidence): all 8 keeps (Morris/Tess/James/Thomas/
  Charles/Louis/Dennis/Miles -> X's) and all 8 strips (Benos/Dilos/Hakis/
  Zoranas/Sarellas/Vannos/Kessas/Ruriks -> X's) exact on A; raw exact on
  6/16 (real s-names the ear already glues right; all 8 fictional strips
  fail raw). seen 4/4 (incl. "jamess ..." -> "James's" via seen stem).
- Latency: normalise median 0.0094 ms, max 0.1396 ms (n=148). A pipeline
  ear+checker+guard median 343.3 ms (context only, no bar).

## Marks, arm A (predictions P270b.1-P270b.6, overall P270b.7, dev P270b.8)

| Mark | Bar | Prediction |
|---|---|---|
| M1 | casual exact TEACH >= 30/40 and >= A261b+15 | A 30-37/40, A261b 5-15/40, margin +18-28; PASS ~60% (P270b.1). Dev 63/64 (+25); blind risk is ear-vocab shapes and so-head holds |
| M2 | casual_q ASK >= 12/15 | A 12-15/15; PASS ~75% (P270b.2). Dev 16/16; blind risk is odd question shapes |
| M3 | lower_trap wrong saves <= 1 | A 0-3; PASS ~45% (P270b.3). Dev 3 (will-future-possessive, check-tail passthrough, is-a); blind traps untested shapes |
| M4 | clean 30/30 identical to A261b | 30/30 by construction, dev 24/24; PASS ~95% (P270b.4) |
| M5 | 0 new wrong saves vs A261b overall | 0-2; PASS ~55% (P270b.5). Dev 1 (087 span-difference class) |
| M6 | median added normaliser time <= 20 ms | ~0.01-0.5 ms; PASS ~99% (P270b.6) |
| ALL | overall registered PASS | ~10% (P270b.7). Needs M1+M2+M3+M5 together |
| DEV | dev table above (no bar) | P270b.8 records the dev numbers as the prediction basis |

Also reported (no bars): every arm's per-family numbers; A261b beside
every figure; every move and every miss by id (no panel text quoted
beyond counts); per-turn normalise ms distribution; ear+checker+guard
latency for context.

## Registered procedure

1. Poll `artifacts/claude-typepanel270b-20260923/SEAL.sha256.txt` (already
   present at seal time) and `shasum -c` it from the repo root; stop and
   report if the check fails.
2. Schema check on load (files, fields, families, labels from the observed
   schema); mismatch = SCHEMA-MISMATCH exit 3, VOID, reported, never
   hand-scored. Panel runner/scorer are written AFTER the seal from the
   observed schema (new files, diffs disclosed, sealed files untouched).
3. Run each arm ONCE (A, A261b: ear wave + checker wave on BensPC, same
   flags/model/port; local score), then RESULTS.md. Never open
   typepanel270.

## Deviations / notes (carried into RESULTS)

- D1 (pre-seal, in the frozen normaliser): check-tail suppression and no
  "so"-head suppression, carried from 270 with the same rationale. A bare-
  so trap costs exactly that hit; reported as-is.
- D2 (pre-seal): whos/whats/wheres/whens/whys/hows -> who's/what's/...
  (contraction, not possessive; needed for casual questions).
- D3: no panel spec was provided with the brief, so the panel
  runner/scorer are written AFTER the seal from the observed schema
  (new files, diffs disclosed, sealed files untouched). Panel rows are
  converted to dev-jsonl shape so the sealed qbuild/devscore path runs
  unchanged (imports only).
- D4: the blind panel was never opened before this seal -- no panel text,
  no gold, no counts read. Its directory listing and SEAL.sha256.txt
  (hashes only) were visible in the worktree before the seal; the panel
  content files were never opened. typepanel270 was never opened.
- D5 (pre-seal dev-gold conventions, from own dev evidence only): ASK gold
  subject = questioned name; pet golds carry the species alias
  (panel-style, as 261b's spec does); M3/M5 count TEACH saves only;
  M5 diffs normalised frames.
- D6: ear-line determinism assumption for M4 (same text -> same frames;
  dev 24/24; registered clean runs both arms to test it, not assume it).
- Known limits: common-word names (will/mark/hope/...) unfixable when
  lowercase; real s-names outside S_NAMES270b and unseen strip; "so"-led
  true facts held by the sealed checker (prompt B); will-future-
  possessive and is-a shapes approved by the checker (dev-measured).

## Seal

Sealed files (new 270b code, PASSMARKS, dev files; 261/261b/270 sealed
files reused read-only, never re-sealed):
scripts/claude_type270b_normalise.py, scripts/claude_type270b_devset.py,
scripts/claude_type270b_turns.py, scripts/claude_type270b_qbuild.py,
scripts/claude_type270b_devscore.py,
artifacts/claude-type270b-20260923/PASSMARKS.md,
artifacts/claude-type270b-20260923/predicted_moves270b.json,
artifacts/claude-type270b-20260923/dev270b.jsonl,
artifacts/claude-type270b-20260923/dev270b_turns.json,
artifacts/claude-type270b-20260923/dev270b_norm.json,
artifacts/claude-type270b-20260923/dev270b_earpreds.json,
artifacts/claude-type270b-20260923/qA/checks.json,
artifacts/claude-type270b-20260923/qA/manifest.json,
artifacts/claude-type270b-20260923/qB/checks.json,
artifacts/claude-type270b-20260923/qB/manifest.json,
artifacts/claude-type270b-20260923/dev270b_pyesA.json,
artifacts/claude-type270b-20260923/dev270b_pyesB.json,
artifacts/claude-type270b-20260923/devreport270b.json
