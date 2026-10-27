# 251 — verb direction (Opus builder)

## The bug
After "X's employer is Y.", the question "Who does X employ?" asks who X employs
(people whose employer is X). Base228 answered "X's employer is Y." — the
opposite direction, a wrong value.

## Where it comes from (traced on base228)
- scripts/fable_loop138_agent.py:122 sends every "?" turn to
  scripts/fable_bench92_english_arm.py:221 `compose_n_hop` first.
- compose_n_hop finds the one mentioned entity (X), walks X's single outgoing
  relation (employer) and checks that the relation is "mentioned" by substring
  cues. REL_CUES92["employer"] (line 100) has the cues "employ" and "works for",
  which are substrings of "Who does X employ?", "Who is employed by X?",
  "Who works for X?", "Whose employer is X?", "Who is X the employer of?",
  "Who is X's employee(s)?", "Who is employed at X?". So all of these read X's
  forward employer. Confirmed by calling compose_n_hop directly.
- Only employer leaked on base (teach/manage/coach/... decline, because their
  cue lists have no verb stem). With 2+ relations on X, compose_n_hop stops
  and no leak happens (still an honest decline).
- For other relations the 153 reverse reader already answers "Whose R is X?" /
  "Who is X the R of?" correctly ("I don't know anyone whose teacher is X.").

## The fix (scripts/claude_fix251_direction.py, one mixin, question side only)
Direction251Mixin sits outermost on the inner ears (instance class swap in
scripts/claude_loop251_agent.py; no file edited).
1. Verb forms, claimed fully: "Who/Whom does|do|did X <verb>?",
   "Who/Whom is|are|was|were <verb-ed> by X?", "What does X own?" for
   employ/hire→employer, teach→teacher, coach→coach, manage→manager,
   supervise→supervisor, treat→doctor, represent→lawyer, mentor→mentor,
   own→owner. Optional "hi/hello/hey," and "please".
   - X known (nb.resolve OK or X equals a stored subject/value): answer from
     facts whose VALUE is X: "X employs Y and Z. (worked out backwards)";
     never stored (clarify action). None: "I don't know who X employs."
   - If X is itself a stored value and there is no answer, the decline says
     "I don't know who they employ." so a decline never repeats a stored value.
   - X not known: unchanged stack runs; any "ask" it returns is replaced by
     the decline; any other reply is kept byte-identical.
2. Extra direction wordings (works for/at, employed at, reports to, works
   under, studies under, learns from, whose R is X, who is X the R of, X's
   employee/student/patient/client/mentee/...): the unchanged stack runs first
   and is kept byte-identical unless it returned an "ask" (the leak); only
   then the reply becomes the inverse fact lines + label, or a decline.
X's own forward value is never read by the mixin.

## Must not change
"Who employs X?", "Who is X's employer?", "Who does X work for?", "Whose
employer is Y?" (153, already right) and other possessives are untouched (dev
must-not-change 10/10 byte-identical; frozen suites 0 moves).

## Known limits
- "Who works for Y?" where facts say "X's employer is Y" still gets the base
  decline (no inverse answer): the extra wordings only step in on a leak.
- "Who do I employ?" falls through to the base decline.
- Verbs outside the ten are not covered.
