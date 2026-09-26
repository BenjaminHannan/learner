# Month-end: what was taken from the evaluator's reply (Ben, 02:11 UTC 2026-09-26), and what is queued

Sections 3 (with Fix sleep), 6 and 10. Every claim was checked against the code and results first. No registration
was touched. Ben's overnight goal comes first; nothing below runs before 11:00 UTC. Each queued item is one change,
with marks fixed here and sealed again with its test data before any run.

## Taken now (into the 0.2c freeze, report only)
PASSMARKS-02c.md addendum ~03:20 UTC: a frozen manifest, three labels per part ("fixed in code", "passed its own
test", "passed in the joined assistant"), and resources (total parameters from file headers via
scripts/claude_params02c.py, resident bytes, sampling, ms per turn).

## Checked claims
- dl-2 "first-try solves 3 to 17/18 per 100": right (VERIFY.md, greedy solves night 7: base 3, S 17 and 18).
- "Trim repairs can't explain 191 -> 29 on GSM8K": right, and never claimed. F2 keeps a final answer only on the
  route's answers; 0.2c's GSM8K reading (bm-391 H5/H6) is what measures the gap.
- 383 is a refusal trigger, not a selector: right. scripts/claude_e2e383.py runs the whole old pipeline first and acts
  only when the reply is the abstain text, so a confident wrong or partial inner answer is never replaced.
  about_user383 keeps a question when it has my/mine/our, a recall phrase ("did I", "again"), a tag question or a
  notebook name. It does not use a bare "I" rule, so "I have seven apples and give away four" is routed. But it has
  both holes the reply describes: "My sister has 7 apples ..." is kept (the "my" rule), and "Where do I work?" is
  routed to the plain 1B (no rule fires; only the G3 name check stands in the way).
- "Crash-safe writes remain open": out of date. Store v3 (in 0.2c) keeps a torn last line aside, fsyncs each write,
  and answers from heard lines only. Still open: one durable log as the only source of truth (below).
- "Dates: latest message wins": partly. Memory answers show each recalled line with its stated date and let the 1B
  judge; nothing ranks by recency. The notebook's own corrections do overwrite. No rule separates message time,
  event time, corrections and conflicts (below).
- Section 3 "flags alone don't show the right model serves the new weights": agreed, and 0.2c already checks
  behaviour, not only flags: TEST and chat_solved are measured through the agent's own shared 1B before and after the
  nights, and X's panels run with the saved adapter reloaded.

## Queued
### sel-02d: answer-source selection instead of the refusal trigger (sec 6)
- One change: before the old pipeline runs, a selector labels the turn: self-contained (solve from the premises
  given), needs history (retrieve), mixed (retrieve the personal premises, then reason), or missing/conflicting
  (say the gap or ask one question). Components report a status (answered, partial, missing evidence, confirmation
  pending) instead of the loop reading refusal wording. A learned selector is preferred; its design is fixed at
  registration. F1-F3 (delivered history, final-answer tail, dates across restarts) stay as they are.
- Test: 300 fresh requests written blind and sealed before any run: 100 self-contained/general, 100 needing history,
  100 mixed or ambiguous, including confident wrong inner answers, statement-plus-question turns, "my" in
  self-contained problems and "Where do I work?"-style asks. Blind judges; arms 0.2c (or the last accepted build) and
  T.
- Marks: general +15 or more of 100 over the wrapped build; general within 3 of T; at most 1 more unsupported personal
  answer than the wrapped build across the history and mixed groups; wrong notebook writes reported separately.
- Proved wrong if the gain comes from answering history questions without support, or if self-contained problems
  with personal wording are still blocked.

### log-02d: the memory index built from the durable turn log (sec 10; with the Director)
- One change: the ep-382 store becomes an index over the notebook's turn log (turnlog323) with stable event ids,
  idempotent indexing and a committed position, instead of a second file of its own.
- CPU acceptance test (fault injection): stop indexing at every write boundary, reopen, replay; repeat after a
  correction and after a restart with dated messages.
- Marks: every committed message searchable exactly once in every case; 0 duplicate ids; every partial tail
  recovered; 0 stale answers after a completed correction (constructed cases, at least 40).
- Proved wrong by any lost committed message, duplicate, unrecoverable tail or stale answer.

### date-02d: dates beyond "what was said last" (sec 10)
- One change: each heard line carries message time and, when stated, event time; a correction marks the line it
  replaces; two current claims that disagree are kept as a conflict.
- Test: a fresh blind bank of dated conversations with historical statements after current ones ("In 2019 I lived
  in Oslo" after "I live in Lima"), corrections and real conflicts.
- Marks: current-fact asks right at least +10 points over the store without it; 0 historical statements taken as
  current in at least 40 constructed cases; conflicts answered with both sides or one question in at least 80%.
- Proved wrong if current-fact accuracy does not rise or historical lines still override current ones.

### Sleep packaging (sec 3), split with Fix sleep
- Fix sleep owns the packaged night: candidate adapter tied to the exact base revision, trained in a separate
  process on a snapshot, no write access to the live notebook, candidate saved -> evaluated -> activated atomically
  -> restart -> activation checked by behaviour (same build with the candidate on and off).
- Month-end owns the joined acceptance test: interrupt before saving, during saving, before activation and right
  after activation; every restart must load a complete accepted version, and rejected or interrupted candidates must
  leave user history and notebook facts unchanged. Any partial activation, lost committed event, or failure to
  return to the previous accepted version rejects the packaging.
- Until retention is fixed (dl-2 lost 26 of 200 by night 7), nights are not promoted automatically; 0.2c runs three.
