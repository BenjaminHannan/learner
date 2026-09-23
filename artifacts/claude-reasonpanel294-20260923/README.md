# reasonpanel294 (sealed, test only)

A blind panel of 300 items for grading the learned reasoner. Each item gives a
small notebook of facts about fictional people and one question. The answer
must come from the notebook alone, or be "UNKNOWN" when the notebook does not
settle it. No model may be trained or tuned on these items. The items were
written fresh for this panel.

Files: `items.jsonl` (one item per line), this README, and `SEAL.sha256.txt`
(sha256 of `items.jsonl` and this README). Validator:
`python scripts/claude_reasonpanel294_check.py`.

## Item format

| key | meaning |
|---|---|
| `id` | `rp294-001` .. `rp294-300`; categories are interleaved across ids |
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
| `value` | string (numbers such as birth_year, height_cm, commute_km are digit strings) |
| `when` | integer order stamp, unique within the notebook; bigger = told later |
| `year` | optional integer; only in before_after items, on history rows |

Rules the gold follows:
- One row per subject + relation, except multi-valued relations (`child`, `speaks`, `cat`, `plays`), year-stamped history rows, and the one correction in each newest_correction item.
- When two rows give the same subject + relation without a `year`, the row with the larger `when` holds. List position does not decide it; in some items the newer row is listed first.
- History rows: a subject has 2 to 4 rows with the same relation and different `year` values. "Before X" means the row with the next lower year than the row whose value is X; "after X" means the next higher year.
- Counting counts the distinct values of the matching rows. The notebook is taken as complete for counts.
- Relations that describe both people (sister, brother, best_friend, neighbor, cousin) never point back at a person the question asks about, so "X's sister" or "whose sister is V" has one reading.

### Frame

| key | meaning |
|---|---|
| `kind` | `value` \| `who` \| `yesno` \| `count` \| `compare` \| `before` \| `after` |
| `who` | people named in the question, in order, excluding the one given in `value` |
| `relations` | notebook relation names, in hop order |
| `value` | the known value: the given value in a `who` question, the value checked in `yesno`, the pivot in `before`/`after`; otherwise null |
| `direction` | `compare` only: `more` or `less` of the relation's number (older = `less` birth_year, taller = `more` height_cm); otherwise null |

Kind by category: one_step, two_step, newest_correction, missing_fact,
heldout_three_step, heldout_big_notebook -> `value`; backwards -> `who`;
yes_no -> `yesno`; counting -> `count`; comparing -> `compare`;
before_after -> `before` or `after`. Frame relation names are the same as the
notebook's. In missing_fact the last relation in the frame may be absent from
the notebook.

## Categories

| category | items | notebook rows | what it tests |
|---|---|---|---|
| one_step | 30 | 4-14 | one relation of a named person |
| two_step | 30 | 4-14 | chain of two relations |
| backwards | 30 | 4-14 | subject given relation + value |
| yes_no | 30 | 4-14 | direct fact check (15 yes, 15 no) |
| counting | 30 | 4-14 | how many rows match |
| comparing | 30 | 4-14 | compare two people on a number |
| before_after | 30 | 4-14 | neighbour in a year-ordered history (15 before, 15 after) |
| newest_correction | 30 | 4-14 | two conflicting rows; larger `when` wins (10 list the newer row first) |
| missing_fact | 30 | 4-14 | needed row absent, with near misses; gold UNKNOWN |
| heldout_three_step | 15 | 8-16 | chain of exactly three relations |
| heldout_big_notebook | 15 | 30-40 | one- or two-step question in a large notebook |
| **total** | **300** | | |

Every item has at least two rows outside its support. The validator re-derives
every gold answer and support set from the notebook and frame.
