# Fluent, conversational replies: gap and plan. Talking line, 2026-09-23 18:10 UTC

Ben (17:55 UTC): "I only want to talk to it when it's able to speak fluent english in a conversational tone".
Evidence was checked in code and in the 04:18 chat-demo transcripts (artifacts/claude-chatweak-20260923, 90 turns, dev material).

## Where replies come from today (base 292)
- 292's mouth is still the stand-in template mouth. Config `mouth`: "Loop138bMouth ... replacement: real mouth
  fable_mouth53". Answers read like "<owner> is <value>." or "Ana's city is Quito.", and relation labels are
  used in place of verbs.
- 241b's better mouth (a rule-based rewriter: 99%+ grammar, and a blind judge preferred it 97 times to 9) is
  installed only on the old base 228. The 280p talking layers are on 260; they reach 292 via 292t (queued).
- Chat demo, 90 turns:
  - 36 are fixed clarify lines. One "I don't know that shape yet..." line appears 17 times, and "I didn't
    understand that question..." appears 14 times.
  - 17 are fixed small-talk or self lines.
  - 37 are built from notebook records. Saves read "Saved: ...".
  - 0 replies ask a follow-up or refer back to an earlier turn.

## The gap, in order of size
1. **Understanding, not wording.** 40% of demo replies are "I didn't understand". No mouth can make those
   conversational; the ear (the understanding step) has to understand more. That is the ear and reasoning
   lines' work. This line will measure it and hand them the counts.
2. **Stiff fixed lines.** One wording per situation, repeated word for word, plus the "I can: a; b; c" list and
   "Saved:". This is fixable on CPU in days.
3. **Sentence wording.** 241b already fixes most of this; it just is not on 292.
4. **Conversation habits.** No acknowledgements, variety, follow-ups or references back. These need a dialog
   state and a reply planner, not just a better sentence writer.
5. **A real generative mouth** (the own talker101, or a small pretrained model that only paraphrases a checked
   record). This is the long-run answer to "fluent". It needs an exact read-back check first, because a yes/no
   checker let 63 of 65 wrong readings through. It belongs to the own-model line, and a new model download needs
   Ben's yes.

## Plan (each step is one sealed experiment; marks fixed before each build)
- **F0: measurement first.** A sealed conversation benchmark: fresh multi-turn everyday dialogs from a blind
  writer, fictional names. Baseline taken on 292.
  - Mechanical marks: unfaithful lines, notebook-event changes, share of the single most common reply, and the
    share of turns that are clarify lines.
  - Graded marks: a dialog-level blind pairwise judge, and a rubric grader (warmth, variety, acknowledgement,
    follow-up). Every grader must first catch at least 36 of 40 planted flaws.
- **F1: 241b's rewriter on 292t.** This also re-registers 241b's speed mark under a quiet-machine rule.
- **F2: conversational fixed text.** Several true wordings per situation (clarify, greeting, thanks, save
  acknowledgement, ability), chosen deterministically, under a sealed style guide. Each wording gets a truth
  check.
- **F3: a small reply planner.** Acknowledge the teach and never repeat the same line twice in a row, with
  nothing new claimed.
- **F4: generative mouth,** coordinated with the own-model line through the coordinator.
Pass mark for "conversational" (proposed, to be fixed in F0's note):
- the blind judge prefers the new arm on at least 70% of non-tie dialogs vs 292, with at most 10% losses;
- 0 unfaithful lines;
- no single reply on more than 10% of turns;
- grammar at least 99%.
Wrong if: 60% or fewer wins, or any unfaithful line.

## F0 baseline on 292 (director-verified, 18:38 UTC)
convbench-f0 (40 dialogs, 286 user turns, seal 2/2 OK). My recount from run/base292.jsonl:
- **197/286 replies (69%) are clarify or not-understood lines.** By kind: small talk 57/68, teach 48/84,
  ask 53/84, other 34/40, correct 5/10.
- The single most common reply appears on 122/286 turns (43%). There are only 77 distinct replies.
- Only 20 of 84 teach turns saved anything.
- Ask turns: 6 right, 77 abstain, 1 wrong. The wrong one is a stale value after a correction the model did not
  understand, not an invented fact.
So on everyday conversation, 292 mostly does not understand. That is the ear's job, and the numbers go to the
ear and reasoning lines through the coordinator. The talking-line steps below still matter for the turns it
does understand, but they cannot make it conversational alone.

## F1: 241b's rewriter on 292t (registered 18:38 UTC)
The one change: install 241b's sealed reply rewriter (scripts/claude_mouth241b_*.py, used exactly as in
scripts/claude_loop241b_agent.py) as the outermost reply layer on 292t. Piece files are imported unchanged.
Marks (fixed now):
- M1: grammar of every changed line is at least 99%, from two blind graders, each valid only if it catches at
  least 36 of 40 planted errors.
- M2: 0 unfaithful lines (each changed line parses back to the same frame, by 241b's brake). 0 notebook-event or
  store changes vs 292t on the suites, the verifier probes, joinpanel292t (regression only) and convbench-f0.
- M3: frozen suites (fable_suitediff218 --only rt136,rt143,sessions152,bench) vs 292t's rows: reply-only moves,
  every one a 241b rewrite, GATE identical.
- M4: a blind pairwise judge on the changed lines from convbench-f0, 292t vs F1, sides randomised. Pass: at
  least 70% of non-ties won, and at most 10% lost.
- M5: the suite wall-clock cost is at most +5%, medians of 3 alternated runs each, with load1 below 40 before
  every run, waiting up to 6 hours. If it never gets quiet, M5 is VOID, not FAIL, and it is re-run.
Wrong if: any unfaithful line, any store change, or 60% or fewer judge wins.
