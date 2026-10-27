# Exp 224b PASSMARKS (agent side) — sealed before the registered runs

Agent: scripts/fable_loop224_agent.py (wraps loop138i read-only: build_agent138i,
then instance-level taps on the ears and one swap on loop.turn). Config for every
run: artifacts/fable-agent138i-20260922/loop138i-config.json.
Sentences (fixed in scripts/fable_decline224.py, sealed with 224a):
- Q1 (ears produced an ask, notebook has no value): "I don't know that yet — you haven't told me."
- Q2 (question the ears could not turn into a lookup): "I didn't understand that question — could you say it another way?"
- S1 (statement the loop could not save): "I didn't understand that well enough to save it — could you say it another way?"
Swap fires only when loop138i's turn returned exactly the glue
(S105.HONEST_DECLINE + L138.DECLINE_SUFFIX) with last_routed intent DECLINE.
Type = what the pipeline did: any ask action this turn -> Q1; else the ears'
question branch ran, or the text ends with "?", or the exp-151 question
predicate fires (the ears' own routing tests) -> Q2; else S1.

Cases: artifacts/fable-decline224-20260922/224b/cases224b.json — 30 Q2 + 30 S1
(pre-checked on 138i: each gets exactly the glue, 0 writes) + 20 Q1 controls.
Fictional names only.

## Marks
- B1: B1 driver scripts/fable_decline224_b1.py, fresh agent + fresh scratch state
  per case. Registered 138i pre-run: 30/30 Q2 and 30/30 S1 get the glue with 0
  writes; 20/20 Q1 controls do NOT get the glue. loop224 run: 30/30 Q2 get the Q2
  sentence, 30/30 S1 get the S1 sentence (kind logged = case type), 0 writes on
  every probe turn; 20/20 Q1 controls byte-identical to 138i.
  DEVIATION (declared before the seal): the brief's ">= 20 Q1 cases that get the glue
  today" cannot be met — on 138i an ask always yields an answer record ("I don't
  know Mira's father." / "I don't know anyone called Zed."), so notebook_missed is
  False and the glue is never served for Q1. The Q1 sentence is wired but
  unreachable on 138i; the 20 Q1 cases are controls (must stay byte-identical).
- B2: scripts/fable_suitediff.py --agent scripts/fable_loop224_agent.py --base 138i,
  one suite at a time (rt136, rt143, sessions152, bench, marks123) into
  224b/suitediff; then scripts/fable_rescore224.py --rows-dir 224b/suitediff
  --exclude diff (is_decline scoring of the 224 rows: 0 changes, 0 sanity
  mismatches); then scripts/fable_decline224_b2.py. Bar: 0 verdict moves, 0
  other moves (every differing leaf of every row must be the 138i glue replaced by
  one 224 sentence, incl. truncated reply echoes), 0 type mismatches (Q2 iff the
  row input is question-shaped: ends with "?" or the 151 predicate; teach turns
  S1), 0 missing rows, suitediff new WRONG / WRONG-WRITE / junk = 0; every moved
  row id listed in RESULTS.
- B3: scripts/fable_sleepsmoke206.py on loop224 (seed 1); scripts/fable_decline224_b3.py
  shows every mark equal to the sealed 138i report
  artifacts/fable-sleepsmoke206-20260922/s1-138i.json (installed, sleeps, episodes,
  probes right/wrong/abstain, overwrites, taught good/total/dupes, broken-chain
  verdict).
- B4: 0 new wrong writes anywhere: B1 writes 0; B2 suitediff new WRONG-WRITE 0 on
  every suite and 0 other moves (rt136 stored triples included in the row walk);
  B3 sleep_overwrote_taught 0.
- Every registered run < 25 min, OMP/MKL threads 1, one heavy suite at a time.

Verdict 224b = PASS iff B1 (as amended by the declared Q1 deviation), B2, B3, B4 pass.

## Pilot-driven decisions (before this seal)
- Imperative requests "Describe Veyla Orne." / "Explain what Tovin does." are not
  routed to the ears' question branch and the 151 predicate does not fire, so the
  pipeline-based rule serves S1 there. No keyword rule added (brief: type from what
  the pipeline did, not keywords). Both listed under pilot_limitations in the case
  file and replaced by the next pre-checked Q2 candidates (Q2-35, Q2-36).
- 7 other candidates did not get the glue on 138i (listed as dropped_precheck).
- fable_rescore224.py (sealed 224a) must be run with --exclude diff on a suitediff
  folder (its rt136 fragment otherwise picks rt136-diff.json first); usage only,
  no code change.
- Known risk: other experiments today saw intermittent single-row reply flakes in
  bench / rt143 with no agent change (218, 220, 226). Any such row fails B2 as
  sealed here; it will be reported, not excused.
