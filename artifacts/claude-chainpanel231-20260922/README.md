# Chain panel 231 (blind), 2026-09-22

72 multi-step ("chain") questions for the notebook assistant. Written blind: no code, relation tables, design docs, other panels or results were read. All people, towns, companies and languages are invented.

Files: `panel.jsonl` (the panel), `make_panel.py` (the generator, which holds the items and checks the counts), `SEAL.sha256.txt` (SHA-256 of panel.jsonl).

Setups use only these forms: "<Name>'s <relation> is <Value>.", "My <relation> is <Value>.", "<Name> lives in <Town>.", "<Name> works at <Company>.", "<Name> speaks <Language>.". Each setup has 1 to 5 sentences, and many include distractor facts.

## Families (9 items each)

| family | what it tests | expect |
|---|---|---|
| verb_2hop | "Where does X's R live / work?", "What language does X's R speak?" | 9 answer |
| possessive_2hop | "What is X's R's town/language?", "Who is X's R's R2?" | 9 answer |
| of_form | "the R of X", including a double of-form | 9 answer |
| three_hop | three lookups (including one "boss's boss's boss") | 9 answer |
| user_chain | chains that start at "My R is ..." (two of them are 3-hop) | 9 answer |
| yes_no_chain | yes/no checks of a chained fact | 9 answer (5 yes, 4 no) |
| casual | lowercase, contractions, filler words, an indirect question | 9 answer |
| traps | missing middle fact (3), unknown person or relation (2), fact stored under a different relation (2), two conflicting towns (2) | 9 abstain |

Totals: 63 answer, 9 abstain. Hops: 60 two-hop, 12 three-hop. clear: 70 true, 2 false.

## Judgement calls
- **"clear"**: true means a careful human would agree the expected behaviour is fully decided by the setup. For answer items, that means the setup settles the answer. For trap items, it means the setup clearly does not settle it, so abstaining is the only correct response. The two conflicting-town traps (c231-071, c231-072) are marked `clear: false`, because a person might treat the later sentence as a correction.
- **"no" answers** (yes_no_chain) use only lives-in (one home assumed) or single-valued person relations (husband/wife). None depends on "does not speak" or "does not work at", because people can speak several languages or hold two jobs. c231-054 asks about a town that never appears in the setup and assumes the person has one home.
- **Vocabulary mapping**: "town" means lives-in, "language" means speaks, and "work" and "workplace" questions expect the company name.
- **First names only**: some questions refer to people by first name only. Within an item, each first name belongs to just one person.
- **Lures**: several items include a tempting wrong answer, such as the first person's own town, workplace or spouse, a parallel chain through a different relation, or a near-identical name. Trap c231-070 uses a company named after a town ("Sunderhollow Mills") to tempt a lives-in answer.
- **Unknown person**: c231-067 names a person who is never mentioned. c231-068 asks for a relation (cousin) that was never stored for a known person.
- New relation words appear only in chains (son, landlord, dentist, coach, mentor).
