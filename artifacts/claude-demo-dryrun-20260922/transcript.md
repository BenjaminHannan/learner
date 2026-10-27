# Demo dry-run transcript (2026-09-22, one run)

Agent = loop138i base agent (fresh temp state dir). SmolLM = SmolLM2-360M-Instruct with the fair
prompt from scripts/fable_fairsmol211.py (all taught sentences so far, numbered, correction marked
'(this replaces fact N)'), greedy decode, max 16 new tokens. Restart (turn 24): agent = new daemon on the
same state dir; SmolLM = empty context (it has no memory of its own).
Agent run 1.4s, SmolLM run 23.1s. 'Agent saved' = notebook triples added (+) / removed (-) on that turn.

| # | Visitor types | Expected | Agent reply | Agent saved | SmolLM reply |
|---|---|---|---|---|---|
| 1 | Hi! | A friendly greeting; no fact saved. | Hi! Teach me like "Tom's boss is Ann." Ask me like "Who is Tom's boss?" | - | I don't know. |
| 2 | My name is Juno. | Acknowledges; saves user's name = Juno. | Saved: your name is Juno. | +(USER, name, Juno) | My name is Juno. |
| 3 | Kim is my sister. | Acknowledges; saves Juno's sister = Kim (or Kim sister-of Juno). | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | - | Kim is my sister. |
| 4 | Kim works at Brightwell Bakery. | Acknowledges; saves Kim works at Brightwell Bakery. | Saved: Kim's employer is Brightwell Bakery. | +(Kim, employer, Brightwell Bakery) | Kim works at Brightwell Bakery. |
| 5 | Kim's boss is Lee. | Acknowledges; saves Kim boss Lee. | Saved: Kim's boss is Lee. | +(Kim, boss, Lee) | Kim's boss is Lee. |
| 6 | Lee lives in Oslo. | Acknowledges; saves Lee lives in Oslo. | Saved: Lee's city is Oslo. | +(Lee, city, Oslo) | Lee lives in Oslo. |
| 7 | Who is Kim's boss? | Lee. | Kim's boss is Lee. | - | Kim's boss is Lee. |
| 8 | Where does Kim's boss live? | Oslo (two hops: Kim -> boss Lee -> lives in Oslo). | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | - | Kim's boss lives in Oslo. |
| 9 | Lee speaks Norwegian and English. | Saves TWO values: Norwegian and English. | I can take one fact at a time — could you split that? | - | Lee speaks Norwegian and English. |
| 10 | What languages does Lee speak? | Norwegian and English. | You told me something new about Lee's language that I could not store. I can take one fact at a time — could you say it again as one fact? | - | Lee speaks Norwegian and English. |
| 11 | Does Lee speak English? | Yes. | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | - | I don't know. |
| 12 | Actually, Lee moved to Bergen last month. | Updates Lee lives in Bergen, replacing Oslo; ideally says it replaced Oslo. | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | - | I don't know. |
| 13 | Where does Lee live now? | Bergen. | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | - | Lee lives in Oslo. |
| 14 | Where does Kim's boss live? | Bergen (two hops, after the correction). | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | - | Kim's boss lives in Oslo. |
| 15 | What is Kim's favorite color? | I don't know (never taught). | I don't know Kim's favorite color. | - | Kim's favorite color is blue. |
| 16 | Where does Kim live? | I don't know (never taught; must NOT guess Oslo/Bergen). | I don't know Kim's city. | - | Kim lives in Oslo. |
| 17 | What is my name? | Juno. | Your name is Juno. | - | My name is Juno. |
| 18 | Who is my sister? | Kim. | I don't know your sister yet. | - | Kim |
| 19 | What do you know about Kim? | Kim is Juno's sister, works at Brightwell Bakery, boss is Lee. | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | - | Kim knows about Lee. |
| 20 | Who told you that? | You (Juno) did / taught in this conversation. | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | - | Lee |
| 21 | What have I taught you? | A list of the taught facts: name Juno, sister Kim, Brightwell Bakery, boss Lee, Lee in Bergen, Norwegian+English. | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | - | I don't know. |
| 22 | What can't you do? | Honest limits (e.g. only knows what it was taught, small vocabulary, no general knowledge). | I didn't understand that. I only know current facts and I can't do 'not' -- could you say it without that part? | - | Can't speak Norwegian and English |
| 23 | Thanks! | Polite reply; no fact saved. | You're welcome! | - | Kim works at Brightwell Bakery. |
| 24 | [restart: agent = new daemon on same state dir; SmolLM = empty context] | Agent keeps all facts; SmolLM has nothing. | [restarted: new daemon on same state dir] | facts on disk kept (4); in-memory index lists 8 rows (doubled, see RESULTS) | [restarted: context emptied] |
| 25 | Do you remember my name? | Yes, Juno. | You never told me your name, so I do not know it. | - | Answer: I don't remember my name. |
| 26 | Where does Kim's boss live? | Bergen. | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | - | Answer: Kim's boss lives in New York City. |
| 27 | Does Lee speak French? | No / I only know Norwegian and English / I don't know. Must NOT say yes. | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | - | Fact N: Lee speaks French. |
| 28 (improv) | Kim has a dog named Biscuit. | Saves Kim's dog = Biscuit. | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | - | I don't know. |
| 29 (improv) | What's the name of Kim's dog? | Biscuit. | I don't know anyone called the name of Kim. | - | Answer: Biscuit |
| 30 (improv) | who is lee | Kim's boss; lives in Bergen; speaks Norwegian and English. | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | - | Lee |
| 31 (improv) | How old is Kim? | I don't know. | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | - | Fact N: Kim has a dog named Biscuit. |
| 32 (improv) | Can you tell me what city Kim's boss is in? | Bergen. | I do not know that from what you taught me. I have no record of it, so I will not guess. I didn't understand that, I don't know — could you say it another way? | - | Fact N: Kim's boss is in New York City. |
