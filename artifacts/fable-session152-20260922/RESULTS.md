# Exp 152 RESULTS — realistic-user session red team (no fixes, bugs only)

6 phone-voice sessions x 30 turns x 2 targets (T-Q loop149-qrewrite,
T-T loop139b) = 360 turns, fresh daemon dir per session, mailbox,
one file per turn. Every reply byte-identical across targets: all
classes reproduce on both. Zero writes from small talk (no critical).
1 HARNESS-ERROR: none. Budget: 3.0 s Mac CPU.

## Marks table (per target; 180 turns each)

| mark | bar | T-Q | T-T | status |
|---|---|---|---|---|
| M1 sessions | 6x30, mix as sealed | 180 | 180 | PASS |
| M2 coverage | every turn reported, never averaged | 180/180 | 180/180 | PASS |
| M3 known-only | K144/K146/K147/K148/K150/K151 excluded | 7 tagged turns | 7 tagged turns | PASS |
| M4 verdicts | OK/WRONG/UNHELPFUL/H-E on every turn | 130/2/48/0 | 130/2/48/0 | PASS |
| M5 budget | < 1500 s | 3.0 s shared | — | PASS |
| M6 additive | own files only, no commits | clean | clean | PASS |

Correction (documented, raw JSONs annotated): S5-T16 both targets
mechanical UNHELPFUL -> OK — idempotent re-teach honestly answered
"I already have that." with 0 writes; the judge wrongly demanded the
stored value in the reply.

## Novel bug classes (known 6 excluded), ranked by 10-minute-chat frequency

| # | class | instances (x2 targets) | cause file:line | one-line proposed single-change fix |
|---|---|---|---|---|
| N1 | every greeting/thanks/lol/bye ("hi", "lol", "thanks!", "ok cool", "k bye") gets "I didn't understand..." | 46 | fable_loop90_agent.py:291 (ChainEars fallthrough; no stage matches) | add a no-write small-talk stage returning a greeting/thanks reply |
| N2 | "who are you" / "what can you do" gets "I didn't understand..." | 10 | same fallthrough; no identity stage | add a no-write identity card (name, teach/ask/how-it-works pointer) |
| N3 | pronouns die ("where does she live?", "what about his mom?"); "mom" != "mother" too | 10 | fable_agent_loop.py:94 (_QUESTION, 's-split only) + :153 (_relation literal) | resolve she/he/his/her to last-mentioned entity; alias mom->mother |
| N4 | "btw/also/oh and + teach" refused, later asks honestly-but-stuck MISSING (8 stuck turns per target) | 16 | fable_agent_loop.py:96 (_STATEMENT ^-anchored) + :141 (one-word-name refuse of "btw marta") | strip leading fillers (btw/also/oh and/hey) before statement parse |
| N5 | "what's X's city?" / "tell me X's city" refused though fact known | 4 | fable_agent_loop.py:94 (who\|what\|where + is\|are only) | accept what's (= what is) and tell-me/show-me imperatives as ask |
| N6 | bare "no wait, it's Denver" ignored (needs Actually-/no,-prefix) | 2 | fable_agent_loop.py:95 (_CORRECTION prefix set) | accept bare corrections against most-recent taught subject |
| N7 | "city???" leaks punctuation into relation -> "I don't know Vera's city??." | 2 | fable_agent_loop.py:94 ([?.]? strips one mark) | strip [?.!]+ trailing marks |
| N8 | "my dog is biscuit" rejected (needs possessive shape) | 2 | fable_agent_loop.py:96 + :143 (chain must be exactly 2 's-parts) | treat leading "my" as self-name alias in statements |
| N9 | WRONG: "Who is Ana's pet's color?" answers "not someone I can look up" though Biscuit's color is taught | 4 | fable_notebook_contract.py:405 (BROKEN_CHAIN on literal mid-value; pet not in PERSON_RELATIONS fable_agent_loop.py:91) | continue hop through literals matching a known entity name/alias |

Known re-confirmed (1 instance each, excluded): K147 married-to, K148 year,
K150 hedge-clarify (no write, good), K144 two-of, K146 refused-correction
staleness (T15 Lima consistent after refusal; T17 Quito via Actually works),
K151 no-"?" question answered fine.

## Reproduce

export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy \
python -B scripts/fable_session152_run.py   # seal check: shasum -c artifacts/fable-session152-20260922/SEAL.sha256.txt

What it means: a normal person's first 10 minutes (hi, who-are-you, "my mom
is X", pronouns, btw/also, what's/tell-me) fail on every session; one shape
(N9) answers wrong instead of abstaining.
What it does not mean: no silent wrong writes were found (0 in 360 turns);
canonical "X's REL is Y / Who is X's REL?" paths all work, including
lowercase, emoji values, 2-hop chains, Actually-corrections and delayed re-asks.
