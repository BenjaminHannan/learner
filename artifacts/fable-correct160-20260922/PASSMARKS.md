# Exp 160 PASSMARKS — bare corrections (sealed BEFORE any registered run)

Registered single-change fix on loop150 (scripts/fable_loop150_agent.py,
artifacts/fable-correct160-20260922/loop160-config.json; loop150 = loop129b
+ 139b value guard + 150 subject guard, read-only, no file edited). Exp-152
red team class N6: a bare "no wait, it's Denver" right after a teach is
ignored — the correction-prefix rules only accept "Actually"/"no," plus a
full sentence.

Responsible code (Step 1): scripts/fable_agent_loop.py:95 (`_CORRECTION`
prefix set) and, on the real chain, scripts/fable_loop102_agent.py:92
(`_CORRECTION_PREFIX_RE`: "actually,"/"actually "/"no,"/"correction:"/
"sorry[ ,] I meant" + full sentence). "no wait, it's Denver" matches no
prefix; the teach-template parse of the whole turn returns None; the exact
old path clarifies with 0 writes and the taught triple stays stale.

THE ONE CHANGE (scripts/fable_fix160_barecorrect.py, BareCorrect160Mixin;
thin loop160 in scripts/fable_loop160_agent.py with --daemon entry incl.
idle_seconds): a bare correction matching a sealed prefix with a valid V
applies to the session's most-recent saved teach (the latest user turn
that stored exactly one teach/correct triple; intervening questions,
clarifies, refusals and small talk neither set nor clear it, only a newer
stored teach/correct replaces it). It synthesizes {"act":"correct", same
name/relation/is_person, value V} through super()._act — the loop's
EXISTING correction machinery (same guards, same "Saved: ..." reply, same
audit trail and supersede rules as "Actually, X's R is V."). With no saved
teach yet in the session it answers the sealed clarify with 0 writes.
Non-matching turns never re-tag: byte-identical to loop150. Previous
triple persists in state.json ("last_teach160").

Correction 2026-09-22 (post-seal, re-sealed before the bench/marks/session
registered runs; only the probe had run): v1 said "IMMEDIATELY previous
user turn" strictly (previous-turn question/refusal/small-talk/two+-ago ->
clarify). That clarifies on the sealed N6 session turn itself (S3n6: teach
3 turns back, previous turn a question), so it cannot meet the sealed C2
bar "the N6 turns become OK". Memory is the most-recent saved teach;
C1-B cases were recomposed to carry no saved teach at all (counts
unchanged: 20/12/12); predictions P160.1-P160.5 unchanged. See
RESULTS.md deviations. Old seal: superseded by SEAL.sha256.txt.

## Sealed bare-correction shapes (case-insensitive, whitespace-collapsed, one trailing "." stripped)

- "no wait, [it's|its|it is] V" (e.g. "no wait, it's Denver")
- "wait, [it's|its|it is] V" (e.g. "wait, it's Denver")
- "sorry, [it's|its|it is] V" (e.g. "sorry, it's Denver")
- "I meant[,] V" (e.g. "I meant Denver"; no it's-form)
- "no, [it's|its|it is] V" (e.g. "no, Denver")
V valid iff ALL hold: non-empty; no "?" or "!" in the turn; no "'s"/"'s"
and no " is "/" are " in V; no ","/";"/":" in V; <= 8 words; not a bare
question word (what/who/where/when/why/how/which/whom/whose); does not
start with "to ". Else the base path runs untouched.
No-fresh-teach clarify (exact, 0 writes): Which fact should I change? You
can say e.g. "Actually, Tom's city is Denver."
Deliberate: bare "no, thank you" right after a teach rewrites the value to
"thank you" (the sealed "no, V" shape, no exception carved).

Sealed inputs:
- C1 probe: artifacts/fable-correct160-20260922/cases160.json (44
  dialogues: 20 bare-after-teach with explicit-"Actually" twins, 12
  bare-without-teach, 12 unrelated no/wait/sorry).
- loop160-config.json (loop150 config + 2 renamed plug strings).
- G1 reference: sealed loop150 bench rows
  (artifacts/fable-fix150-20260922/fable_bench150_loop150_*_rows.jsonl) via
  scripts/fable_loop129b_bench.py run_item by import.
- G2 reference: sealed loop150 marks
  (artifacts/fable-fix150-20260922/marks150) via scripts/fable_marks123_all.py.
- G3/C2 reference: sealed T-T session rows
  (artifacts/fable-session152-20260922/turns152-T-T-*.json) via
  scripts/fable_session152_run.py run_session/judge by import.

## Marks (integer counts, every seed/case reported, never averaged)

- C1 NEW probe of 44 dialogues (scripts/fable_fix160_probe.py): A 20/20
  bare-after-teach -> triples AND turn-2 reply equal to the explicit
  "Actually, ..." twin run on a fresh loop; B 12/12 bare with no saved
  teach anywhere in the dialogue -> exactly the sealed clarify with 0 FACT
  writes on the bare turn; C 12/12 unrelated
  no/wait/sorry -> every reply byte-equal to loop150 with equal FACT
  counts. 44/44 OK.
- C2/G3 sessions152 re-run through loop160
  (scripts/fable_fix160_session152.py): exactly ONE predicted move,
  S3-teachers-correction turn 6 "no wait, it's denver" UNHELPFUL->OK with
  +1 write and reply "Saved: Rao's city is denver."; the other 179 T-T
  turns byte-identical (reply, statuses, writes); 0 new WRONG, 0 other new
  writes.
- G1 bench121 new + old fresh split + Fable-Edit per-item verdicts AND
  replies identical to the sealed loop150 rows
  (scripts/fable_fix160_bench.py): ZERO predicted moves, 0 new wrong.
- G2 scripts/fable_marks123_all.py suites per-case verdicts identical to
  loop150's marks150 run (same --workers 4 invocation, --out into this
  exp's marks160 dir): ZERO predicted moves.
- G4 each registered run (probe, bench, marks123, sessions) < 25 min
  wall-clock (< 1500 s) Mac CPU
  (export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project
  --python 3.12 --with torch --with numpy python -B ...); daemon wrappers
  take idle_seconds.

## Pre-seal evidence (dev only, NOT registered runs)

- Pure-function scan, parse_bare_correction over 4375 bench strings
  (taught+question, edit200 + old_s2fresh + new_121): 0 hits.
- Same scan over 180 sealed session152 turns: exactly 1 hit (S3 turn 6).
- Same scan over 145 redteam136 cases + 1333 redteam110/81 suite strings:
  0 hits.
- Dev smoke (fresh loops, loop160 vs loop150): teach+"no wait, it's
  Denver" triple+reply equal to teach+"Actually, ..." twin; chained bares
  (Austin->Reno) supersede; question/small-talk/refused-teach then bare ->
  sealed clarify, 0 writes; "no idea"/"wait, who is Tom's boss?"/
  "sorry, what?"/"wait, what"/"I meant to ask where Tom lives"/
  full-sentence "wait, Tom's city is Denver."/"no, Tom's city is Denver."
  byte-identical to loop150.

A registered FAIL is recorded as FAIL, never re-run into a pass. Claims
never exceed evidence. No code edit after sealing except as reported with
affected marks re-run in the open.

## Registered reproduce (run from worktree root, after sealing)

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix160_probe.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix160_bench.py
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop160_agent.py --config artifacts/fable-correct160-20260922/loop160-config.json --out artifacts/fable-correct160-20260922/marks160 --workers 4
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix160_session152.py
