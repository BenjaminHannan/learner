# 224: one decline sentence per turn type (design notes, Opus, 2026-09-22)

Results: `artifacts/fable-decline224-20260922/RESULTS.md`. 224a PASS. 224b FAIL as sealed: one intermittent bench row served Q1.

## Problem

When loop138i does not understand a turn, it answers with two stuck-together declines:

- S105.HONEST_DECLINE: "I do not know that from what you taught me. I have no record of it, so I will not guess."
- L138.DECLINE_SUFFIX: "I didn't understand that, I don't know — could you say it another way?"

The first half claims a lookup happened; the second half says the turn was not understood.

This is built in exactly one place, `Loop138gAgentLoop.turn` (scripts/fable_loop138g_agent.py:337-348). It fires when:

1. the notebook path missed (no records, or only "didn't understand" clarifies), and
2. the frozen self router (route127) returned DECLINE.

## Where the glue actually fires (measured)

- Every stored glue row has ears stage "none" or "loop138-nonexplicit". No ask was ever produced.
- An ask with no value always returns an answer record ("I don't know X's father." / "I don't know anyone called X."). So on 138i, the "notebook has no value" case (Q1) is already answered by one sentence and never reaches the glue.
- In practice the glue covers two cases:
  - questions the ears could not parse (Q2);
  - statements the ears could not save (S1).

## Design

The scorer side (224a) is `scripts/fable_decline224.py` `is_decline`. It takes the union of the frozen marker lists plus the census extras.

- Replies starting with "Saved:" or "Forgotten:" are never declines.
- Self-router CANNOT answers are not declines.
- `scripts/fable_rescore224.py` re-scores stored rows with each suite's own check swapped for `is_decline`, by monkeypatch or a verbatim copy. No frozen file is edited.

The agent side (224b) is `scripts/fable_loop224_agent.py`. It builds loop138i unchanged, then adds instance-level taps:

- outer `ears.hear`, to collect the actions;
- inner `_hear_question`, to see whether the question branch ran;
- one post-turn swap, only when the reply is exactly the glue and last_routed is DECLINE.

The type rule uses what the pipeline did (no keywords of its own):

- an ask action → Q1;
- the question branch ran, or the text ends with "?", or the exp-151 predicate fires → Q2;
- otherwise → S1.

The self logs are updated so the self answerer reports what was actually said. Nothing new is written.

## Lessons / next steps

1. **The Q1 branch is unsafe as written.** In one intermittent registered run, bench132-4hop-031 lost its 138b rewrite (stage "none"). The captured actions for that turn included an ask, but the reply was still the glue, so Q1 ("you haven't told me") was served for facts that *had* been taught. Two possible fixes:
   - Require Q1 only when the turn's records include a MISSING_FACT answer. The glue can't coexist with that, so Q1 would be dead code.
   - Or simply map any ask-plus-glue turn to Q2.

   The cause of the flake is not established: 0 of 11 reruns on 138i, 0 of 11 on loop224. Diagnosis needs a per-turn action log written to disk by the daemon.
2. **Imperative requests** ("Describe X.", "Explain …") go down the statement path and get S1 ("…save it"). The honest fix is in the ears (route requests to the question branch), not a keyword list in the mouth.
3. **fable_rescore224.py** should gain a suitediff-folder mode. For now it needs `--exclude diff`.
4. **A re-run of 224b** with fix (1) needs a new experiment number and a fresh seal. It must also be ready for the known one-row bench flakes; one option is a paired same-process base comparison, as in exp 220.
