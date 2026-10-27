# Exp 249 PASSMARKS (cause D of diagnosis 243: first-person twins)

Base: scripts/claude_loop228_agent.py + artifacts/claude-determinism228-20260922/loop228-config.json.
Agent: scripts/claude_loop249_agent.py + artifacts/claude-firstperson249-20260922/loop249-config.json
(228 guard installed at import; SrcGuardMixin228 first in Loop249Daemon bases).
The one change: scripts/claude_fix249_firstperson.py (FirstPerson249Mixin outermost on the ears,
plus Render249Mixin, which gives 249-claimed replies the same Me166 "Your ..." rendering; it
touches no other turn).

## Rule
Only turns ending in "?" that contain I/me/my (whole word) and fully match a MAP249 pattern
(optional lead "hi/hello/hey/ok/okay/so" and/or "please", optional tail ", please/now/currently/
these days/again") are rewritten, and only when the target is STORED for USER (active taught
fact). Several candidates: exactly one must be stored, else no rewrite (0 or 2+ -> original turn
unchanged). The base ears must then return exactly one read-only Me166 ask on USER with the
same relations; otherwise the original turn is heard. Statements never reach the code.

## Mapping table (MAP249; relation keys are the ones "My <relation> is <Value>." stores for USER)
| question form | candidates (exactly one stored) | rewritten to |
|---|---|---|
| where do I (currently) live | city, town | What is my <rel>? |
| what/which city do I live in | city | What is my city? |
| what/which town do I live in | town | What is my town? |
| what/which country do I live in | country | What is my country? |
| who am I married to / who is married to me | spouse, wife, husband | Who is my <rel>? |
| where do I work | employer, workplace, company | Who is my <rel>? |
| who do I work for / what/which company do I work for/at | employer, company | Who is my <rel>? |
| who do I report to | boss | Who is my boss? |
| what do I do for (a) living/work / what job/work do I do / what do I work as | job, occupation, profession | What is my <rel>? |
| where was I born / what city/town/place was I born in | birthplace | What is my birthplace? |
| where did I grow up | hometown | What is my hometown? |
| where am I from | hometown, country | What is my <rel>? |
| what/which country am I from | country | What is my country? |
| how old am I | age | What is my age? |
| what pet do I have | pet | What is my pet? |
| what/which school do I go to/attend / where do I go to school | school | What is my school? |
| what language(s) do I speak | language | What is my language? |
| What's / Who's / Where's my <chain>? | every link resolves from USER | What/Who/Where is my <chain>? |

## Marks (registered; each run once)
- M1a: panel family first_person right >= 90 % (>= 11/12). Right = every gold part in reply
  (case-insensitive) and reply does not start with "I don't know"/"I do not know".
- M1b: wrong values on all 124 items = 0 (whole-word, case-insensitive; gold and
  allowed_mentions exempt; ABSTAIN items: any stated value).
- M1c: question writes on all 124 items = 0 (active triples after question != after setup).
- M1d: control 12/12 byte-identical to base228.jsonl base_reply.
- M1e: no item in another family (compose, no_apos, whats, verb_subject, my_relation, untaught,
  direction) with base_right true goes to wrong/decline or starts giving a value; untaught 10/10
  no stored value; direction: no NEW value leak vs base228.jsonl base_reply (old leaks listed).
- M1f: combo per item, no bar (wrong values count in M1b).
- M2: dev249.jsonl (39 first_person, 11 must_not_change, 10 traps): first_person all right with
  no wrong value; must_not_change byte-identical to the base228 arm run in the same session and
  no wrong value; traps give no stored value (setup values of either arm); 0 question writes.
- M3: fable_suitediff218 --base 138i --only rt136,rt143,sessions152,bench: 0 new WRONG /
  WRONG-WRITE / junk write / lost OK, GATE clean; moves equal the predicted list.
- M4: fable_sleepsmoke206: sleeps 1, installed, probes 5/5, wrong 0, taught 50/50, overwrote 0,
  under 300 s.
- M5: median over the 124 panel items of (loop249 question ms - base228 question ms), both arms
  run interleaved per item in one session by scripts/claude_firstperson249_run.py: <= +5 ms.
Verdict PASS only if every mark passes.

## Predicted moves
- M3: NONE in rt136, rt143, sessions152, bench (pilot: 0 moves in all four, GATE clean).
- M2: 39 first_person items move decline/other -> right; 11 must_not_change and 10 traps
  unchanged (pilot 60/60).
- M1: first_person items move from decline to right (predicted 11-12/12). No other family
  moves except possibly combo/whats items that are "What's my ..." with the apostrophe (they
  may move decline -> right; listed, not counted). Control 12/12 identical.

## Pilot (before seal)
Dev 60/60, 0 writes, median dev time diff -4.4 ms; suites 0 moves GATE clean; sleep smoke
sleeps 1 installed 5/5 wrong 0 taught 50/50 ow 0 84 s.
