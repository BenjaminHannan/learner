# reasonpanel296 (sealed, test only)

A blind panel of 300 items for grading the learned reasoner. Each item gives a
notebook of facts about fictional people and one everyday-English question.
The answer must come from the notebook alone, or be "UNKNOWN" when the
notebook does not settle it. No model may be trained or tuned on these items.
The items were written fresh for this panel, independently of any training or
practice generator.

What is different from reasonpanel294: the notebooks look like a real, messy
personal notebook after weeks of chat. Sizes vary from 3 to 40 rows inside
every category; people appear in many rows and as both subject and value;
several people share the same relations; multi-valued facts (kids, pets,
languages, hobbies and so on) appear as distractors; numbers, multi-word
values and facts told in any order are common. The panel uses 89 distinct
relation names.

Files: `items.jsonl` (one item per line), this README, and `SEAL.sha256.txt`
(sha256 of `items.jsonl` and this README, computed from the repo root).
Validator: `python scripts/claude_reasonpanel296_check.py` (re-derives every
gold answer and support set; must print PASS).

## Item format

| key | meaning |
|---|---|
| `id` | `rp296-001` .. `rp296-300`; categories are shuffled so that no more than 2 consecutive items share a category |
| `category` | one of the categories below |
| `notebook` | list of rows (below) |
| `question` | everyday English question |
| `gold.answer` | exact short string; `"yes"`/`"no"`; an integer as a string for counting; `"UNKNOWN"` for missing_fact |
| `gold.support` | fids of the rows that justify the answer (`[]` for UNKNOWN) |
| `frame` | structured form of the question (below) |

### Notebook rows

| key | meaning |
|---|---|
| `fid` | `f1`, `f2`, ... in list order |
| `subject` | a person |
| `relation` | snake_case relation name; the row reads "subject's relation is value" |
| `value` | string (numbers such as birth_year, height_cm, monthly_rent are digit strings) |
| `when` | integer order stamp, unique within the notebook; bigger = told later. List order and `when` order often differ |
| `year` | integer; only on history rows, only in before_after items |

Rules the gold follows:
- Single-valued relations have one row per subject + relation, except the one
  correction in each newest_correction item.
- Multi-valued relations (`kid`, `pet`, `speaks`, `plays_instrument`,
  `plays_sport`, `hobby`, `allergy`, `houseplant`, `visited_country`,
  `takes_class`, `volunteers_at`, `subscribes_to`) may hold several values for
  one person. They are never on a deciding path except in counting.
- Relations that describe both people (`roommate`, `cousin`, `sibling`,
  `best_friend`, `neighbor`, `spouse`, `bandmate`, `coworker`, `classmate`,
  `friend`) appear only as distractors: never in a frame, and never touching a
  person the question depends on.
- History relations (`lived_in`, `worked_at`, `had_job`, `drove`,
  `played_for`, `studied_at`, `rented_from`) always carry `year`. The asked
  person has 2 to 4 such rows with distinct years. "Before X" means the row
  with the next lower year than the row whose value is X; "after X" means the
  next higher year.
- When two rows give the same subject + relation without a `year`, the row
  with the larger `when` holds (newest_correction only).
- Chain questions have exactly one current value at every hop.
- Counting counts the distinct values of the matching rows; the notebook is
  taken as complete for counts. A value may be mentioned twice.
- Backwards questions have exactly one row with the given relation + value.
- Every item has at least two rows outside its support.

### Frame

| key | meaning |
|---|---|
| `kind` | `value` \| `who` \| `yesno` \| `count` \| `compare` \| `before` \| `after` |
| `who` | people named in the question, in order, excluding the one given in `value` |
| `relations` | notebook relation names, in hop order |
| `value` | the known value: the given value in a `who` question, the value checked in `yesno`, the pivot in `before`/`after`; otherwise null |
| `direction` | `compare` only: `more` or `less` of the relation's number (older = `less` birth_year, taller = `more` height_cm); otherwise null |

Kind by category: one_step, two_step, heldout_three_step, newest_correction,
missing_fact -> `value`; backwards -> `who`; yes_no -> `yesno`; counting ->
`count`; comparing -> `compare`; before_after -> `before` or `after`. Frame
relation names are the notebook's own. In missing_fact the last relation in
the frame may be absent from the notebook.

## Categories

| category | items | notebook rows | what it tests |
|---|---|---|---|
| one_step | 30 | 3-38 | one relation of a named person |
| two_step | 30 | 4-40 | chain of two relations |
| heldout_three_step | 30 | 6-38 | chain of exactly three relations |
| backwards | 30 | 5-39 | subject given relation + value |
| yes_no | 30 | 3-40 | direct fact check (15 yes, 15 no; "no" values are near misses) |
| counting | 30 | 6-38 | distinct values of a multi-valued relation (answers 1-7) |
| comparing | 30 | 4-40 | compare two people on a number |
| before_after | 30 | 4-40 | neighbour in a year-ordered history (15 before, 15 after) |
| newest_correction | 30 | 4-37 | two conflicting rows; larger `when` wins (12 list the newer row first; 19 one-hop, 11 two-hop) |
| missing_fact | 30 | 3-38 | needed row absent, with near misses (same relation for someone else, same person with other relations); gold UNKNOWN (9 one-hop, 16 two-hop, 5 three-hop) |
| **total** | **300** | | |
