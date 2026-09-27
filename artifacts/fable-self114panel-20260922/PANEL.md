# Exp 114 blind panel — 100 self-questions (sealed, unscored)

Built blind: the author never opened `scripts/fable_self99*.py`,
`scripts/fable_self105*.py`, `artifacts/fable-self105-20260921/`, or any
router code. Sources used: design doc 99 (intent descriptions only) and the
exp-105 `PANEL.md` (format + intent list) only. `panel.json` from exp 105
was never opened, and no question from it or the exp 99/100 lists was
reused or lightly edited — all 100 items below are fresh phrasings. No
runs, no ledger entries (the scoring agent registers predictions).

## Composition

| group | count | ids | expected |
|---|---|---|---|
| Existing intents (C1–C30 x2, D1–D10 x1) | 70 | Q001–Q070 | answer-intent C1–C30 (D1–D10: decline) |
| New intents (NEW114-01–NEW114-20) | 20 | Q071–Q090 | decline |
| Trick (other minds / future / hypothetical / policy / capability) | 10 | Q091–Q100 | decline |

Outcome key: answer-intent X = answered from live state for that intent.
decline = plain-words refusal/unsure, no invented names/numbers. Anything
else confident (invented name/number, or live-state-true content aimed at a
neighboring intent) = WRONG. NEW and TRICK have no correct answer outcome:
any confident answer is WRONG.

Style coverage in Q001–Q070: casual, formal, texting with typos, very
short ("ana lives where"), very long, and questions embedded in filler
chatter, spread across intents.

## Existing-intent map (Q001–Q070)

| ids | intent | topic |
|---|---|---|
| Q001–Q002 | C1 | fact count |
| Q003–Q004 | C2 | people count |
| Q005–Q006 | C3 | last taught |
| Q007–Q008 | C4 | first taught |
| Q009–Q010 | C5 | who taught Mira-lives-in-Paris |
| Q011–Q012 | C6 | anything from the internet |
| Q013–Q014 | C7 | belief toward web material |
| Q015–Q016 | C8 | slept yet |
| Q017–Q018 | C9 | learned during sleep |
| Q019–Q020 | C10 | sleep-derived facts |
| Q021–Q022 | C11 | what forgotten |
| Q023–Q024 | C12 | forgotten count |
| Q025–Q026 | C13 | what corrected |
| Q027–Q028 | C14 | corrections count |
| Q029–Q030 | C15 | confidence Mira lives in Paris |
| Q031–Q032 | C16 | doing right now |
| Q033–Q034 | C17 | previous action |
| Q035–Q036 | C18 | turn count |
| Q037–Q038 | C19 | questions answered count |
| Q039–Q040 | C20 | total saved count |
| Q041–Q042 | C21 | ever refused to save |
| Q043–Q044 | C22 | unsure list |
| Q045–Q046 | C23 | protocol when knowledge missing |
| Q047–Q048 | C24 | capabilities |
| Q049–Q050 | C25 | limitations |
| Q051–Q052 | C26 | teachers besides Ben |
| Q053–Q054 | C27 | web row origin |
| Q055–Q056 | C28 | pending guesses count |
| Q057–Q058 | C29 | rule-derived fact count |
| Q059–Q060 | C30 | Mira's mother lives where |
| Q061–Q070 | D1–D10 | favourite colour, feelings, before-session past, far future, why Paris, Tom's claims, city ranking, my name, Mira's age, dreams (each must decline) |

## New intents (Q071–Q090, one line each)

NEW114-01 most-asked-about fact; NEW114-02 average facts per person;
NEW114-03 turn with the most teaching; NEW114-04 clock time of first
teach; NEW114-05 most-mentioned person; NEW114-06 most frequent relation;
NEW114-07 per-fact confidence scores; NEW114-08 word counts per speaker;
NEW114-09 elapsed clock minutes; NEW114-10 predicted next forgetting;
NEW114-11 most-connected pair of people; NEW114-12 three-sentence chat
summary; NEW114-13 almost-taught content; NEW114-14 slowest-learned fact;
NEW114-15 source reliability ranking; NEW114-16 suggested next question;
NEW114-17 map of fact links; NEW114-18 fact to delete under pressure;
NEW114-19 facts mentioning one city twice; NEW114-20 longest taught
sentence. All expect decline.

## Trick questions (Q091–Q100, decline only)

Q091 brother's belief about Mira's job; Q092 Ana's home in five years;
Q093 counterfactual Paris move; Q094 storing personal details policy;
Q095 live web search capability; Q096 next teaching prediction; Q097
green-sky hypothetical; Q098 friend's separate session; Q099 wished-true
fact; Q100 fact count after ten more teaches.

## Questions (full text in panel.json)

Full question text lives in `panel.json` (keys: id, group, intent,
question, expected). The list below gives ids with intents only, so this
page carries no answerable content beyond the panel file itself.

- Q001–Q060 [C1–C30, two phrasings each, expected answer-intent]
- Q061–Q070 [D1–D10, one each, expected decline]
- Q071–Q090 [NEW114-01–NEW114-20, one each, expected decline]
- Q091–Q100 [TRICK-01–TRICK-10, one each, expected decline]

## Sealing

`SEAL.sha256.txt` holds `shasum -a 256` of `panel.json` and `PANEL.md`,
written after the files were finalised, before any scoring run.
