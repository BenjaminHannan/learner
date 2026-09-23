# Exp 249 RESULTS: first-person twins (cause D of diagnosis 243)

**Result: registered FAIL, on mark M1b only.** The sealed scorer counts 6 wrong values on the
124 panel items. All 6 are in the direction family (q243-085..090, exp 251's cause). The
replies are byte-identical to base228.jsonl's base_reply: 249 did not change them, and base228
already leaks them. M1e lists these leaks and does not count them, but M1b as I registered it
("wrong values on all 124 items = 0") has no such exception, so under the sealed marks the
verdict is FAIL. I did not re-score or re-interpret it. Every other mark passed: first_person
11/12, 0 question writes, control 12/12 identical, 0 regressions, dev 60/60, suites GATE clean
with 0 moves, sleep smoke matches 138i, and the median time cost was -0.05 ms.

## Marks (registered runs, each once, after seal; seal checks OK before the panel)
| mark | bar | result | pass |
|---|---|---|---|
| M1a first_person right | >= 11/12 | 11/12 | PASS |
| M1b wrong values, 124 items | 0 | 6 (all direction; all base228 leaks, unchanged) | **FAIL** |
| M1c question writes | 0 | 0 | PASS |
| M1d control byte-identical | 12/12 | 12/12 | PASS |
| M1e base_right -> wrong/decline | 0 | 0 | PASS |
| M1e untaught no stored value | 10/10 | 10/10 | PASS |
| M1e new direction leaks vs base228 | 0 | 0 (6 old leaks listed: 085-090) | PASS |
| M1f combo (no bar) | - | 0/8 right, 0 wrong values | - |
| M2 dev first_person / must_not_change / traps / writes | all | 39/39, 11/11, 10/10, 0 | PASS |
| M3 suites (rt136, rt143, sessions152, bench) | 0 bad, moves = predicted (none) | GATE clean, 0 moves in all four | PASS |
| M4 sleep smoke | 138i marks | sleeps 1, installed 1, probes 5/5, wrong 0, taught 50/50, ow 0, 89.1 s | PASS |
| M5 median added ms per panel question | <= +5 | -0.05 | PASS |

Panel family right counts for loop249 (base228 is the same except the 13 moves below): compose 0/16,
no_apos 0/16, whats 0/12, first_person 11/12, verb_subject 0/12, my_relation 2/16,
direction 4/10, combo 0/8, control 12/12, untaught 10/10. My own base228 arm reproduced
base228.jsonl base_reply on 124/124 items.

## Every move
Panel (13 moves, all from a decline or "You never told me your name" to the right answer):
- first_person q243-045 "Where do I live?", 046 "What's my city?", 047 "Who am I married to?",
  048 "Where do I work?", 049 "Who do I work for?", 050 "Who's my boss?", 051 "What's my pet?",
  052 "Who's my doctor?", 053 "Where do I go to school?", 054 "where do i live?",
  055 "Who's my sister?": all now answer "Your <relation> is <value>." with the gold value.
- my_relation q243-073 "What's my sister's city?", q243-081 "What's my friend's pet?": decline
  -> right. These two were NOT predicted (I predicted possible "What's my" moves only in combo/
  whats). Both are the "What's my <chain>?" rule of 249. No wrong value, no write.
Dev: 39 first_person items moved from decline / "I have no opinions." / "Was that a question?" /
"You never told me your name..." to right; 11 must_not_change and 10 traps did not move
(m2-dev-score.txt lists each one).
Suites: none.

## Misses
- q243-056 "Who employs me?" -> glued decline. The verb "employs" with "me" as the object is
  not in MAP249 (I mapped "Where do I work?" / "Who do I work for?" / "What company do I work
  for?", but not "Who employs me?").
- M1b's 6 items (q243-085..090, direction): e.g. "Who does Brylto employ?" -> "Brylto's
  employer is Gedund." This is the base's direction leak (exp 251's cause). The replies are
  byte-identical to base228, and 249 never claims these turns because they contain no I/me/my.

## Deviations
- The M1b bar I registered has no carve-out for leaks that base228 already had, but the common
  brief's M1e has one. Under the sealed marks this is a FAIL. With the M1e carve-out applied to
  M1b, M1b would count 0 new wrong values, but that is not the registered mark.
- Render249Mixin (loop level) is part of the one change. It makes 249-claimed replies say
  "Your city is X." instead of the base backstop's lowercase "your city is X.". It touches only
  turns that the 249 ears claimed.
- The design choice to check "stored for USER" first replaces the brief's literal wording "try
  the rewrite, then fall back". A turn has side effects, so it cannot safely run twice. When the
  target is not stored, the original turn runs unchanged, which gives the same outcome.
- Two unpredicted panel moves in my_relation (both gains, listed above).
- No driver or scorer change after the seal. There were no re-runs.

## Per-item panel table (loop249)
| id | family | base_right | right (249) | same as base228 | wrong values |
|---|---|---|---|---|---|
| q243-001 | compose | False | False | True | - |
| q243-002 | compose | False | False | True | - |
| q243-003 | compose | False | False | True | - |
| q243-004 | compose | False | False | True | - |
| q243-005 | compose | False | False | True | - |
| q243-006 | compose | False | False | True | - |
| q243-007 | compose | False | False | True | - |
| q243-008 | compose | False | False | True | - |
| q243-009 | compose | False | False | True | - |
| q243-010 | compose | False | False | True | - |
| q243-011 | compose | False | False | True | - |
| q243-012 | compose | False | False | True | - |
| q243-013 | compose | False | False | True | - |
| q243-014 | compose | False | False | True | - |
| q243-015 | compose | False | False | True | - |
| q243-016 | compose | False | False | True | - |
| q243-017 | no_apos | False | False | True | - |
| q243-018 | no_apos | False | False | True | - |
| q243-019 | no_apos | False | False | True | - |
| q243-020 | no_apos | False | False | True | - |
| q243-021 | no_apos | False | False | True | - |
| q243-022 | no_apos | False | False | True | - |
| q243-023 | no_apos | False | False | True | - |
| q243-024 | no_apos | False | False | True | - |
| q243-025 | no_apos | False | False | True | - |
| q243-026 | no_apos | False | False | True | - |
| q243-027 | no_apos | False | False | True | - |
| q243-028 | no_apos | False | False | True | - |
| q243-029 | no_apos | False | False | True | - |
| q243-030 | no_apos | False | False | True | - |
| q243-031 | no_apos | False | False | True | - |
| q243-032 | no_apos | False | False | True | - |
| q243-033 | whats | False | False | True | - |
| q243-034 | whats | False | False | True | - |
| q243-035 | whats | False | False | True | - |
| q243-036 | whats | False | False | True | - |
| q243-037 | whats | False | False | True | - |
| q243-038 | whats | False | False | True | - |
| q243-039 | whats | False | False | True | - |
| q243-040 | whats | False | False | True | - |
| q243-041 | whats | False | False | True | - |
| q243-042 | whats | False | False | True | - |
| q243-043 | whats | False | False | True | - |
| q243-044 | whats | False | False | True | - |
| q243-045 | first_person | False | True | False | - |
| q243-046 | first_person | False | True | False | - |
| q243-047 | first_person | False | True | False | - |
| q243-048 | first_person | False | True | False | - |
| q243-049 | first_person | False | True | False | - |
| q243-050 | first_person | False | True | False | - |
| q243-051 | first_person | False | True | False | - |
| q243-052 | first_person | False | True | False | - |
| q243-053 | first_person | False | True | False | - |
| q243-054 | first_person | False | True | False | - |
| q243-055 | first_person | False | True | False | - |
| q243-056 | first_person | False | False | True | - |
| q243-057 | verb_subject | False | False | True | - |
| q243-058 | verb_subject | False | False | True | - |
| q243-059 | verb_subject | False | False | True | - |
| q243-060 | verb_subject | False | False | True | - |
| q243-061 | verb_subject | False | False | True | - |
| q243-062 | verb_subject | False | False | True | - |
| q243-063 | verb_subject | False | False | True | - |
| q243-064 | verb_subject | False | False | True | - |
| q243-065 | verb_subject | False | False | True | - |
| q243-066 | verb_subject | False | False | True | - |
| q243-067 | verb_subject | False | False | True | - |
| q243-068 | verb_subject | False | False | True | - |
| q243-069 | my_relation | False | False | True | - |
| q243-070 | my_relation | False | False | True | - |
| q243-071 | my_relation | False | False | True | - |
| q243-072 | my_relation | False | False | True | - |
| q243-073 | my_relation | False | True | False | - |
| q243-074 | my_relation | False | False | True | - |
| q243-075 | my_relation | False | False | True | - |
| q243-076 | my_relation | False | False | True | - |
| q243-077 | my_relation | False | False | True | - |
| q243-078 | my_relation | False | False | True | - |
| q243-079 | my_relation | False | False | True | - |
| q243-080 | my_relation | False | False | True | - |
| q243-081 | my_relation | False | True | False | - |
| q243-082 | my_relation | False | False | True | - |
| q243-083 | my_relation | False | False | True | - |
| q243-084 | my_relation | False | False | True | - |
| q243-085 | direction | False | False | True | Gedund |
| q243-086 | direction | False | False | True | Dendund |
| q243-087 | direction | False | False | True | Brathin |
| q243-088 | direction | False | False | True | Fyra |
| q243-089 | direction | False | False | True | Kraembek |
| q243-090 | direction | False | False | True | Foxan |
| q243-091 | direction | True | True | True | - |
| q243-092 | direction | True | True | True | - |
| q243-093 | direction | True | True | True | - |
| q243-094 | direction | True | True | True | - |
| q243-095 | combo | False | False | True | - |
| q243-096 | combo | False | False | True | - |
| q243-097 | combo | False | False | True | - |
| q243-098 | combo | False | False | True | - |
| q243-099 | combo | False | False | True | - |
| q243-100 | combo | False | False | True | - |
| q243-101 | combo | False | False | True | - |
| q243-102 | combo | False | False | True | - |
| q243-103 | control | True | True | True | - |
| q243-104 | control | True | True | True | - |
| q243-105 | control | True | True | True | - |
| q243-106 | control | True | True | True | - |
| q243-107 | control | True | True | True | - |
| q243-108 | control | True | True | True | - |
| q243-109 | control | True | True | True | - |
| q243-110 | control | True | True | True | - |
| q243-111 | control | True | True | True | - |
| q243-112 | control | True | True | True | - |
| q243-113 | control | True | True | True | - |
| q243-114 | control | True | True | True | - |
| q243-115 | untaught | True | True | True | - |
| q243-116 | untaught | True | True | True | - |
| q243-117 | untaught | True | True | True | - |
| q243-118 | untaught | True | True | True | - |
| q243-119 | untaught | True | True | True | - |
| q243-120 | untaught | True | True | True | - |
| q243-121 | untaught | True | True | True | - |
| q243-122 | untaught | True | True | True | - |
| q243-123 | untaught | True | True | True | - |
| q243-124 | untaught | True | True | True | - |

(Replies and timings per item: panel-scored.jsonl and m1-panel-rows.jsonl in this folder.)

## What it means
When you tell Premonition a fact about yourself ("My city is Mundan.") and later ask in a normal
way ("Where do I live?", "Who am I married to?", "Where do I work?", "What's my pet?"), it now
answers from its notebook instead of saying "I don't know." It only does this when it really
has that fact saved, and it never saves anything while answering. It gets no slower, and nothing
else it said on the tests changed, apart from two "What's my sister's city?"-style questions
that also started working.

## What it doesn't mean
It does not understand every way of asking about yourself: "Who employs me?" still fails,
because only a fixed list of wordings is covered. The run is a registered FAIL because of the
6 wrong answers in the "direction" group. The old model already gave those same answers, and
this change does not fix them (that is exp 251's job). It also does not show that the fix
works together with the other fixes (245-251). Combined questions ("whats my sisters city?")
still fail here, and they are scored only at merge time.
