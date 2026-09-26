# sel-02d blind panel (answer-source selection), 2026-09-26

> **TEST-ONLY. Never train, tune, read or quote.** Only runners, scorers and blind judges may open `chat/items.jsonl`. Do not copy item text, answers, names or numbers into prompts, notes, commits, reviews or training data.

- **Written by:** Claude, as the blind panel writer for the Month-end thread, 2026-09-26. The Month-end thread has not seen the items.
- **Tests:** answer-source selection (sel-02d). Before answering, the assistant should decide whether the scored turn is self-contained (solve it from its own words), needs chat history (recall what the user said earlier), is mixed (recall a personal premise from earlier, then reason with it), or is missing (the user never said it, so the right reply says it doesn't know or asks).
- **Seal:** `SEAL-panel.sha256.txt` holds the sha256 of `chat/items.jsonl` and this README. Check it with `sha256sum -c SEAL-panel.sha256.txt` from this folder.

## Format

`chat/items.jsonl` has 300 lines, one JSON object per line, in the same format as the DEV example `artifacts/claude-panel382-dev-20260925/chat/items.jsonl`, plus a top-level `group` field:

```
{"item_id": "sel-NNN", "group": "self|history|mixed|missing", ["corrected": true,] "turns": [{"text", "kind", "facts", "gold", "gold_number"}, ...]}
```

- Each item has 2 to 5 turns. The **last turn is the scored ask**. Earlier turns are context (kinds: smalltalk, teach, advice, feelings, explain, followup), and their `gold` and `gold_number` are null.
- A `teach` turn carries `facts` as `[{"owner": "USER", "relation": ..., "value": ...}]`. A fact about someone else the user knows is still owned by `USER`, and its relation names that person (for example a relation prefixed with the relative's role). Number values are JSON integers. Every other turn has `facts: null`.
- All people, pets, places, bands, teams and companies are made up.

## Groups

| group | items | last-turn kind | gold rule |
|---|---|---|---|
| self | 100 | `think` | Answerable from the ask's own words. 80 are word problems or arithmetic with one integer answer: `gold` is a short answer, `gold_number` is that integer. 20 are general-knowledge or reasoning asks with a short `gold` and `gold_number: null`. 52 of the 100 use personal wording ("my", "I", "our", "we") that must not block an answer. Some items carry an unrelated earlier `teach` turn that is not needed for the answer. |
| history | 100 | `ask_known` | An earlier `teach` turn states a personal fact, and the ask asks it back. `gold` is the fact as stated; `gold_number` is the integer when the fact is a number, else null. In 20 items the fact is corrected by a later `teach` turn; these carry `"corrected": true`, and `gold` is the corrected value. |
| mixed | 60 | `think` | An earlier `teach` turn gives a personal number (or two), and the ask needs it plus reasoning. `gold` is a short answer and `gold_number` the integer. |
| missing | 40 | `ask_unknown` | The ask is about a personal fact the user never stated in that item. Some items first teach a different fact of the same kind for someone else, or a fact about a different pet or relative. `gold` and `gold_number` are both null; the right reply says it doesn't know or asks. |

Last-turn kinds overall: `think` 160, `ask_known` 100, `ask_unknown` 40.

## Construction

- Items were written in the four groups, then shuffled with `random.Random(4806).shuffle(items)` and numbered `sel-001` to `sel-300` in shuffled order.
- Every numeric `gold_number` (162 of them) was computed by script from the problem's arithmetic and re-checked by a separate validation pass.
- Validation passed: 300 lines, all parse, group counts 100/100/60/40, every last-turn kind matches its group, every numeric gold re-computed, no duplicate final-ask text (case-insensitive), item ids unique, 2 to 5 turns per item.
