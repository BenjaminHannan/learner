# Exp 238: grammar sweep of Premonition's replies (measurement only)

**Result: grammar is below the 99% target, and natural-sounding replies are far below it.** In real conversation replies from the in-scope agents, **87.4%** are grammatical (26,509 of 30,315 occurrences) and **44.1%** sound natural (13,363 of 30,315). Most of the grammar misses come from four fixable templates. One of them, the stacked "I do not know that ... I didn't understand that, I don't know —" decline, accounts for half of all grammar misses by itself.

**Who graded:** I (Claude, Opus 5.5) graded every sentence myself, using copy-editor judgment written down as rules in scripts/claude_grammar238_grade.py. No person or second model checked the grades. Meaning errors (a wrong answer or the wrong referent) are flagged separately and do not lower the grammar rate. No model code was changed.

## Rates

| measure | grammatical | natural | meaning errors |
|---|---|---|---|
| (a) real replies, weighted by frequency: in-scope folders, conversation rows only **(primary)** | 26,509 / 30,315 = **87.4%** | 13,363 / 30,315 = **44.1%** | 74 |
| (a2) real replies: every folder dated today, conversation rows only | 732,092 / 775,909 = 94.4% | 265,277 / 775,909 = 34.2% | 305 |
| (a3) real replies: in-scope folders, including bench rows | 160,577 / 251,552 = 63.8% | 122,906 / 251,552 = 48.9% | 74 |
| (a4) real replies: every row | 1,836,424 / 2,788,153 = 65.9% | 1,169,791 / 2,788,153 = 42.0% | 306 |
| (b) unique templates (fillers masked; 2,122 templates) | 1,331 / 2,122 = **62.7%** | 937 / 2,122 = **44.2%** | 2 |
| (c) tricky renders (real agent runs, 16 dialogs, 142 unique replies) | 125 / 142 = **88.0%** | 73 / 142 = **51.4%** | 2 |

How to read the variants:
- "Conversation rows" leave out files whose path contains bench or mquake. Those rows are "Saved: <Wikidata fact>" lines, repeated tens of thousands of times, and they swamp everything else.
- Rate (b) is lower than (a) because the rare templates (bench relation names, older agents) are wrong more often than the common ones.
- (a2) is higher than (a) because older agents (before 138i) used shorter decline lines.

What the rate would become with only the top classes fixed (primary weighting; this is arithmetic on the same grades, not a test):
- fix the decline splice: 93.7%
- plus relation phrases: 96.7%
- plus capitalisation: 98.5%
- plus possessive, question mark and double punctuation: 99.8%

## The known examples: all five confirmed

| brief example | status | where seen |
|---|---|---|
| "I know 0 people: ." | CONFIRMED | 228 base and 138j probe; 2 real rows. Also "1 facts about 1 people", "0 web row", "turn ?.". Cause: fable_self99.py:417-425 and nearby lines |
| "Juniper Lane Books's owner is Silas Wendt." | CONFIRMED | 229 probe; claude_loop229_agent.py:445 |
| "works for" answer to a "works at" fact | CONFIRMED in 231 two-hop answers ("Deni works for Fennick." after "Deni works at Fennick."). Not seen in 229 single-hop answers ("Priya Dunmore's employer is ...") | claude_loop231_agent.py:303-307 |
| "(I'm treating that as pretend, so I won't save it.)" after "Say my name." | CONFIRMED on every agent probed. The full reply is the fragment "my name. (I'm treating that as pretend, so I won't save it.)" | fable_fix137d_frame.py:71,74 |
| "You never taught me their age" for "How old r u?" | CONFIRMED on the 228 base. The same line also answers "When is my birthday?" | fable_fix168_ground.py:66 |

## Bug classes (primary weighting = in-scope conversation occurrences)

The full table, with two examples and file:line for every class, is in bugclasses.md.

| class | kind | in-scope conv | all conv | templates | renders |
|---|---|---:|---:|---:|---:|
| RELATION_NOT_VERB ("Mira's city is Lisbon") | natural | 11,167 | 450,808 | 191 | 47 |
| STACKED_POSSESSIVE ("marta's father's city") | natural | 3,669 | 22,470 | 515 | 5 |
| DECLINE_SPLICE / ROBOTIC_DECLINE | grammar + natural | 1,902 | 15,210 | 7 | 1 |
| BAD_RELATION_PHRASE ("founded by is", "director of X's officeholder") | grammar | 1,350 | 6,516 | 411 | 0 |
| LOWERCASE_START / NAME_ECHO | grammar | 675 | 3,183 | 158 | 5 |
| DOUBLE_DASH ("--") | natural | 216 | 1,608 | 3 | 0 |
| PLURAL_NAME_POSSESSIVE ("Books's") | grammar | 208 | 794 | 43 | 1 |
| QUESTION_NO_QMARK | grammar | 160 | 291 | 1 | 1 |
| TEACH_ME_LIKE | natural | 124 | 606 | 1 | 1 |
| OFF_TOPIC_NO_OPINIONS | meaning | 72 | 298 | 1 | 1 |
| COLON_LABEL ("Forgotten: X.") | natural | 62 | 3,118 | 25 | 3 |
| VALUE_LIST_AGREEMENT ("friend is Odo, Ivy and Ash") | grammar | 55 | 217 | 5 | 4 |
| NO_ARTICLE_JOB ("job is baker") | natural | 22 | 1,172 | 11 | 2 |
| DOUBLE_TERMINAL_PUNCT ("D.C..") | grammar | 15 | 1,303 | 150 | 0 |
| NUMBER_AGREEMENT ("1 facts") | grammar | 7 | 155 | 6 | 4 |
| MISSING_ARTICLE_THE ("United Kingdom's") | grammar | 6 | 2,417 | 58 | 0 |
| ANYONE_CALLED_THING | natural | 5 | 21 | 0 | 2 |
| SPELLING ("origianl", bench data) | grammar | 2 | 235 | 25 | 0 |
| WRONG_REFERENT_AGE | meaning | 2 | 7 | 1 | 1 |
| RAW_RELATION ("country_of_origin") | grammar | 0 | 15,885 | 67 | 0 |
| PRETEND_PAREN / SAY_FRAGMENT | grammar | 0 | 14 / 4 | 3 / 2 | 2 / 1 |
| WORKED_BACKWARDS_TAG | natural | 0 | 8 | 2 | 2 |
| EMPTY_LIST ("I know 0 people: .") | grammar | 0 | 2 | 1 | 1 |
| BARE_NAME_LIST / PLACEHOLDER_LEAK / GARBLED_READBACK | mixed | 0 | 0 | 0 | 2 / 1 / 1 |

## Top 10 fixes, ranked by how often users would see them

1. **Replace the stacked decline with one short sentence** (fable_self105.py:64 + fable_loop138_agent.py:92). Use "Sorry, I didn't understand that. Could you say it another way?" This fixes 1,902 in-scope occurrences, half of all grammar misses. It also stops small talk and "Who is your boss?" from getting a three-sentence refusal.
2. **Say facts with verbs, not "X's rel is Y", and keep the user's verb.** Examples: "Mira lives in Lisbon", "Deni works at Fennick", "Sefa speaks Veltish". The write text is at contract:349 and :77, the answers at FakeMouth fable_agent_loop.py:155-172, and the 231 chain at :303-307, which also fixes "works for". This is the largest naturalness gain (11,167).
3. **Break up possessive chains into clauses**: "Marta's father, Tom, lives in Dallas." (3,669)
4. **Show relation labels only as noun phrases.** "founded by" becomes "founder", "director of X's officeholder" becomes "the director of X", "languages spoken written or signed" becomes "language", and "origianl" is corrected. (1,350)
5. **Capitalise the sentence start and proper names when echoing them.** "your" becomes "Your" at fable_fix221_tableask.py:397, and stored lower-case names are shown capitalised. (675)
6. **Use "—" or a full stop instead of "--"** (fable_screen148_mixin.py:51,53; fable_loop102_agent.py:72), and **add the missing "?"** (fable_loop188_agent.py:86 and the 138j decline line). (216 + 160)
7. **Possessives and "the" for names that are plural or take "the".** "Juniper Lane Books'", or better "Silas Wendt owns Juniper Lane Books"; "the Netherlands'"; "the United Kingdom". This covers claude_loop229_agent.py:445 and contract:349. (208 + 6)
8. **Make list answers agree.** "Wren's friends are Odo, Ivy and Ash." Join the last two items with "and" at fable_fix221_tableask.py:379, claude_loop231_agent.py:297 and fable_fix154d_yesno.py:161. (55)
9. **Fix the count sentences in fable_self99.py.** Handle 0, 1 and many ("1 fact", "1 person", "no web rows"), use "I don't know anyone yet." for an empty list, never show "turn ?", and leave companies out of "people". (7 in scope; it shows on every "What do you know?")
10. **Fix the small scripted replies.**
    - "Say my name." should say "Your name is Ren." (fable_fix137d_frame.py:71,74).
    - "How old r u?" should answer about itself; "When is my birthday?" should not get the "their age" line (fable_fix168_ground.py:66).
    - "Who lives in Oslo?" should do a lookup instead of "I have no opinions.".
    - Drop "(worked out backwards)" (fable_fix221_tableask.py:69).
    - Reword "Teach me like" (fable_fix156b_smalltalk.py:53).
    - "anyone called Norlandia" should be "anything about Norlandia" (fable_fix221_tableask.py:411).

## What was done

1. **Harvest** (scripts/claude_grammar238_harvest.py). I walked every artifacts/*-20260922 folder except those with "panel" in the name, fable-naturalpanel208, claude-tablepanel221 and reading94/94b, and skipped panel*/p1panel* files. None of those were opened. Replies came from the fields reply, teach_replies, replies, agent_reply and response, and from outbox/*.txt. Result: 1,348,622 files, 2,788,212 reply occurrences and 41,759 unique strings (harvest.jsonl).
2. **Code scan** (scripts/claude_grammar238_codescan.py and claude_grammar238_coderender.py). I followed the imports of 17 agents through 161 modules. That gave 788 literal strings, which I filtered to 177 user-facing reply templates and rendered with fillers (codetemplates.jsonl, coderenders.jsonl).
3. **Real-agent tricky renders.** I ran the real agents in fresh scratch workdirs:
   - probes/probe238.json (12 dialogs) on 228, 138j, 219, 230, 230b, 227, 227b, 227c, 223, 224c, 226, 233, 234, 221, 221c, 229 and 231
   - probes/probe238b.json (4 dialogs) on 228, 138j, 229, 221c and 231

   The fillers covered names ending in s/x/z, multi-word names, lower-case names, vowel-initial values, 1 or 3 values, counts of 0/1/2, an empty notebook, dates, and I/you subjects. Outputs are probes/out*.txt; renders.jsonl holds 142 unique replies.
4. **Grading** (scripts/claude_grammar238_grade.py). I grouped strings into templates (templates.jsonl) and graded each string or template. Each got grammatical yes/no, natural yes/no, meaning-error flags, classes and a one-line correction (grades.jsonl, summary238.json). Strings from talker, ears, smol, cardfold and demo126 folders (29 strings, 59 occurrences) were dropped as out of scope.

## Deviations

- **Self-grading.** The grades are my own judgment, written as rules. A rule-based grader can miss problems no rule covers, and some corrections in grades.jsonl are mechanical (for example, a few "correct" fields only fix capitalisation). bugclasses.md gives hand-written fixes.
- **Pieces run separately.** The 13 pieces were probed one at a time, each on its own agent file, not as a merged agent. The 228 base run had the source guard. The piece agents were run as they are, and some of them predate the guard. No merged 138i+all-pieces agent exists to probe.
- **Code-scan renders used only qualitatively.** The code-scan renders fill slots by guessing their type and produce nonsense like "My Silas is Silas.". They are not counted in rate (c); rate (c) uses only real agent output. The "never seen in a run" check on code templates is approximate.
- **Weighting.** Frequency weighting counts rows that the test suites repeat, not real users. The in-scope conversation weighting is the closest stand-in available.
- **Time.** The run took about 25 minutes of wall-clock time. One heavy job ran at a time; the harvest was IO-bound at about 5 minutes.

## What it means

- The assistant does not yet meet "99% grammar." About one real reply in eight has a grammar mistake a person would notice.
- The mistakes are concentrated. Fixing four reply templates (the decline, relation labels, capitalisation, and the question mark / possessive / double-dot group) would, on the same replies, take grammar to about 99.8%.
- Sounding natural is the bigger gap. Fewer than half of replies sound like a person, mainly because facts are said as "Mira's city is Lisbon" instead of "Mira lives in Lisbon".
- All five problems named in the brief are real and reproducible.

## What it doesn't mean

- It does not measure whether the answers are correct. Meaning errors were noted but not searched for systematically.
- The "about 99.8% after fixes" figure is a projection from these grades, not a test of fixed code. Fixes can introduce new mistakes.
- The rates come from test-suite traffic, not real users. Real users would ask different things in different proportions.
- It was not checked by a second grader, so borderline calls (for example, whether "Forgotten: Mira's city." sounds natural) are one opinion.
- It says nothing about the talker, the ears or the reading panels, which were out of scope or off-limits.
