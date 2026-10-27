# gram-360 pass marks (grammar thread, registered 2026-09-25 before any run on bank G)

## Question
Most of 0.1's grammar misses come from the rule agent's fixed fill-in lines, which paste stored slots in raw
(VERIFY-336.md M7: graders split on lowercase names and slot text; VERIFY-338.md: template lines ~82% vs the
1B's ~97%). Does rendering those slots properly fix the fill-in lines without changing anything else?

## The one change
Arm P360 = 330c (scripts/claude_e2e330c.py, unchanged) + the gram-360 slot finisher
(scripts/claude_gram360.py via scripts/claude_e2e360.py:build_360). It rewrites only parts the rule agent
produced: relation keys without underscores, pronoun owners as possessives, lowercase names capitalised in name
slots (relation table v1 value kinds + the relation's head noun) or when English always capitalises the word
(Debian wamerican list), Python lists joined with "and" and "are", the catch-all relation "other" said as
"V goes with O", sentence-initial capitals, "0 web rows", "Could you ...?" requests ending in "?", and "a"/"an"
before a common-noun value of a thing relation (pet, car, other). No notebook access. Built and tuned on DEV only
(artifacts/claude-e2e331-dev-20260924 replies from the 330 / 330c / lis e2e DEV rehearsals).

## Test data
Bank G: artifacts/claude-gram360-bankG-20260925, 10 fresh lives written blind to spec 331 by a separate agent
that never saw any code (names E to J, unlike DEV's S to Z). Sealed (SEAL.sha256.txt) before the run.
Rental: arms P360 and P330c (control, report only), MiniCPM5-1B with enable_thinking=False, lis-301 reader,
GRAM360_LOG=<run>/gram360_parts.jsonl on the P360 arm.

## Grading
scripts/claude_gram360_check.py writes rule_raw (distinct rule-agent parts before rendering), rule_final (after)
and all_final (distinct whole P360 replies). Two blind Opus graders each grade one shuffled file holding the
union of the three sets plus 40 planted errors and 40 planted clean lines (336's generator,
artifacts/claude-e2e336-20260924/judges/judge_prep336.py, new seeds 3601 and 3602; scripts/claude_gram360_gradeprep.py).
Graders judge each line on its own with the question "Is this line grammatical, natural English with no simple
mistakes (spelling, capitalisation, punctuation, agreement, word order, missing or extra words)? Do not judge
whether the content is true or fits a conversation." They never see which set a line came from, and nothing tells
them what changed. A grader counts only if it flags >= 36/40 planted errors and keeps >= 36/40 planted clean
lines. Marks computed by scripts/claude_gram360_score.py.

## DEV basis for the bars (report only)
One strict blind grader on 247 DEV fill-in lines (planted 39/40 caught, 40/40 clean kept), with an earlier
version of the finisher (no "?" or article rules): raw 118/247 (47.8%), rendered 202/245 (82.4%). Of the 43 still
flagged: 13 "Could you ..." requests ending in "." and 7 missing articles (both then added), the rest the reader's
nonsense frames ("is your granddaughter this?"), which rendering cannot fix. DEV estimate with the final version:
about 90%.

## Marks (fixed now)
| Mark | What | Bar |
|---|---|---|
| P360.1 | rendered fill-in lines (rule_final) graded grammatical, each grader | >= 90% |
| P360.2 | gain over the same lines unrendered (rule_final % minus rule_raw %), each grader | >= +20 points |
| P360.3 | rendering changes no score: confirm flag, the harness's confirm answer, the 336 ask class (raw vs final reply); parts not from the rule agent changed | 0 and 0 |
| P360.4 | slot words lost by rendering (checker) | 0 |

Proved wrong: if either valid grader gives rule_final less than rule_raw + 5 points, slot rendering is not what
makes these lines ungrammatical, and the diagnosis is wrong.

Report only, no mark: all distinct P360 replies graded grammatical (the 336 M7 measure, bar 99% there); the
336 scorer's line for P360 and P330c; which fill-in lines are still flagged, by shape (counts only).
Expected after this change alone: the remaining misses are the reader's nonsense frames ("is your snack Uriah?")
and the 1B's own replies (~97% in 338), which are the next two changes, not this one.
