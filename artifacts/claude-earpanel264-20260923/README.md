# Ear panel 264 (blind reader panel), 2026-09-23 — TEST-ONLY

Fresh test panel for the "reader": one chat turn in, the facts it states
(TEACH) or the question it asks (ASK) out. Written blind. The author read
only the exp 264 spec, OPUS-RULES.txt, and the schema and judgement-call
sections of the earpanel235 README. No code, relation tables, training data,
design notes, results, other briefs, other panels, or builder folders were
read. All names are invented. No turn uses first-person-plural owners or
subjects (per the spec, those are tested in a separate experiment; R7 is
dropped). Category-level report only: this file quotes no item.

Files:
- `panel.jsonl`: 150 items, one JSON object per line.
- `make_panel.py`: generator. Holds the items by hand, writes the file
  deterministically, and runs the self-checks. Run from the repo root with
  `uv run --offline --no-project --python 3.12 --with torch --with numpy python -B artifacts/claude-earpanel264-20260923/make_panel.py`.
  It checks family counts, no duplicate turns, word-for-word subjects/values,
  every R quota, lowercase/typo and no-"?" counts, and schema exactness
  including chain_aliases.
- `SEAL.sha256.txt`: SHA-256 of `panel.jsonl` and `make_panel.py`.

## Families

| family | items | clear: false |
|---|---|---|
| plain_teach | 25 | 0 |
| varied_teach | 30 | 0 |
| full_names | 15 | 0 |
| questions | 25 | 1 |
| chain_questions | 15 | 0 |
| no_save | 25 | 12 |
| corrections | 15 | 0 |
| **total** | **150** | **13** |

## Item format

- Each line is exactly `{id, family, turn, gold, clear, notes}`.
  ids are `e264-001` … `e264-150` in family-block order.
- TEACH frame: exactly `{act, subject, relation, relation_aliases, value}`.
  `subject`/`value` are the exact words from the turn in the same case
  (lowercase spans kept in lowercase turns). `me` stands for the speaker.
- ASK frame: exactly `{act, subject, relation, chain, relation_aliases,
  chain_aliases}`. `chain` is null for one hop. For two hops `chain` is
  [first relation, second relation], `relation` is the second one,
  `subject` is the start person, and `chain_aliases` is [aliases of hop 1,
  aliases of hop 2] with the second list equal to `relation_aliases`.
- `relation_aliases` come from one fixed alias list per relation in the
  generator. Pet aliases include every species word the turns use.
- `notes` holds comma-separated risk tags (R-numbers, `lower`, `typo`,
  `noq`, `correction`).

## Risk quotas (counts of tagged items)

| quota | count (minimum) |
|---|---|
| R1 pronoun reference across clauses (varied_teach + full_names) | 10 (8) |
| R2 statement-questions in no_save, gold [] | 9 (8) |
| R2 of those with no question mark | 5 (5) |
| R2 question-word statements with TEACH gold (varied_teach) | 3 (3) |
| R3 verb decides relation (teach/coach -> workplace; study -> school) | 6 (6) |
| R4 compound family relations | 8 (6) |
| R5 everyday relations beyond the core list | 11 (8) |
| R6 two-hop questions with a relative first hop (chain_questions) | 7 (5) |
| R8 plans/goals/wishes in varied_teach (plan excluded from gold) | 4 (3) |
| R8 whole-turn plans in no_save, gold [] | 4 (3) |
| R9 pretend/hypothetical turns in no_save, gold [] | 6 (5) |
| R10 plural relatives naming two people, a frame per person | 4 (4) |
| R11 appositive relatives, relative frame plus the other fact | 10 (6) |
| R12 pronoun after "A's R is B" referring to B | 4 (4) |
| R13 typo next to a name (teach items) | 8 (8) |
| R14 all-lowercase names (teach items) | 6 (6) |
| R15 name particles (teach items) | 6 (6) |
| R16 wrong-relation traps (teach items) | 8 (8) |
| R17 stale values named outside "not X" (corrections) | 6 (6) |
| lowercase or typo chat turns in all | 25 (15) |
| lowercase or no-"?" items in questions + chain_questions | 6 (5) |

## Judgement calls

- **Teaching/coaching vs studying**: teaching or coaching at a School,
  College or Club gives `workplace`; studying at one gives `school`.
- **"Work with" vs "work for"**: companions named with `with`/`alongside`
  get no frame unless a relation to the speaker is stated; the stated
  employer/workplace is the only work frame.
- **In-law by description**: a brother's wife stated as such is
  `sister_in_law`, never `wife` or `sister`.
- **"Near" is not "in"**: living near a place stores nothing for that
  place; only the separately stated work place is gold.
- **"Used to" is not "now"**: past workplaces are never in gold.
- **Plural relatives**: one frame per person for the kin relation, plus
  each person's other stated fact.
- **Statement-shaped questions** (tag questions, `so`-checks, with or
  without a question mark): gold is `[]`, clear false, since an ASK reading
  is also defensible.
- **Plans and wishes**: a whole-turn plan is `[]`; a plan clause next to a
  current-fact clause keeps only the fact.
- **Pretend/hypothetical framing** (`imagine`, `suppose`, `let's say`,
  `what if`, `pretend`, `say that`): gold is `[]`.
- **Corrections**: gold holds only the new value, whether the old value is
  negated with `not` or restated as a stale value (`moved from A to B`,
  `used to be A, now B`).
- **Job vs workplace questions**: asking what someone does for work is
  gold `job`, clear false, since `workplace` is also a fair reading.
- **Hearsay, past residence, and news** (`apparently …`, `used to live
  in …`, `did you hear … is closing?`): gold is `[]`, clear false.
- **Opinions without an owner** ("X is the best boss ever") and bare
  second-person remarks store nothing.
