# Decided inputs for the mode integration (Fable coordinator, 21 Sep 2026)

These are fixed by Ben. The reviewer connects to them; it does not reopen them.

## Final mode list
LISTENING, WORKING, CREATIVE, BORED, SLEEP. The agent is persistent and always in exactly one defined state.
"Always doing something" means always in a defined state; when the budget is spent the correct behaviour is to
rest and log it. The agent's home and compute is Ben's Windows PC with an RTX 5070 Ti (native Python, resumable).
No separate WAITING mode: a job blocked on Ben parks with a pending-question record, the agent drops to BORED,
and the question sits at the top of Ben's digest; the job resumes when he answers.

## LISTENING (rules; coordinator-written, accepted by Ben)
- Ben is teaching, correcting or asking. Pre-empts every other mode.
- The ONLY mode that writes `taught` rows.
- Says "saved" only after a validated durable write (acknowledgement is not transaction success).
- Ambiguous reference (two Miras, unclear "her") → ask, never guess or merge.
- Quotes, hypotheticals and reported speech are not assertions and write nothing as `taught`.
- Unanswerable questions return the executor's discrete status through a deterministic template.
- v1: supervised parser → structured event → deterministic executor → template reply. The learned talker waits
  until this works end to end (Ben's decision), then is trained against the same interface.

## SLEEP (agreed with Ben 18 Sep 2026; v1 narrowed per outside review #19)
- Trigger: consolidation pressure ("tiredness") from measurable quantities + a body clock; naps whenever needed.
- Sleep is a TRANSACTION: runs on a background copy with a snapshot; wake-up check (incl. told-ledger: every
  taught fact still retrievable); bad night → full rollback. A new job from Ben makes sleep finish or roll back.
- Order: NREM-like first (sort, dedupe, repair, flag conflicts, invalidate inferred rows whose dependencies
  changed, replay successful traces by replay-priority tag, rebuild indexes), then REM-like (recombine facts
  into "dreams" = candidate links/rules, kept only if the checker can verify them; labelled inferred).
- Alias/identity merges are PROPOSALS for Ben, never automatic.
- v1 is notebook-only: no weight changes. v2 (weights change only in sleep; knowledge slots; growing thought
  codebook with code births in sleep; upward distillation) only after a measured need. Target ~1:2
  sleep:awake compute; key baseline = the same compute spent awake.

## Drives and rules already agreed
Learning progress, gap curiosity (rewarded only on confirmation), replay-priority tag, effort, consolidation
pressure, hunger-like spending limit (gaining compute is never a reward). Assigned jobs are never abandoned;
"frustration" only for self-chosen practice; plateaus trigger a strategy switch. No novelty bonus, no
teacher-approval reward, no summed happiness score, no self-invented goals in v1. Thinking (BORED/CREATIVE) may
use the web; web text is data, lands in quarantine with source, quoted span and time, and is promoted only by
Ben or a written source policy. Inferences never overwrite taught facts.
