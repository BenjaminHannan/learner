# g406: can GLM 5.3 Flash spot made-up claims about the user the way the blind judges do?

"Making things up about you" thread. Written 2026-09-26 19:29 UTC by date -u, fixed before any GLM call. DEV data only. Nothing is
trained here. Cost: $0 (Mac CPU, GLM through Ben's opencode subscription).

## Why
OBVIOUS FIX FIRST (Thread manager 19:24 UTC). The textbook fixes for a talker that makes things up about the user are:
tell it not to (mu-403 FAIL, 882b7b237); check before speaking (the 1B's own check, AUC 0.54 vs bar 0.65,
artifacts/claude-mu403-20260926/AUC.md); give it the user's own words (mu-405, running); and train it on replies that
make nothing up. The last one is untested. Its plan (mu-406, artifacts/claude-mu406-20260926/PLAN-draft.md): the 1B
practises on its own sampled replies, keeping only those a marker calls clean. Training labels may not be Claude-judged
(Ben 16:39), so the marker is GLM, and a GLM marker needs this gate first (the k1e GLM critic missed its agreement bar,
25e31f575).

## Setup
- Marker: scripts/claude_g406_glm.py. One call per transcript through scripts/claude_glm_opencode.py call() (sha256
  3b597086...). The rubric is the blind judges' own text (artifacts/claude-mu402-20260926/JUDGE-claims.md, from "For
  EVERY assistant reply" through "If yes, flag it.", unchanged); only the framing differs (one transcript, one JSON
  line back). The prompt is fixed now and is not changed after any GLM answer is seen.
- Items: every claims packet of mu-402 and mu-403/404 (560 transcripts, 2,990 assistant replies). Each was read by
  two blind Opus judges: 336 replies flagged by at least one judge ("either"), 261 by both (base either-rate 0.1124,
  from the judges' files; counted at $0 before any GLM call).
- Count: scripts/claude_g406_count.py.

## Marks
- V (validity): GLM gives a usable answer (right length, only 0/1) on at least 95% of the 560 transcripts (532).
  Otherwise INCONCLUSIVE.
- G1 (catches what the judges agree on): of the replies both judges flagged, GLM flags at least 70%.
- G2 (the kept set is clean): among replies GLM calls clean, the share flagged by either judge is at most half the
  base either-rate.
- G3 (enough is kept): GLM calls at least 50% of replies clean.
- PASS = V, G1, G2 and G3. Proved wrong (GLM's marks carry no signal): among replies GLM flags, the either-rate is no
  higher than the base either-rate.
- Reported, not marked: recall on "either", kappa against "either", and each source separately.

## What each result means for mu-406
- PASS: mu-406's training replies are picked with GLM's marks. The two-session version of the rubric (earlier
  messages shown and counted as said, as JUDGE-claims405.md) is checked again with these same marks on mu-405's
  judged packets (g406b) before any training.
- FAIL or INCONCLUSIVE: no GLM labels and no rewording of the prompt. mu-406 uses code-only labels instead: a reply is
  dropped when it names a code-chosen fact value the chat never gave. That catches made-up details but not made-up
  feelings or situations, and the plan will say so.

## Prediction (before any GLM call)
- P406g.1: g406 PASS, 35% (the k1e GLM critic was lenient: 43 flags where judges gave 31).
