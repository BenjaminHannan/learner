# Exp 238 bug classes

Claude (Opus 5.5) graded every sentence here. The rules are in scripts/claude_grammar238_grade.py, so the counts can be reproduced. No outside grader checked them.

Count columns:
- **scope-conv**: occurrences in real conversation replies from the in-scope folders (138i/138j/228 and the 13 pieces). This is the primary weight.
- **all-conv**: real conversation replies from every folder dated today.
- **tmpl**: unique templates.
- **rend**: tricky renders from the real agent runs.

Bench/MQuAKE rows are excluded from the conversation weights. "G" means the class makes a reply ungrammatical. "N" means it is grammatical but unnatural. "M" means a meaning error.

| class | kind | scope-conv | all-conv | tmpl | rend | example -> fix | where |
|---|---|---:|---:|---:|---:|---|---|
| RELATION_NOT_VERB | N | 11167 | 450808 | 191 | 47 | "Saved: Mira's city is Lisbon." -> "Got it: Mira lives in Lisbon." / "Priya Dunmore's employer is Juniper Lane Books." -> "Priya Dunmore works at Juniper Lane Books." | fable_notebook_contract.py:349 (write text), :77 (SAVED); fable_agent_loop.py:155-172 (FakeMouth) |
| STACKED_POSSESSIVE | N | 3669 | 22470 | 515 | 5 | "marta's father's city is dallas." -> "Marta's father lives in Dallas." / "Harborline's founded by's spouse's city is ..." -> "The founder of Harborline's spouse lives in ..." (better still: "Ada Wren founded Harborline; her spouse lives in ...") | fable_agent_loop.py:155-172 |
| DECLINE_SPLICE + ROBOTIC_DECLINE | G+N | 1902 | 15210 | 7 | 1 | "I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way?" -> "Sorry, I didn't understand that. Could you say it another way?" (also given to "How are you?", "Tell me a joke.", "Who is your boss?") | fable_self105.py:64 + fable_loop138_agent.py:92 |
| BAD_RELATION_PHRASE | G | 1350 | 6516 | 411 | 0 | "Saved: Harborline's founded by is Ada Wren." -> "Got it: Ada Wren founded Harborline." / "director of Harborlight Choir's officeholder is ..." -> "The director of Harborlight Choir is ..." | relation display in fable_agent_loop.py:155-172 and fable_notebook_contract.py:349; bench relation names |
| LOWERCASE_START (+ LOWERCASE_NAME_ECHO) | G | 673 (+2) | 3090 (+93) | 157 (+1) | 3 (+2) | "tess's city is Omaha." -> "Tess lives in Omaha." / "your birthday is June 4." -> "Your birthday is June 4." / "Saved: max's sister is lena." -> "Saved: Max's sister is Lena." | fable_fix221_tableask.py:397; stored names are echoed in the case the user typed (contract :349) |
| DOUBLE_DASH | N | 216 | 1608 | 3 | 0 | "... I can't do 'not' -- could you say it without that part?" -> "... I can't handle 'not' yet. Could you say it without that part?" | fable_screen148_mixin.py:51,53; fable_loop102_agent.py:72 |
| PLURAL_NAME_POSSESSIVE | G | 208 | 794 | 43 | 1 | "Juniper Lane Books's owner is Silas Wendt." -> "Silas Wendt owns Juniper Lane Books." / "Netherlands's capital is Alwernia." -> "The Netherlands' capital is Alwernia." | claude_loop229_agent.py:445; fable_notebook_contract.py:349 |
| QUESTION_NO_QMARK | G | 160 | 291 | 1 | 1 | 'Could you say it another way, like "Kim's boss is Lee."' -> 'Could you say it another way? For example: "Kim's boss is Lee."' | fable_loop188_agent.py:86; the 138j decline line has the same shape |
| TEACH_ME_LIKE | N | 124 | 606 | 1 | 1 | 'Hi! Teach me like "Tom's boss is Ann."' -> 'Hi! You can teach me facts like "Tom's boss is Ann." and ask "Who is Tom's boss?"' | fable_fix156b_smalltalk.py:53 |
| OFF_TOPIC_NO_OPINIONS | M | 72 | 298 | 1 | 1 | "Who lives in Oslo?" -> "I have no opinions." should be a lookup, or "Nobody you've told me about lives in Oslo." | opinion screen in the 138i chain (seen on the 228 base) |
| COLON_LABEL | N | 62 | 3118 | 25 | 3 | "Forgotten: Mira's city." -> "OK, I've forgotten where Mira lives." | fable_notebook_contract.py:78-86 |
| VALUE_LIST_AGREEMENT | G | 55 | 217 | 5 | 4 | "Wren's friend is Odo, Ivy and Ash." -> "Wren's friends are Odo, Ivy and Ash." / "Your sister is Ula and Eve." -> "Your sisters are Ula and Eve." | fable_fix221_tableask.py:379; claude_loop231_agent.py:297 (also joins without "and"); fable_fix154d_yesno.py:161 |
| NO_ARTICLE_JOB | N | 22 | 1172 | 11 | 2 | "Saved: Jon's job is baker." -> "Got it: Jon is a baker." | contract :349 |
| DOUBLE_TERMINAL_PUNCT | G | 15 | 1303 | 150 | 0 | "... Washington, D.C.." -> "... Washington, D.C." / 'like "Mira's city is Lisbon.".' -> 'like "Mira's city is Lisbon."' | contract :349 (value already ends in "."); fable_agent_loop.py:126,139; fable_decline224.py:70; fix140:208 |
| NUMBER_AGREEMENT | G | 7 | 155 | 6 | 4 | "I have 1 facts about 1 people." -> "I have 1 fact about 1 person." / "0 web row" -> "no web rows" | fable_self99.py:421,425,447,455,506,508,510,513,515,585; fable_fix168_ground.py:164 |
| MISSING_ARTICLE_THE | G | 6 | 2417 | 58 | 0 | "Saved: United Kingdom's capital is London." -> "Saved: The United Kingdom's capital is London." / "That write is not allowed from web." -> "... from the web." | contract :349, :85 |
| ANYONE_CALLED_THING | N/M | 5 | 21 | 0 | 2 | "I don't know anyone called Norlandia." -> "I don't know anything about Norlandia yet." | fable_fix221_tableask.py:411 |
| SPELLING | G | 2 | 235 | 25 | 0 | "origianl broadcaster" -> "original broadcaster" | fable_bench92_english_arm.py:65 (bench data) |
| WRONG_REFERENT_AGE | M | 2 | 7 | 1 | 1 | "How old r u?" -> "You never taught me their age..." should be "I don't have an age. I'm a program." It is also the reply to "When is my birthday?" | fable_fix168_ground.py:66 |
| RAW_RELATION | G | 0 | 15885 | 67 | 0 | "association football's country_of_origin is England." -> "Association football comes from England." | older agents only; none in scope |
| PRETEND_PAREN + SAY_FRAGMENT | G+N | 0 | 14 / 4 | 3 / 2 | 2 / 1 | "Say my name." -> "my name. (I'm treating that as pretend, so I won't save it.)" should be "Your name is Ren." | fable_fix137d_frame.py:71,74 |
| WORKED_BACKWARDS_TAG | N | 0 | 8 | 2 | 2 | "Brindle Mill's owner is Sato Venn. (worked out backwards)" -> drop the tag: "Sato Venn owns Brindle Mill." | fable_fix221_tableask.py:69 |
| EMPTY_LIST | G | 0 | 2 | 1 | 1 | "I know 0 people: ." -> "I don't know anyone yet." | fable_self99.py:417-425 |
| BARE_NAME_LIST | N | 0 | 0 | 0 | 2 | "I know 2 people: Max, Silas." -> "I know two people: Max and Silas." | fable_self99.py:417-425 (it also counted the company Juniper Lane Books as a person) |
| PLACEHOLDER_LEAK | G | 0 | 0 | 0 | 1 | "... forget it in turn ?." -> "... forget it earlier." | fable_self99.py:469-470 |
| GARBLED_READBACK | G | 0 | 0 | 0 | 1 | "I read it as in 1987's founder is Juniper Lane Books was, but ..." -> "I didn't save that. Could you tell me who founded Juniper Lane Books, or the year it was founded?" | claude_loop229_agent.py:216-243 |

## Meaning slips that are not grammar (from the probes; not in the grammar rate)

- **"works at" becomes "works for" (231).** Teaching "Deni works at Fennick." and then asking "Where does Orla's coach work?" gives "Deni works for Fennick." The cause is claude_loop231_agent.py:303-307, which uses the relation's first teach template, not the verb the user taught.
- **Name check (219, 230).** "Is my name Bo?" gets "Yes. Your name is Ren." 230b fixes this.
- **Name check (228 base).** "Is my name Ren?" and "What do you know about me?" get "You never told me your name" after the name was taught.
- **Forget, then ask (228).** "Forget Silas's sister Eve." followed by "Who is Silas's sister?" gives "You told me something new about Silas's sister that I could not store...".
- **Forget with "my" (228).** "Forget my sister Eve." gets "I don't know anyone called my sister."
- **Age question (228 base).** "How old is Ada Pell?" is declined even though her age was taught. 221, 221c and 231 answer it.

## Code-scan risks never seen in a run (hand-graded templates)

- fable_notebook_contract.py:80 "I know more than one {name}: {choices}." has the same risk of an empty list or a list without "and".
- The shouting "I could NOT ..." appears in fable_agent_loop.py:376 and the contract.
- Hard-coded demo names (Mira, Paris, Oslo) appear in fable_fix168_ground.py:54,183, fable_self99.py:442 and fable_fix219:85 "All ... turns". They can show up in replies about people the user never mentioned.
- fable_loop138j_agent.py:397 "I don't have another {key} for {subject}." can show a raw key or a plural ("another friends").
- fable_fix171:136 "What is Juniper Lane Books's owner's name?" has the plural possessive plus a stacked possessive.
- fable_fix154d_yesno.py:161 "I have {shown} as {owner}." has an agreement problem ("I have Eve, Ula and Ines as Silas's sister.").
