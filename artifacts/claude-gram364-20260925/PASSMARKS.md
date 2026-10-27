# gram-364 pass marks (grammar thread, registered 2026-09-25 before any run on bank H)

## Question
After gram-360 (VERIFY-360.md) the rule agent's fill-in lines are about 91% clean. On DEV, what is still flagged
is partly the reader's nonsense (not fixable by wording) and partly rendering misses. Does a second version of
the finisher fix the rendering misses without changing anything else?

## The one change
Arm P364 = 330c + the fill-in finisher v2 (scripts/claude_gram364.py via scripts/claude_e2e364.py:build_364) in
the place of gram-360's finisher. v2 is gram-360 plus six rendering changes, each for a DEV miss:
1. the catch-all relation "other": 'your note about O says "V"' / 'does your note about O say "V"?' instead of
   "V goes with O";
2. a value "you" turns the sentence round: "are you Saoirse's child?" instead of "is Saoirse's child you?";
3. a one-word value of an animal relation is a name ("is Uriah's hamster Sprout?"), unless it is a state word
   ("sick") or an -ing/-ed/-ly word ("limping");
4. an owner that is an animal noun is "the hamster's", not "Hamster's";
5. short acronyms inside a longer value in capitals ("ER nurse");
6. "a"/"an" before a thing value whose first word ends in -ed/-ing ("a bearded dragon"), and for "employer".
Unit tests: scripts/claude_gram364_test.py (45/45: gram-360's 16 cases, 2 of them intentionally changed, plus
15 new cases and 14 no-word-lost checks). Built on DEV only.

## DEV basis (report only)
234 distinct DEV fill-in lines (330a / 330c / lis e2e DEV rehearsals), rendered by gram-360, one strict blind
grader: 41 flagged, about 24 of them reader nonsense ("allergy is talking", "granddaughter is this"). v2 changes
21 of the 234 lines; a second fresh blind grader flags 4 of those 21 (the first grader flagged 19 of their
gram-360 versions): 2 reader nonsense turned round ("are you Uriah's snack?"), 1 reader nonsense elsewhere in the
line, 1 "your note about hamster" (then fixed as item 4).

## Test data
Bank H: artifacts/claude-gram364-bankH-20260925, 10 fresh lives (199 turns, 123 facts) written blind to spec 331
by a separate agent that never saw any finisher code (names A to D, unlike DEV's S to Z and bank G's E to J).
Five checks pass. Sealed (SEAL.sha256.txt, 4 files) before the run. Nobody in this thread has read its turns.

## Run (one arm, paired replay)
BensPC (Windows, through scripts/claude_winnl2_wrap.py as bm-390), MiniCPM5-1B 87179e5c with
enable_thinking=False, lis-301 reader, GRAM360_LOG=<run>/gram364_parts.jsonl:
  W scripts/claude_twinb_wrap.py scripts/claude_e2e336_run.py --bank <bank H> --arm claude_e2e364:build_364 \
      --name P364 --model READER --gen-model BASE --out <run>
scripts/claude_gram364_check.py re-renders every raw rule-agent part with gram-360's realise and the same seen
names (checked against the bank G run: 0 of 183 parts differ from what gram-360 rendered live), so gram-360 and
v2 are compared on exactly the same parts.

## Grading
scripts/claude_gram364_grade.py prep: two blind Opus graders, each one shuffled file with the union of rule_raw,
rule_final360, rule_final364 and all_final (a line in several sets is graded once) + 336's 40 planted errors + 40
planted clean lines (seeds 3641, 3642). Question: "Is this line grammatical, natural English with no simple
mistakes (spelling, capitalisation, punctuation, agreement, word order, missing or extra words)? Do not judge
whether the content is true or fits a conversation." (gram-360's wording.) A grader counts only with >= 36/40
planted errors caught and >= 36/40 clean kept.

## Marks (fixed now)
| Mark | What | Bar |
|---|---|---|
| P364.1 | v2 fill-in lines (rule_final364) graded grammatical, each grader | >= 94% |
| P364.2 | gain over gram-360 on the same parts (rule_final364 % minus rule_final360 %), each grader | >= +3 points |
| P364.3 | v2 changes no score: confirm flag, the harness's confirm answer, the 336 ask class (raw vs final reply); parts not from the rule agent changed | 0 and 0 |
| P364.4 | slot words lost by v2 rendering (checker) | 0 |

Proved wrong: if either valid grader gives rule_final364 less than rule_final360 + 1 point, these rendering misses
are not a real share of what graders flag on fresh lives.
Report only: all distinct P364 replies graded grammatical; the 336 scorer's line for P364; how many parts v2
renders differently from gram-360; which lines are still flagged, by shape (counts only).
