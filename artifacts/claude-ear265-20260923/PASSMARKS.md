# Exp 265 PASSMARKS: 261b's arm A plus the "our/we" ask-whose rule (builder, 2026-09-23)

Registered arm A: 261b's sealed arm A (v4.1 ear + brake + entailment checker at
sealed theta 0.25, prompt B + mixed-case span guard, scorer with Ruling 1,
all imported read-only and unchanged) with the ONE change from
design/v3/30-modes/265-our-ask.md (Ben's ruling
our-policy-decision-20260923.md): the canonicaliser maps only
i/me/my/mine/myself to "me"; a TEACH frame whose subject is we/us/our/ours/
ourselves (any case) is never saved -- it is diverted to the fixed reply
"Whose <relation words> is <V>? Tell me whose, and I'll remember it." with 0
writes. Every other frame is handled as before.

## Frozen config

- Ear: v4.1 checkpoint on BensPC `C:\Users\benja\smolear235\out_v41\smolear235.safetensors`,
  sha256 `55284dec92ea3e6d5d9d99c5afa99ae80a73eafaf644a0c2ca268dcb9fad0bd2`
  (verified by hash with --expect-sha on BensPC before the dev wave; inference
  asserts it). Same inference (claude_smolear257_infer, table v2, --tau 9.3
  recorded for format parity), brake, checker prompt B, theta 0.25, guard as
  261b. Nothing else changes.
- 265 rule (`scripts/claude_ear265_canon.py`, fixed before the seal):
  FIRST_WORDS = i/me/my/mine/myself -> "me" (TEACH+ASK subjects, after the
  brake, same position as 261's canon). GROUP_WORDS = we/us/our/ours/ourselves
  (any case): TEACH frames with such subjects divert (why=ASK_WHOSE, fixed
  reply, 0 writes, no checker query spent by arm A though a pYES is recorded
  for the A261b arm). ASK group subjects pass through unchanged (questions
  never write; registered panel has no question families).
  Relation words = table-v2 canonical name with _ -> space (raw fallback).
  Turn reply = per-diverted-frame replies joined with one space; "" if none.
  Sealed ask check: reply starts "Whose " and contains the fixed tail.
- Checker/guard/scorer matching: 261 prompt B + theta 0.25 + 261b guard +
  Ruling-1 narrower patch, all imported read-only. One recorded pYES file
  serves both ear arms (claims for non-diverted frames are byte-identical
  under both canons; teach indices count kept TEACH in kept order).
- Arms: A (registered: 265 divert + checker + guard), A261b (261b's A exactly,
  recomputed from the same pYES), B (138i + 228 statement items, report only).
- Compute: BensPC RTX 5070 Ti; llama-server started by this builder detached
  via Win32_Process (PID 27936 launcher / PID 30076 server, Qwen3.8-27B-
  UD-IQ4_XS, --host 127.0.0.1 --port 8081 -ngl 99 -fa 1 q8_0 KV cache,
  --parallel 1 -t 6 -c 4096); /health ok; VRAM with both resident ~13.7/16.3
  GB, no spill. Server LEFT RUNNING for the registered wave (same PID reused);
  stopped by exact PID (WMI terminate; taskkill is blocked by session-0
  isolation -- see D3) at the very end.

## Dev (before the seal; own wording, fictional names; never any panel)

- Dev set `dev_265.jsonl` (generator sealed): 44 turns -- 14 group_owner
  (our/we/ours/lowercase/OUR x pet, house, city, son, daughter, car, teacher,
  cottage, language, boss, school), 10 mixed (group clause + first-person or
  named fact), 10 first_person, 10 named.
- GPU ear preds (cuda, ckpt sha ok, median 144.8 ms, 41/44 beamed): all 14
  group turns surface group-word subjects (Our/We/our/OUR); all 10 mixed
  surface a group frame AND a second frame; first_person all first-word
  subjects; named all name subjects (2 with flipped relation direction, 1 odd
  relation -- ear-level, A261b shares them).
- Checker pYES for all 102 kept TEACH queries (canon + nc), prompt B,
  0 fallbacks, median 281.5 ms.
- Dev score (theta 0.25; counts guard fires COUNTS=false on dev -- dev fams are
  14/10/10/10, not panel counts; marks read directly):
  - group_owner: 0 group-subject saves; ask-whose on 12/14 turns. Misses (2):
    brake dropped an odd-relation group frame; an "Ours"-possessive turn whose
    ear subject span is not literally in the turn.
  - mixed: 7/10 exactly right. Misses (3): twice the ear read the group clause
    with a first-person subject (no divert; extra save) -- once with the other
    fact still hit, once relation-direction flip on the other fact.
  - first_person: 10/10 hits, 0 lost vs A261b. named: 10/10 byte-identical.
  - M5: 0 new wrong saves (A wrong 5, all checker-guard-passed non-group
    frames A261b also saves; A261b wrong 25 = 20 diverted group frames + 5).
  - Wrong rates: A per-fact 5/31, per-turn 5/44; A261b 25/51, 24/44; B 0/6
    saves, 6/30 hits (rule reader abstains almost everywhere on dev).
  - Ear+checker+guard latency on dev: median 356.6 ms (no bar; reported).
- Pre-seal plumbing pilot (synthetic 4-turn fixture in /tmp only): qbuild dev
  4 rows -> 8 checks; scoremain --dev scores (divert+ask on all group turns,
  mixed partial as designed); bad fixture -> SCHEMA-MISMATCH exit 3 ok.

## Marks, arm A

| Mark | Bar | Prediction |
|---|---|---|
| M1 | group_owner: 0 group-owned facts saved, and >= 27/30 turns ask whose | 0 saves; ask 24-28/30; PASS ~45% (P265.1). Dev 12/14 ask; blind risk is ours/us/lowercase/odd-relation turns |
| M2 | mixed: >= 12/15 turns exactly right (other fact saved, no group fact) | 11-14/15; PASS ~55% (P265.2). Dev 7/10; misses are ear misattribution + direction flips |
| M3 | first_person: 0 lost vs A261b | 0 lost; PASS ~95% (P265.3). Construction (divert needs a group subject) + dev 10/10 |
| M4 | named: 15/15 byte-identical to A261b | exact; PASS ~99% (P265.4). Construction, verified on dev 10/10 |
| M5 | 0 wrong saves overall besides those A261b already makes | 0 new; PASS ~99% (P265.5). Construction (A saves subset of A261b saves) + dev 0 new. Per-fact/per-turn rates reported for A, A261b, B |
| ALL | overall registered PASS | ~25% (P265.6). Needs M1+M2 together; M3/M4/M5 near-certain |

Latency (no bar, P265.7): ear+checker+guard median ~350-450 ms per turn
(dev 356.6 ms); B mostly abstains (report-only).

Also reported (no bars): per family; each wrong/diverted frame by category
only (relation + status, never quoted); panel theta curve for A.

## Deviations / notes (carried into RESULTS)

- D1: counts guard in the scorer verdict requires exact panel family counts
  (30/15/20/15, enforced by the strict loader); on dev it forces ALL=false --
  read dev marks directly instead. Registered run unaffected.
- D2: the blind panel (artifacts/claude-ourpanel265-20260923/) is never opened
  before this seal -- no listing, no hashes, no line counts. After this seal:
  poll for its SEAL.sha256.txt every 2 minutes up to 120 minutes, `shasum -c`
  from the repo root, strict schema check (265 keys incl. ask_whose + exact
  family counts; SCHEMA-MISMATCH exit 3), then every arm ONCE. Never run
  earpanel257/261/261b (test-only).
- D3: llama-server handling. Plain `taskkill /PID` is denied (session-0
  isolation); WMI `Terminate()` verified working on a dummy process and used
  for the final stop (server PID 30076 + launcher cmd PID 27936), confirmed
  with nvidia-smi. Server left running between dev and registered waves (same
  flags/model/PID); pythonw 13036 and all other BensPC processes untouched.
- D4: diverted group frames still consume a checker query (shared pYES file
  keeps A261b byte-exact); arm A never uses those values. Documented, not
  tuned.
- D5: M5 "new wrong" = per-turn multiset difference of wrong frames
  (A minus A261b). A saves ⊆ A261b saves by construction (divert/checker/guard
  only remove; guard is per-frame), verified on dev.

## Seal

Sealed files (new 265 code, PASSMARKS, dev files; 261/261b sealed files reused
read-only, never re-sealed):
scripts/claude_ear265_canon.py, scripts/claude_ear265_arms.py,
scripts/claude_ear265_panel.py, scripts/claude_ear265_turns.py,
scripts/claude_ear265_armb.py, scripts/claude_ear265_qbuild.py,
scripts/claude_ear265_scoremain.py, scripts/claude_ear265_devset.py,
artifacts/claude-ear265-20260923/PASSMARKS.md,
artifacts/claude-ear265-20260923/dev_265.jsonl,
artifacts/claude-ear265-20260923/dev265_earpreds.json,
artifacts/claude-ear265-20260923/dev265_q/checks.json,
artifacts/claude-ear265-20260923/dev265_q/manifest.json,
artifacts/claude-ear265-20260923/dev265_pyes.json,
artifacts/claude-ear265-20260923/dev265_bpreds.json,
artifacts/claude-ear265-20260923/dev265_score.json
