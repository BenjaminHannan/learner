# Exp 264 PASSMARKS: the question-answering checker (builder, 2026-09-23)

Registered arm A: 261b's registered arm A (v4.1 ear + speaker canonicaliser +
brake + span guard) with the YES/NO entailment checker REPLACED by the
question-answering checker (design/v3/30-modes/264-qa-checker.md). 261 and
261b stay FAIL; this is the discovery follow-up Ben picked.

## Frozen config

- Ear: v4.1 checkpoint on BensPC
  `C:\Users\benja\smolear235\out_v41\smolear235.safetensors`, sha256
  `55284dec92ea3e6d5d9d99c5afa99ae80a73eafaf644a0c2ca268dcb9fad0bd2`
  (verified by hash on BensPC before dev waves; inference asserts it).
  Same inference, brake, relation table v2, canonicaliser as 261/261b,
  imported read-only. Nothing else changes.
- QA checker (the ONE change; `scripts/claude_earcheck264_qa.py`,
  PROMPT_VERSION `v5-plan-inflect + qrel-v1 + qown-v3 + qmap-v3(owner-suffix)`).
  For each TEACH frame (S, R, V) the brake keeps, Qwen3.8-27B is asked three
  questions at temperature 0 with thinking off (same Qwen3 chat-template
  transport as 261's sealed checker, n_predict 32, sent one after another):
  Q-value (V hidden), Q-owner (S hidden), Q-relation (R hidden).
  Save iff V is one of Q-value's answers AND S is one of Q-owner's ("the
  speaker" matches "me") AND Q-relation's answer maps to R (case- and
  space-normalised; split on ' | '; NOT STATED / AMBIGUOUS never match).
  Otherwise hold back as UNSURE (`why=QA_UNSURE`, `qa_failed` lists the
  failing questions). No threshold, nothing tuned. ASK frames never checked.
- Q-relation mapping (through table v2 plus deviation D-rel-map, all sealed
  in qa.py): names, aliases, narrower, ancestors (a broader answer maps:
  "pet" for cat/dog; the sealed scorer's Ruling 1 already treats the species
  family as one concept), possessive-strip ("The speaker's cat" -> "cat"),
  head-noun acceptance ("color" for favorite_color; compound relatives stay
  discriminated because "mother" is not the last word of "mother in law"),
  spaceless normalisation ("home town" -> "hometown"), pet-family
  interchange (pet/dog/cat/rabbit/hamster/parrot/horse), truncations
  (date/birthday -> date_of_birth, country -> country_of_origin).
- Span guard (261b sealed, imported read-only) stays after the QA checker.
  The QA checker + guard only hold back; they never add, edit or reorder, so
  every A frame is byte-identical in A_brake (M6 by construction, verified).
- Scorer (`scripts/claude_earcheck264_scoremain.py`): 261b's sealed scorer
  (Ruling 1 included, imported not reimplemented) in a new wrapper that also
  reports wrong saves per saved fact AND per turn for every arm.
- Arms: A (registered: brake -> canon -> QA -> guard), A261b (261b's A
  exactly: brake -> canon -> YES/NO checker at sealed theta 0.25, prompt B ->
  guard), A_brake (canon + brake), B (138i + 228, statement fams).
- Compute: BensPC RTX 5070 Ti; llama-server started by this builder
  (Qwen3.8-27B-UD-IQ4_XS, --host 127.0.0.1 --port 8081 -ngl 99 -fa 1 q8_0 KV
  cache, --parallel 1 -t 6 -c 4096; first background launch died silently,
  relaunched fully detached via Win32_Process `cmd /c ...`, PID 1424,
  /health ok). VRAM with Qwen resident ~13.6/16.3 GB, no spill. Server
  stopped by exact PID at the end. "our/we" turns excluded from panel 264
  per Ben's ruling (separate exp 265); D_our dev reported for the record.

## Dev (before the seal; never any panel)

- Step 1 (reproduction): 261's sealed theta sweep rerun from its sealed
  files: sweep byte-equal (theta 0.25, recall 1085/1180 = 91.9%, wrong 13,
  unsure 109). 261b guard reproduction: 1098 checker-saved TEACH frames ->
  guard holds 8 (0.7%), all subject_mix on tag base, all 8 RIGHT (false
  holds). Pipeline matches.
- Step 2 (QA on 261's dev: 257 dev split d257 + dev_checker dc):
  1207 kept TEACH frames -> QA held 316, guard held 7, false holds 235,
  wrong saves let through 15 (base 4, R1 1, C4 1, C6 1, D_apos 8).
  Recall (sealed 235 match, no Ruling 1): d257 741/1009 = 73.4% wrong 7;
  dc 128/171 = 74.9% wrong 8. Holds by tag: D_pre 5/5 held 0 wrong;
  D_checkq 13/13 held 0 wrong; D_plan 26 held 0 wrong (8 false);
  D_our 36/36 saved 0 wrong; D_plain 60/60 saved 0 wrong; R2 7/7 held;
  base 92 held (80 relation) 4 wrong; R1 63 held 1 wrong; C6 12 held 1
  wrong; D_apos 22 held 8 wrong. QA per-question latency median 286.7 ms,
  p90 359.6, max 850.0, 0 fallbacks (3621 answers).
- Step 2b (QA on 261b's dev b5 + own dev d264): b5 recall 42/56 = 75.0%
  wrong 4. Own dev (`dev_264.jsonl`, generator sealed): 16 wrong-relation
  traps (D_rel) + 16 stale values (D_stale), own wordings, fictional names.
  GPU ear preds (median 240.9 ms, 26/32 beamed, ckpt sha ok) + QA: kept 38,
  recall 18/35 = 51.4%, wrong 5. D_rel wrong 4 (structural residuals: an
  inferred coworker-employer frame all three questions agree on; a
  spouse-arrangement frame the relation gate maps wife->spouse on; a
  near-vs-in value echo; an ear-convention pet-subject frame); D_stale
  wrong 1 (retired employer with no replacement named); D_typo (b5's) 4.
  False holds 11 (owner-echoes-value model errors, city-conflation on
  birthplace, employer-conflation on boss -- all principled holds).
- Wording log (every change, dev-tested, pilots above): v0 spec-verbatim
  (pretend 0/2 held) -> v1 explicit NOT STATED triggers (pretend 3/3, plan
  3/3, plain 3/3, checkq 1/3) -> v2 decide-first (checkq 3/3, plain 3/3)
  -> v3 owner de-anchor (third-person 8/8 fixed, pretend 4/4 intact)
  -> Q-relation v1 single-word (17/24 previously-unmapped now map)
  -> v4 explicit so-check (8/8 so-checks held, plain 3/3 intact)
  -> v5 plan inflections ("trains/studying to be"; fixed the one dev
  goal-leak) + owner tail-of-answer acceptance.
- Per-turn ear+QA latency on d257 dev (n=1530): median 874.5 ms, p90
  1131.8, max 2942.6.
- Pre-seal plumbing pilot (synthetic 3-item fixture in /tmp only):
  scoremain saves good frames (pet-ancestor mapping verified), holds bad,
  M1-M6 + per-fact/per-turn rates + details categories ok; bad fixture
  (149 lines) -> SCHEMA-MISMATCH exit 3 ok.

## Marks, arm A

| Mark | Bar | Prediction |
|---|---|---|
| M1 | no_save saves <= 1 | 0-3 saves; PASS ~55% (P264.1). Dev: pretend/checkq/plan all held |
| M2 | wrong saves <= 1 | 2-6 wrong; PASS ~25% (P264.2). Dev ~1%/turn + new R16/R17 traps |
| M3 | exact TEACH recall >= 85% and >= B + 30 | 65-78%; PASS ~15% (P264.3). Dev 73-75%; three gates multiply holds |
| M3b | held back <= 12% of gold TEACH | 20-30%; PASS ~10% (P264.4). Dev 323/1180 = 27.4% |
| M4 | exact ASK recall >= 90% | 90-100%; PASS ~85% (P264.5). ASK untouched |
| M5 | median per turn <= 800 ms | 850-1100 ms; PASS ~5% (P264.6). Dev median 874.5 (3 x ~287 + ear) |
| M6 | every A frame byte-identical in A_brake | exact; PASS ~99% (P264.7). Holds only remove |
| ALL | overall registered PASS | ~5% (P264.8) |

Wrong-save rates (no bar): A per-fact ~1-3%, per-turn ~2-5%; A261b, A_brake
and B reported with the same rates (P264.9).

Also reported (no bars): A vs A261b on M1-M4; per family; per tag
R1-R17 (R7 dropped); panel QA latency distribution; each held/wrong frame
by category only.

## Deviations / notes (carried into RESULTS)

- D1 (prompt wording): Q-value/Q-owner lead with a fact-vs-check decision
  and name the check patterns (tag questions, so-restatements, pretend
  verbs, plan verbs incl. inflections, denial, replacement); Q-relation is
  constrained to one relation word with format examples. Sealed after the
  dev pilots above; the spec's three-question save rule is unchanged.
- D2 (D-rel-map): Q-relation mapping accepts ancestors, possessive-stripped,
  head-noun, spaceless-normalised, pet-family and date/country-truncation
  answers beyond the spec's "names, aliases or narrower". All trap-safe by
  construction (wife-vs-in-law, employer-vs-school, city-vs-hometown pairs
  share no accepted link); dev wrong let-through stayed 15-16 while the
  mapping fixed ~40 false holds (see devreport_261.json).
- D3: the blind panel (artifacts/claude-earpanel264-20260923/) is never
  opened before this seal -- no listing, no hashes, no line counts. After
  this seal: poll for its SEAL.sha256.txt every 2 minutes up to 120 minutes,
  `shasum -c` from the repo root, strict schema check, then every arm ONCE.
  Never run earpanel257, earpanel261 or earpanel261b.
- D4: llama-server first background launch died silently (empty log);
  relaunched via Win32_Process `cmd /c` (PID 1424). Stopped by exact PID at
  the end; nvidia-smi confirms idle. pythonw 13036 untouched.
- D5: M5 counts ear-greedy ms + all three QA ms + guard ms per turn
  (beam-decode time excluded); QA questions sequential (server has 1 slot).

## Seal

Sealed files (new 264 code, PASSMARKS, dev files; 261/261b sealed files
reused read-only, never re-sealed):
scripts/claude_earcheck264_qa.py, scripts/claude_earcheck264_client.py,
scripts/claude_earcheck264_qbuild.py, scripts/claude_earcheck264_arms.py,
scripts/claude_earcheck264_scoremain.py, scripts/claude_earcheck264_panel.py,
scripts/claude_earcheck264_turns.py, scripts/claude_earcheck264_armb.py,
scripts/claude_earcheck264_devset.py, scripts/claude_earcheck264_devreport.py,
artifacts/claude-earcheck264-20260923/PASSMARKS.md,
artifacts/claude-earcheck264-20260923/dev_264.jsonl,
artifacts/claude-earcheck264-20260923/dev264_earpreds.json,
artifacts/claude-earcheck264-20260923/dev257_qa.json,
artifacts/claude-earcheck264-20260923/devcheck_qa.json,
artifacts/claude-earcheck264-20260923/dev261b_qa.json,
artifacts/claude-earcheck264-20260923/dev264_qa.json,
artifacts/claude-earcheck264-20260923/dev257_qmanifest.json,
artifacts/claude-earcheck264-20260923/devcheck_qmanifest.json,
artifacts/claude-earcheck264-20260923/dev261b_qmanifest.json,
artifacts/claude-earcheck264-20260923/dev264_qmanifest.json,
artifacts/claude-earcheck264-20260923/devreport_261.json,
artifacts/claude-earcheck264-20260923/devreport_264.json
