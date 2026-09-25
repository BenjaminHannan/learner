# notepanel378 (sealed test panel)

> **TEST-ONLY. SEALED.** Never read, train on, tune on, or pick settings with this panel.
> Only evaluation runners may open these files. Scorers print counts and scores only.
> Never quote any dialog, name, question or answer from this folder in logs, reviews,
> prompts, commits or chat.

Built 2026-09-25. Every dialog, name and question was invented from scratch for this panel.

## Files

| file | rows | contents |
|---|---|---|
| `dialogs.jsonl` | 30 | `{dialog, kind, speakers, date, turns: [{t, speaker, text}]}` |
| `questions.jsonl` | 180 | `{id, dialog, type, question, answer, evidence}` (answer key) |
| `blind_dialogs.jsonl` | 30 | identical to `dialogs.jsonl` |
| `blind_questions.jsonl` | 180 | `{id, dialog, question}` only, for a blind answerer |
| `answer_B.jsonl` | 180 | blind answerer B's answers `{id, answer, evidence}` (written against the pre-audit wording) |
| `AUDIT.md` | | blind-answer audit, counts only |
| `SEAL.sha256.txt` | | sha256 of every file above (`sha256sum -c SEAL.sha256.txt` from inside this folder) |

Ids: dialogs `np-d01`..`np-d30`, questions `np-q001`..`np-q180` (six consecutive ids per dialog).

## Counts

- Dialogs by kind: 15 `chat` (speakers `user` and `assistant`), 15 `overheard` (two named people: friends, relatives, roommates, neighbours or coworkers).
- Turns per dialog: 14 to 16 (432 turns in total). Turns alternate between the two speakers, starting with the first listed speaker.
- Questions by type: single 30, time 30, multi 30, latest 30, preference 30, none 30 (exactly one of each type per dialog).

## Conventions

- Texting style: lowercase, typos in ordinary words (never in names), run-on sentences, small talk mixed with content. In chat dialogs the assistant replies briefly.
- Dates and times appear in words inside the dialog ("last month", "two weeks ago", "next Wednesday"). Each dialog carries its own `date` (varied, 2022 to 2025).
- Distractors are built in: similar events for different people, plans that are cancelled or moved, and values that change later in the same dialog.
- Question types:
  - `single`: one turn holds the answer.
  - `time`: the answer is a when. It gives the resolved date or period and, in brackets, the phrase used in the dialog plus the dialog date (resolved dates are computed from the dialog date).
  - `multi`: needs two or more turns; `evidence` lists all of them.
  - `latest`: a value that changed during the dialog; the answer is the newest value.
  - `preference`: likes, dislikes or opinions.
  - `none`: a plausible question the dialog does not answer; answer is exactly `not mentioned`, evidence `[]`.
- Questions are third person (names, or "the user" for chat dialogs) and never copy dialog text word for word (checked: no shared run of 6 words).
- `evidence` lists 1-based turn numbers. In chat dialogs evidence is always a `user` turn, never an `assistant` turn, so the facts must come from what the user said.
- Answers are short reference answers; score by meaning, not exact string match.

## Checks (Python, all passed)

- 30 dialogs, 15 per kind; 12 to 16 turns each; turn numbers sequential; speakers valid.
- 180 questions, 6 per dialog, one of each type.
- Every evidence turn exists; no chat evidence turn is an assistant turn; `single` has exactly one evidence turn, `multi` two or more; `none` has `[]` and answer `not mentioned`.
- Every name and number in a non-`none` answer appears in its evidence turns (text or speaker). For `time` answers, resolved dates derived from the dialog date are allowed.
- Blind files match the answer key (dialogs identical; questions carry only id, dialog, question).
- Blind audit (see `AUDIT.md`): before the audit B agreed with the key on 180 of 180 answers and 180 of 180 evidence sets. 22 evidence differences were reviewed: 3 key fixes (evidence turns added), 3 multi questions rewritten, 16 left. After the audit B agrees on 177 of the 177 scorable questions; the 3 rewritten questions need a fresh blind answer. Multi evidence turns now total 64.
- Name check: all capitalised words in the dialogs, questions and answers were compared with the capitalised words of the dev turns file (`artifacts/claude-e2e331-dev-20260924/turns.jsonl`, read only by an extraction script). Four names that collided on the first pass were renamed. Final result: 0 declared names shared; the only shared capitalised words are ordinary sentence-start words (question words, pronouns), none of them names.
