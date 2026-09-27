# TEST-ONLY: Ask panel 243 (blind panel for builders 245-251)

**TEST-ONLY. Builders 245-251 must not open, print or tune on any file in this folder before
their own seal.** It is scored once, after sealing, by each builder's scorer.

Written 2026-09-22 by an independent panel writer. Sources read: the director's schema brief,
OPUS-RULES, and artifacts/claude-diag243-20260922/RESULTS.md plus the code files it cites
(the relation cue tables in fable_bench92/bench73 and the verb table in fable_fix167_verb.py).
No builder file, other panel, grades file or examples file was opened.

## Schema (restated exactly from the director's brief)

Files: `panel.jsonl` (124 lines), `base228.jsonl` (124 lines, same ids, same order), `README.md`,
`SEAL.sha256.txt`.

`panel.jsonl`, exactly 10 fields per line:
`id` ("q243-001" ... "q243-124", family blocks in the order below), `family`, `setup` (list of
teach turns), `question` (ends with "?"), `twin_question` (string, or null for direction,
control and untaught), `gold` ("A; B" means every part must appear; null for direction and
untaught), `expect`, `stated_facts` (list of [subject, relation, value], copied from what the
base stored after the setup), `note`, `allowed_mentions` ([] for most; always [] for direction
and untaught).

`base228.jsonl`, exactly 8 fields per line:
`id`, `base_setup_replies`, `stored_after_setup`, `base_reply`, `stored_after_question`,
`twin_reply` (null when twin_question is null), `base_right`, `twin_right` (null when
twin_question is null).

| family | ids | count | expect | twin |
|---|---|---|---|---|
| compose | q243-001..016 | 16 | ANSWER | possessive form ("Who is X's spouse?" / "What is X's country of citizenship?" / "Who is X's employer?") |
| no_apos | q243-017..032 | 16 | ANSWER | same text with the apostrophe |
| whats | q243-033..044 | 12 | ANSWER | "what is / who is / where is" |
| first_person | q243-045..056 | 12 | ANSWER | "What/Who is my <relation>?" |
| verb_subject | q243-057..068 | 12 | ANSWER | possessive form, same name casing |
| my_relation | q243-069..084 | 16 | ANSWER | the person's name in place of "my <relation>" (name in allowed_mentions) |
| direction | q243-085..094 | 10 | ABSTAIN | null |
| combo | q243-095..102 | 8 | ANSWER | the fully normalised form |
| control | q243-103..114 | 12 | UNCHANGED | null |
| untaught | q243-115..124 | 10 | ABSTAIN | null |

Scoring rules (identical across 245-251, from the brief): ANSWER right = every gold part in the
reply (case-insensitive) and the reply does not start with "I don't know" / "I do not know".
Wrong value = a stated_facts value that is neither gold nor in allowed_mentions (ABSTAIN: any
stated value), matched case-insensitively as whole words. Question write = stored triples after
the question differ from those after the setup. Control = reply byte-identical to base228
`base_reply`. Schema mismatch on load -> SCHEMA-MISMATCH, exit 3, VOID.

`base_right` here follows the brief: ANSWER/UNCHANGED = every gold part appears in base_reply
(case-insensitive); ABSTAIN = no stated_facts value appears in base_reply (whole-word,
case-insensitive). `twin_right` = every gold part appears in twin_reply.

## How the base rows were made

Base agent: scripts/claude_loop228_agent.py (`Loop228Daemon`, 228 guard installed) with
artifacts/claude-determinism228-20260922/loop228-config.json. One fresh work dir per dialog;
each twin was asked in its own separate fresh dialog after the same setup. The whole candidate
pool (161 candidates, 282 dialogs) ran twice; the 276 dialogs common to both runs gave
byte-identical replies (the base is deterministic here). Wall time about 8 s per full run.
Generator, runner and raw logs stay in the writer's scratchpad, not in the repo.

Names and values are coined fictional words, filtered against /usr/share/dict/words, against
every relation cue substring in the bench92/bench73 cue tables, and against names ending in "s".

## Results on the base (all acceptance rules met)

| family | base_right true / false | twin_right true / false |
|---|---|---|
| compose | 0 / 16 | 16 / 0 |
| no_apos | 0 / 16 | 16 / 0 |
| whats | 0 / 12 | 12 / 0 |
| first_person | 0 / 12 | 12 / 0 |
| verb_subject | 0 / 12 | 12 / 0 |
| my_relation | 0 / 16 | 16 / 0 |
| direction | 4 / 6 | n/a |
| combo | 0 / 8 | 8 / 0 |
| control | 12 / 0 | n/a |
| untaught | 10 / 0 | n/a |

- Every stated_facts triple is in stored_after_setup (stated_facts are copied from it), and every
  setup turn was saved ("Saved: ..." reply, one triple per turn).
- stored_after_question == stored_after_setup on all 124 items.
- Direction leaks on the base: **6 of 10** (q243-085 employ, 086 create, 087 found, 088 written,
  089 produce, 090 "Whose child is X?"). The base declines teach/coach/manage/treat (091-094).
  Kept as they are, as the brief says.

Variety (questions whose wording matches a row of 243's grid table, names replaced by X):
compose 3/16, no_apos 5/16, whats 2/12, first_person 4/12, verb_subject 5/12, my_relation 0/16.
So at least half of each cause family uses a wording or relation not in the grid.

## Replacements

Candidates were tried in a fixed order; any that failed its rule was skipped and the next
candidate took its place.

| candidate | family | question | why replaced |
|---|---|---|---|
| c43 | whats | "Whos X's spouse?" | base already right (base_right true, twin true): cause not proved |
| c51 | whats | "whats X's employer?" | base already right: cause not proved |
| c65 | first_person | "What country am I a citizen of?" | teach "My country of citizenship is V." not saved |
| c79 | verb_subject | "Where was <lowercase> born?" | base already right |
| c80 | verb_subject | "Where was <Two Word> born?" | base already right |
| c85 | verb_subject | "where was <two word> born?" | base already right |
| c101 | my_relation | "Where does my coach work?" | teach "My coach is N." not saved |

Three extra verb_subject candidates were added after the first run to fill the slots freed by
the "born" items; one was used (q243-068, "where does <x> work?"). Surplus candidates that passed
but were not needed are not in the panel.

## Base bugs found

- **Untaught leaks: none.** 0 of 14 untaught candidates leaked a stored value.
- **Direction leaks (by design, kept):** 7 of 12 direction candidates leaked, 6 are in the panel
  (the seventh, "What did X develop?" with X's developer stored, was surplus). Cause: the
  composer's relation cues are substrings ("employ" in "employer", "creat", "found", "written",
  "produc", "child"), so an inverse verb reads as the stored relation.
- Other wrong-type replies seen (not leaks, all counted as base_right false where they occur):
  "What's my pet/doctor/sister/school?" -> "You never told me your name, so I do not know it."
  (read as a name question); "What's my sister's city?" / "What's my friend's pet?" /
  "What's my boss's employer?" -> "I don't know anyone called my <relation>."; "What is
  <Two Word>s city?" -> "I have no opinions." (q243-027); "Where was I born?" -> name reply.
- Teach gaps seen: "My country of citizenship is V.", "My place of birth is V." and
  "My coach is N." are not saved by the base (so those candidates could not be used).
- Not bugs, but noted: "Whos X's spouse?" and "whats X's employer?" are answered right by the
  base, and "Where was X born?" works for lowercase and two-word names, so C2 and B are not
  universal.

## Seal

From the repo root: `shasum -a 256 artifacts/claude-askpanel243-20260922/panel.jsonl artifacts/claude-askpanel243-20260922/base228.jsonl > artifacts/claude-askpanel243-20260922/SEAL.sha256.txt`. README.md is not sealed.

## Deviations

- The base_right check for ABSTAIN uses whole-word, case-insensitive matching (the scoring
  rule's wording); for ANSWER it uses plain case-insensitive substring, as the brief defines
  base_right. No item's verdict depends on the difference.
- compose twins follow the brief ("possessive form"), so for forms like "To whom is X married?"
  the twin differs by more than one word.
- A few coined names happen to look like real surnames or words in other languages (e.g.
  "Hamar", "Dorna"); none is in the system dictionary.
