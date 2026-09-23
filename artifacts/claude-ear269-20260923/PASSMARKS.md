# Exp 269 PASSMARKS: 265's arm A plus a text-level group-owner check (builder, 2026-09-23)

Registered arm A: 265's sealed arm A (v4.1 ear + brake + 265 canon/divert +
checker prompt B at sealed theta 0.25 + 261b span guard, scorer with Ruling 1,
all imported read-only and unchanged) with the ONE change: a deterministic
text-level group-owner check (`scripts/claude_ear269_groupcheck.py`, fixed
before the seal) that runs on the raw turn BEFORE the ear frames and the
brake are used. If the turn states something owned or shared by we/us/our/
ours (not "I/my", not a named person), the turn gets 265's fixed ask-whose
line; group-subject frames still save nothing via the unchanged divert, and
mixed turns still save their non-group frames through the unchanged
checker+guard.

## Frozen config

- Ear: v4.1 checkpoint on BensPC `C:\Users\benja\smolear235\out_v41\smolear235.safetensors`,
  sha256 `55284dec92ea3e6d5d9d99c5afa99ae80a73eafaf644a0c2ca268dcb9fad0bd2`
  (verified with --expect-sha on BensPC before the dev wave; inference
  asserts it). Same inference (claude_smolear257_infer, table v2, --tau 9.3
  recorded for format parity), brake, 265 canon/divert, checker prompt B,
  theta 0.25, 261b guard as 265. Nothing else changes.
- Group check (the ONE change; sealed rules in `claude_ear269_groupcheck.py`,
  written from table-v2 relation vocabulary + general knowledge, tuned only
  on the builder's own dev turns): P1 our+ownable noun; P2a we+residence/work/
  ownership verb (work needs at/for/in; "live to", "own up", "attend to"
  excluded); P2b we+acquisition verb + ownable object ("have lunch",
  "got home", "at home" excluded); P2c we+study/speak with at/for, ownable
  object or capitalized word ("study late" excluded); P3 relative-clause
  ownership ("the boat we bought", "the school our cousins attend"); P4 ours
  possessives ("at/to ours", "ours is the <ownable>", "<ownable> of ours",
  "<ownable> is ours"; "the choice/fault/win is ours" excluded); P5a "us
  two/three/... share/own ..." + ownable; P5b transfer-to-us + ownable
  (told/asked/showed/taught + us never fire); N1 quote guard (attributed
  quoted "our" stays silent). Bare we/us/our with no ownership pattern never
  fires. Deterministic, no model calls, median 0.008 ms on dev.
- Reply rule: 265's diverted per-frame reply when it asks, else the sealed
  generic line "Whose is it? Tell me whose, and I'll remember it." when only
  the text check fires (passes 265's sealed asks_whose shape check), else "".
- Saving rule (sealed interpretation): the check changes only the ASK
  trigger. Arm-A saved frames are 265's arm-A frames byte-identically (the
  scorer asserts this per turn); "save nothing from that turn" holds in the
  per-frame sense (group frames never save via the unchanged divert) and
  mixed non-group frames flow through checker+guard unchanged. M3/M4/M7/M8
  guard this construction.
- Arms: A (registered: text check + 265 A), A265 (265's A exactly, recomputed
  from the same pYES), A261b (261b's A exactly, same pYES), B (138i + 228
  statement items, report only).
- Compute: BensPC RTX 5070 Ti; llama-server started detached by this builder
  via Win32_Process (PID 26480, Qwen3.8-27B-UD-IQ4_XS, 265's exact flags
  --host 127.0.0.1 --port 8081 -ngl 99 -fa 1 q8_0 KV cache, --parallel 1
  -t 6 -c 4096); /completion shape verified (this build answers no /health;
  the checker ran 162/162 queries, 0 fallbacks). Server LEFT RUNNING for the
  registered wave (same PID reused); stopped by exact PID (WMI terminate) at
  the very end. GPU idle 282 MiB before dev; VRAM with both resident
  ~13.7/16.3 GB, no spill. pythonw 13036 and all other BensPC processes
  untouched.

## Dev (before the seal; own wording, fictional names; never any panel)

- Dev set `dev_269.jsonl` (generator sealed): 121 turns = 265's 44 verbatim
  (14 group_owner, 10 mixed, 10 first_person, 10 named) + 77 new 269 turns:
  32 group_new (owner word mid-sentence, "at ours", "us three share ...",
  relative clauses, lower/upper-case variants), 12 mixed_new (mid-sentence
  group clause + first-person/named fact), 33 non_owner_we (we+social/motion
  verbs, we+cognition verbs with named complements, our+event nouns, us as
  speech-verb object, quoted "our", prepositional us). New owner-worded
  turns: 44 (bar: 40+). New non-owner turns: 33 (bar: 30+).
- Text check on dev text: fires on all 68 group_owner+mixed (46+22), fires
  on 0 of 53 controls (33 non_owner_we + 10 first_person + 10 named).
  Adversarial probe (46 extra wordings: "the choice/fault is ours", "got
  home", "share a birthday", "work late", "study late", "own up",
  "attend to", quoted "our dog" said by name): 46/46 as intended.
- GPU ear preds on BensPC (cuda, ckpt sha ok, median 123.2 ms, 66/121
  beamed) + prompt-B pYES for all 162 kept TEACH queries (0 fallbacks,
  median 282.7 ms).
- Dev score (theta 0.25; counts guard forces ALL=false on dev -- dev fams
  are 46/22/10/10/33, not panel counts; marks read directly):
  - group_owner (46): 0 group-subject saves; ask-whose on 46/46 turns
    (18 via 265 divert + 28 via text check only).
  - mixed (22): 14/22 exactly right, ask on 22/22 (divert 10, text-only 12).
    Misses (8): 6 extra checker-guard-passed non-group frames read off the
    group clause (hit kept, exactness lost), 2 neighbour-relation direction
    flips on the other fact (hit 0/1). Ex265 subset reproduces 265 exactly
    (7/10, same 3 misses).
  - first_person: 10/10 hits, 0 lost vs A265. named: 10/10 hits,
    10/10 byte-identical to A265.
  - non_owner_we (33): 0 asks (0 divert + 0 text fires), 0 gold hits lost
    vs A265 (2 hits both arms), 0 wrong saves both arms.
  - M5/M8: 0 new wrong (A wrong 13, A261b wrong 39 = 26 diverted + 13).
  - Wrong rates: A per-fact 13/51, per-turn 13/121; A265 identical;
    A261b 39/77, 37/121; B 0/6 saves, 6/121 hits (abstains almost
    everywhere, as in 265).
  - Ear+checker+guard+groupcheck latency on dev: median 332.61 ms
    (group check 0.008 ms; no bar, reported).
- False asks on dev (the brief's report): 0 in total -- 0 on 33
  non_owner_we, 0 on 10 first_person, 0 on 10 named (text check 0 fires,
  divert 0 asks there).
- Pre-seal plumbing pilot: 269 loader reads 121 dev turns; bad fixture
  (missing ask_whose) -> SCHEMA-MISMATCH exit 3 ok; scorer asserts
  A-saves == A265-saves per turn (holds on all 121).

## Marks, arm A

| Mark | Bar | Prediction |
|---|---|---|
| M1 | group_owner: 0 group-owned facts saved, and >= 27/30 turns ask whose | 0 saves; ask 24-29/30; PASS ~55% (P269.1). Dev 46/46; blind risk is exotic nouns/verbs outside the sealed lists |
| M2 | mixed: >= 12/15 turns exactly right (other fact saved, no group fact) | 8-12/15; PASS ~35% (P269.2). Dev 14/22; misses are extra checker-passed frames + direction flips |
| M3 | first_person: 0 lost vs A265 | 0 lost; PASS ~99% (P269.3). Construction + dev 10/10 |
| M4 | named: 15/15 byte-identical to A265 | exact; PASS ~99% (P269.4). Construction + dev 10/10 |
| M5 | 0 wrong saves overall besides those A261b already makes | 0 new; PASS ~99% (P269.5). Construction (A saves subset of A261b saves) + dev 0 new. Per-fact/per-turn rates reported for A, A265, A261b, B |
| M6 | false asks on non_owner_we + first_person + named <= 1 total | 0-1; PASS ~85% (P269.6). Dev 0/53; blind risk is our+ownable wordings the writer files as non-owner |
| M7 | gold TEACH hits lost on non_owner_we, A vs A265, <= 1 | 0 lost; PASS ~99% (P269.6). Construction + dev 0 |
| M8 | 0 new wrong saves A vs A265 across all families | 0 new; PASS ~99% (P269.6). Construction + dev 0 |
| ALL | overall registered PASS | ~20% (P269.7). Needs M1+M2 together; M3-M8 near-certain |

Latency (no bar, P269.8): ear+checker+guard+groupcheck median ~300-450 ms
per turn (dev 332.61 ms); group check ~0.01 ms; B mostly abstains
(report-only).

Also reported (no bars): per family; M1 ask split (divert vs text-only);
each wrong/diverted/text-asked frame by category only (never quoted);
panel theta curve for A.

## Deviations / notes (carried into RESULTS)

- D1: counts guard in the scorer verdict requires exact panel family counts
  (30/15/20/15/20, enforced by the strict loader); on dev it forces
  ALL=false -- read dev marks directly instead. Registered run unaffected.
- D2: the blind panel (artifacts/claude-ourpanel269-20260923/) is never opened
  before this seal -- no listing of its contents, no hashes, no line counts
  (its existence was visible in the artifacts directory listing alongside
  other folders; nothing inside was ever read). After this seal: poll for
  its SEAL.sha256.txt every few minutes up to 120 minutes, `shasum -c`
  from the repo root, strict schema check (269 keys incl. ask_whose + exact
  family counts 30/15/20/15/20 and ids o269-001..100; SCHEMA-MISMATCH exit
  3), then every arm ONCE. Never run ourpanel265 or any earpanel (test-only).
- D3: llama-server handling. Plain `taskkill /PID` is denied (session-0
  isolation, as in 265); started detached via Win32_Process (server PID
  26480), final stop by WMI Terminate on that exact PID, confirmed with
  nvidia-smi. This llama-server build answers no /health; readiness was
  verified through /completion (162/162 checker queries, 0 fallbacks).
  Server left running between dev and registered waves (same flags/model/
  PID); pythonw 13036 and all other BensPC processes untouched.
- D4: diverted group frames still consume a checker query (shared pYES file
  keeps A265/A261b byte-exact); arm A never uses those values. Documented,
  not tuned.
- D5: M5/M8 "new wrong" = per-turn multiset difference of wrong frames
  (A minus A261b / A minus A265). A saves == A265 saves by construction
  (asserted per turn in the scorer); both save ⊆ A261b saves (divert/
  checker/guard only remove; guard is per-frame), verified on dev.
- D6 (sealed interpretation): the text check changes only the ASK trigger;
  whole-turn save suppression is per-frame via the unchanged divert (mixed
  non-group frames always flow through). A pure group turn whose ear
  hallucinates a non-group frame keeps 265's behavior for that frame
  (counted in M5/M8, never new). The director can judge this reading from
  the M5/M8 numbers.
- D7: known detector residuals (dev-measured categories, not tuned):
  ownership verbs outside the sealed lists (walk, feed, carry) do not fire;
  death/loss contexts ("our dog died") still fire via P1; "ourselves"
  needs an ownable noun nearby. All reported with the dev counts above
  (0 misses, 0 false asks on 121 dev + 46 adversarial probes).

## Seal

Sealed files (new 269 code, PASSMARKS, dev files; 265/261/261b sealed files
reused read-only, never re-sealed):
scripts/claude_ear269_groupcheck.py, scripts/claude_ear269_arms.py,
scripts/claude_ear269_panel.py, scripts/claude_ear269_turns.py,
scripts/claude_ear269_armb.py, scripts/claude_ear269_qbuild.py,
scripts/claude_ear269_scoremain.py, scripts/claude_ear269_devset.py,
artifacts/claude-ear269-20260923/PASSMARKS.md,
artifacts/claude-ear269-20260923/dev_269.jsonl,
artifacts/claude-ear269-20260923/dev269_earpreds.json,
artifacts/claude-ear269-20260923/dev269_manifest.json,
artifacts/claude-ear269-20260923/dev269_pyes.json,
artifacts/claude-ear269-20260923/dev269_bpreds.json,
artifacts/claude-ear269-20260923/dev269_score.json
