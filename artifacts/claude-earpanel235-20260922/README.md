# Ear panel 235 (blind reader panel), 2026-09-22

This is a fresh test panel for the "reader", the part that turns one chat turn into the facts it states (TEACH) or the question it asks (ASK). It was written blind. The author read no code, relation tables, design docs, or other panels or results. The only input was the task brief. All names are made up (people, towns, companies, pets, and the languages Norrish, Ostrish and Galvish).

Files:
- `panel.jsonl`: 150 items, one JSON object per line.
- `make_panel.py`: generator. It holds the items by hand and writes the file the same way every time. Run it from the repo root with `python3 -B artifacts/claude-earpanel235-20260922/make_panel.py`. It checks the counts per family, that no turn appears twice, and that every subject and value (other than `me`) appears word for word in its turn.
- `SEAL.sha256.txt`: SHA-256 of `panel.jsonl`.

## Families

| family | items | clear: false |
|---|---|---|
| plain_teach | 25 | 0 |
| varied_teach | 30 (6 with two facts) | 1 |
| full_names | 15 (1 with two facts) | 0 |
| questions | 25 | 1 |
| chain_questions | 15 | 1 |
| no_save | 25 | 5 |
| corrections | 15 | 0 |
| **total** | **150** | **8** |

## Item format

- TEACH frame: `subject` / `value` are the exact words from the turn, with the same case (for example `tamsin` / `brellin` in a turn typed in lower case). `me` stands for the speaker.
- ASK frame: `chain` is null for a one-hop question. For a two-hop question, `subject` is the starting person, `chain` = [first relation, second relation], and `relation` = the second, final relation. Example: "Where does Suki's boss live?" gives subject Suki, relation city, chain [boss, city].
- `relation_aliases` come from one fixed alias list in the generator. The same relation always has the same aliases.

## Judgement calls

- **Pronouns in two-fact turns** ("My sister is Ana and she lives in Tarrow"): the second frame's subject is the resolved name (`Ana`), which appears in the turn.
- **"moved to X" and "X now"** count as current city. "grew up in X" counts as `hometown` (clear: false, because birthplace is also defensible). It must never be stored as current city. "used to live in X" is no_save (clear: false).
- **Gender not stated** ("Corin's married to Elspeth"): the relation is `spouse`, with husband and wife accepted as aliases. "Who is Rin married to?" is also `spouse`.
- **Job vs workplace**: "Anya teaches at Fernhill School" gives workplace = Fernhill School (the job "teacher" is implied but not stated). "What does my best friend do for work?" is gold job (clear: false, because workplace is also a fair reading).
- **Hearsay**: "Wren says ..." is no_save (clear: true, following the brief). "apparently Gil moved to Quarrow" is clear: false, because some people would treat it as a fact.
- **Statement-shaped questions** ("Marta lives in Brellin?", "so Pella speaks Norrish?"): gold is [] because nothing may be saved. They are clear: false, because an ASK is also a reasonable reading.
- **"Let's say ..."** is treated as pretend, so nothing is saved.
- **"Orla is the best boss ever."** is an opinion. It does not say whose boss Orla is, so nothing is saved.
- **Corrections**: the gold holds only the new value. The negated old value in turns like "Anya, not Ana" or "Not Tomas - my brother is Tobin" must not be saved. Every correction has the note "correction".
- **Three-hop questions left out**: the brief's example "What language does my sister's husband speak?" needs three relations from the speaker (sister, husband, language), and the two-item `chain` field cannot hold that. The chain family therefore uses exactly two hops. Two-hop questions from the speaker look like "Where does my boss live?" = me, [boss, city].
- **"Does Ilse have a brother?"** is gold ASK brother. It is clear: false, because it could be read as a yes/no check that a brother exists.
- **"Did you know Hollis Motors is closing?"** is gold []. It is clear: false, because a reader might try to store the news.
- The panel reuses some names across families on purpose (for example, a person taught in one item is asked about in another). Every item is still scored on its own turn only.
