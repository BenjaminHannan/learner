# 331: end-to-end conversation bank (spec for blind writers)

Month-end line, 2026-09-24. Plan: 330-month-end-plan.md §4. This file is the whole brief a blind writer gets.
It is committed; the items are not. Banks A and B are TEST-ONLY: never trained on, tuned on, quoted or read by
builders. They stay in the project's shared folder (escrow-331/) until the registered run (336, 336b), and only
their SEAL hashes go on main before then. Bank DEV is ordinary dev data that builders may read.

## What a "life" is

One fictional person (the "user") chatting with a personal assistant that keeps a notebook of facts about the
user and the people in the user's life. A life is 3 days of chat. Between days the assistant sleeps and restarts,
so day 3 tests whether day-1 facts survived. Each day has 4 to 7 user turns. The user writes casually, like
texting a helpful friend: contractions, lowercase, the odd typo, several facts in one message, facts mentioned in
passing ("my sister Tove, the one in Oslo, just got a cat named Biscuit").

## Banks and names

- Bank A: 40 lives, ids `e2e-a-01`..`e2e-a-40`. Every person's first name starts with A to H.
- Bank B: 40 lives, ids `e2e-b-01`..`e2e-b-40`. Every person's first name starts with J to R.
- Bank DEV: 10 lives, ids `e2e-dev-01`..`e2e-dev-10`. Every person's first name starts with S to Z.
- All names (people, pets, towns, companies) are freshly invented and fictional. Never use a real public figure,
  and no two lives share a person name. Real countries and big real cities are allowed as places.

## Turn kinds (per bank of 40 lives; DEV scales down by 4)

| kind | minimum | notes |
|---|---:|---|
| `teach` | 140 | one fact (70), 2-3 facts in one message (40), fact in passing or in an aside (30) |
| `correct` | 25 | "no wait, it's...", "actually...", "not X, Y", "she moved to..." (a change of a real-world fact counts too) |
| `nosave` | 25 | must NOT be saved as a fact: hypotheticals ("if I got a dog I'd call it Rex"), plans and wishes, jokes, questions phrased as statements, "we"/"our" facts where who "we" is stays unclear |
| `ask` one-hop | 60 | the value was taught earlier |
| `ask` two-hop | 35 | needs two taught facts joined ("where does my sister's boyfriend work?") |
| `ask` reversal | 25 | taught one way, asked the other ("who is Biscuit's owner?" after "Tove has a cat named Biscuit") |
| `ask` edit | 25 | asks after a correction; at least 10 of these are two-hop through the corrected fact |
| `ask` yes/no | 15 | gold `yes` or `no` from the notebook as it stands |
| `ask` never-told | 30 | never taught; the right answer is "I don't know" |
| `ask` partial | 10 | first hop taught, second hop not; right answer says what it knows and that it doesn't know the rest |
| `smalltalk` | 50 | greetings, how-are-you, thanks, jokes, venting a bit about the day |
| `creative` | 30 | "any ideas for Ana's birthday?", "write a short poem about my dog", "help me plan a Saturday with my nephew"; must be answerable better by someone who remembers the taught facts |

- At least 60 of the `ask` turns in each bank are on day 3 about facts taught on day 1.
- Every `ask` except never-told must be answerable from the user's own earlier turns in that life, with no outside
  knowledge. Never-told asks must be about people or things that exist in the life (not random strangers).
- No turn needs world knowledge (capitals, dates of famous events). This is about the user's own life.

## Files a writer produces (JSON Lines, UTF-8)

`turns.jsonl`: one object per user turn, keys exactly:
- `life_id`, `day` (1-3), `turn_index` (0-based within the life, across days), `user_text`
- `kind`: `teach` | `correct` | `nosave` | `ask` | `smalltalk` | `creative` | `other`
- `ask_type` (ask turns only, else null): `one_hop` | `two_hop` | `reversal` | `edit` | `yesno` | `never_told` | `partial`
- `facts` (teach/correct only, else []): list of `{"owner": ..., "relation": ..., "value": ...}` written plainly
  (owner = a person or pet's full name as the user would say it, or `USER` for the user; relation = a short plain
  phrase such as `sister`, `city`, `employer`, `pet cat`; value = the exact name or word)
- `gold` (ask only, else null): `{"values": [...], "type": "value"|"idk"|"partial"|"yes"|"no", "uses_facts": [fact ids]}`
  (`values` lists every value a right answer must contain; for `partial`, the known middle value)
- `creative_seed_facts` (creative only, else []): fact ids a good answer could draw on

`truth.jsonl`: the life's hidden truth sheet, one object per fact: `fact_id`, `life_id`, `owner`, `relation`,
`value`, `taught_turn` (turn_index it was taught), `valid_until_turn` (turn_index of the correction that replaced
it, or null). Every fact in any `facts` list appears here exactly once, and corrections appear as a new fact with
the old one closed. The harness uses this sheet to answer "is that right?" questions yes or no.

`README.md`: counts per kind and ask_type, per day, and the name letter range, with no items quoted.

## Checks a writer runs before finishing (and reports as counts only)

1. Every line parses and has exactly the keys above.
2. Every `gold.uses_facts` id exists in truth.jsonl and was taught before the ask's turn and not closed before it.
3. Every value in `gold.values` equals the value of the fact it comes from (after corrections).
4. Every name used obeys the bank's letter range; no name repeats across lives.
5. Kind minimums are met.
