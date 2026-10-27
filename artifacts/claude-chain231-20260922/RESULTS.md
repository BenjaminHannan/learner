# Exp 231 -- possessive chains inside table questions (read-only, taught facts only)

## Verdict: FAIL (registered). M1a, M1c and M1d fail. M1b, M1e, M2, M3, M4 and M5 pass.

The main problem is that most of the blind panel could not be taught to the base.
- **58 of 72 panel items are BLOCKED.** On 221 (and 138i), at least one setup sentence did not
  save:
  - 83 failed setup turns are verb teaches with a two-word subject ("Gideon Pelk lives in
    Tarrowby."). This is the base limitation that experiment 232 is fixing.
  - One is "My coach is Gunnar Treece.", which the base did not understand.
- **Only 14 items are answerable.** On those, 231 scores 7 right against 221's 4.
- **The M1a failure is a scorer flag, not a false value.** It is item c231-013, a blocked item,
  where all three arms give the same true reply (details under M1).

Build: loop231 = loop221 + Chain231Mixin outermost (scripts/claude_loop231_agent.py).
Design note: design/v3/30-modes/231-chain-opus.md.

Order:
1. PASSMARKS, code, config, dev cases, scorer, predictions and the base221 row copies were sealed
   at 15:35 (SEAL.sha256.txt, 15 files).
2. Only after that was the panel opened. Its seal was verified (panel.jsonl: OK).
3. Each arm was run once on the panel. All 15 sealed files still verify after the runs.
4. The panel field names matched load_items() as written, so no field-map change was needed.

All runs used Mac CPU with OMP/MKL=1, one at a time, with the 1-minute load under 60 at each start.

## Marks

| mark | bar | result | pass? |
|---|---|---|---|
| M1a WRONG for 231, all 72 items | 0 | **1** (c231-013; identical on 138i and 221) | **FAIL** |
| M1b question writes, 231, all items | 0 | 0 of 72 (138i 0, 221 0) | pass |
| M1c answerable: 231 right >= 221 right + 20 | >= 24 | **7 vs 4 (+3)** | **FAIL** |
| M1d answerable answer + yes/no items: 231 right | >= 85 % | **7 of 14 = 50 %** | **FAIL** |
| M1e items right on 221 but not on 231 | 0 | 0 | pass |
| M2a dev answerable: 231 right | >= 90 % | 54 of 54 (221: 26 of 54) | pass |
| M2b dev answerable abstain items (traps) | 100 % | 15 of 15 | pass |
| M2c dev WRONG / question writes | 0 / 0 | 0 / 0 | pass |
| M3a suitediff218 vs 221 rows: new WRONG / WRONG-WRITE / junk / lost OK | 0 | 0 / 0 / 0 / 0; GATE clean on all four suites | pass |
| M3b moves not in predicted_moves231.json | 0 | 0 (4 moves, all predicted) | pass |
| M4 sleep smoke | 221 marks, < 300 s | sleeps 1, installed 1 (20 episodes), probes 5/5, wrong 0, broken = abstain, taught 50/50, overwrote 0, 98.6 s | pass |
| M5 median (231 ms - 221 ms) per panel question | <= +10 ms | -1.89 ms (p90 +1.55) | pass |

Whole-panel totals (72 items, 9 of them abstain items):

| arm | RIGHT | WRONG | ABSTAIN | OTHER |
|---|---|---|---|---|
| 138i | 13 | 1 | 58 | 0 |
| 221 | 13 | 1 | 58 | 0 |
| 231 | 16 | 1 | 55 | 0 |

Right answers by family on 231 (221 in brackets), out of 9 each:

| family | 231 | (221) |
|---|---|---|
| verb_2hop | 0 | (0) |
| possessive_2hop | 3 | (3) |
| of_form | 1 | (0) |
| three_hop | 0 | (0) |
| user_chain | 1 | (1) |
| yes_no_chain | 2 | (0) |
| casual | 0 | (0) |
| traps | 9 | (9) |

Every case with all three grades and the 231 reply is in panel/cases.md. Blocked items are marked
there. Full rows, including setup replies and which setup turns saved, are in panel/rows-*.jsonl.

## M1 details
- **The M1a item: c231-013** "What is Bram Tolliver's coach's language?"
  - Blocked: "Sunniva Rask speaks Kettish." did not save.
  - Reply, the same on 138i, 221 and 231, from the base's own "fake" stage (not the 231 stage):
    "Bram Tolliver's coach is Sunniva Rask, which is not someone I can look up."
  - The sealed scorer calls this WRONG. The reply names a stored value that is not on a path to the
    gold, because the gold fact was never stored, and "not someone I can look up" is not in the
    abstain word list.
  - By hand, the reply is true and makes no false claim. The registered mark still counts it, and
    I am not overriding it.
- **The 14 answerable items:**
  - 3 moved to RIGHT:
    - c231-025 "Who is the brother of the wife of Soren Achebe?" -> "Soren Achebe's wife is Liesl
      Harrow, and Liesl Harrow's brother is Evander Harrow."
    - c231-051 -> "Yes. Barnaby Keel's sister is Petronella Keel, and Petronella Keel's husband is
      Lorcan Abernathy."
    - c231-052 -> "No. Seraphine Otto's boss is Wendel Grise, and Wendel Grise's wife is Maud
      Grise."
  - 4 were already RIGHT on 221 and stay RIGHT (012, 016, 018, 038). The base answers them itself.
  - 7 misses:
    - 6 ask about a person by first name only, while the setup used the full name (011 Ysolde, 020
      Ruben, 023 Benedek, 031 Taddeo, 034 Oriana, 061 alaric). The notebook does not resolve a
      first name to a full name. The 231 stage honestly replies "I don't know anyone called
      Ysolde." (138i and 221 gave the long refusal.)
    - 1 uses a "Who's" contraction that no table template has (044 "Who's the husband of my
      cousin?"). This is unchanged from 221.
- **Blocked items (58):** 25 of the 231 replies there are "..., but I don't know X's city/employer."
  The last fact did not save, so this is right to say.
  - None of the 231-stage replies asserts a false value.
  - The 9 traps are all blocked. All 9 abstain on all three arms, including both
    conflicting-town traps.
- **Panel reply changes, 221 -> 231: 38 items.**
  - 3 ABSTAIN -> RIGHT.
  - 27 ABSTAIN -> ABSTAIN. The long glued refusal becomes a targeted abstain that shows how far the
    chain got.
  - 8 RIGHT -> RIGHT (traps, now targeted abstains).
  - 0 moves toward WRONG.

## M3 moves (all rt143, all reply-only OK -> OK, all predicted)
- A1: "Bram Kite's country of citizenship is Norland, but I don't know Norland's official language."
- F6: "Moonchant's performer is Harborlight Choir, but I don't know Harborlight Choir's director."
- K8: "The Glass Orchard's author is Bram Kite, but I don't know Bram Kite's spouse."
- U1: "Bram Kite's spouse is Cora Lind, but I don't know Cora Lind's country of citizenship."

Hand verdict: all 4 are better. The long refusal becomes a true partial chain with an honest gap.
rt136, sessions152 and bench had 0 moves. The known bench flake did not appear.

## Unregistered probe (director note, after the registered runs; not part of any mark)
Files: probe-director-unregistered/ (probe231_director.py, replies.jsonl). It uses the sealed
runner's build() and a fresh notebook per case. Every setup sentence saved on all three arms.

| question (after teaching every fact) | 138i | 221 | 231 |
|---|---|---|---|
| (a) "Where does Kestrel's boss work?" | long refusal | long refusal | "Kestrel's boss is Orrin, and Orrin works for Palewick Mill." |
| (b) "What city does Fenn's boss's boss's boss live in?" | long refusal | long refusal | "Fenn's boss is Ada, Ada's boss is Brisk, Brisk's boss is Corvin, and Corvin lives in Hollowmere." |
| (b') "Where does Fenn's boss's boss's boss live?" | long refusal | long refusal | same 3-hop chain answer |

- 0 question writes on all arms.
- "boss" does reach the chain path. It is relation 24 in relation_table_v1, with storage key
  "boss". Either way, a hop is read as a stored relation key, so it works as long as the facts were
  taught with that word.
- One small wording point. The fact was taught as "works at", but the answer says "works for".
  That is because the last clause uses the employer relation's live teach template. The value is
  right.

## Deviations
1. **Answerable subset.** It was added to PASSMARKS before the seal, after the coordinator's
   232 note. Two-word-name dev cases were added at the same time (d231-049 to 055). d231-055 is
   blocked by design and abstains.
2. **base221/.** It holds byte-identical copies of 221's sealed suitediff rows, with rt136/rt143
   renamed so that the 218 tool finds them. The hashes are in SEAL, and the rt136 and rt143 copies
   match the originals.
3. **Declared in PASSMARKS.**
   - The chain-only filler tidy.
   - Yes/no rows are read for chain subjects.
   - Table v1 gaps are inherited ("language(s)" template; wife/husband not aliases of spouse).
   - The scorer allows intermediate chain entities.
4. **Pilot runs** (dev, suites, sleep smoke) were done before the seal in the scratchpad. The dev
   set was fixed twice before the seal, because my own cases had used forget and correction
   wordings the base does not act on.
5. **Sleep smoke root.** The notebook lives under sleepsmoke/s1-231 in this folder, as in 221.
   It is not the repo-root notebook.
6. **No srcguard228.** install_srcguard228() (scripts/claude_loop228_agent.py) became required for
   new experiments after 231 was sealed. loop231 does not install it. The seal was left as it is,
   per the coordinator's note.

## What it means
- The chain step works when the facts are actually in the notebook. On my own dev cases it
  answered every one. On the blind panel it answered every answerable item that did not depend on
  a first-name lookup or a missing template.
  - In those answers it shows its work in plain words, e.g. "Kim's boss is Lee, and Lee lives in
    Oslo."
  - It gave honest partial abstains everywhere else.
- It never wrote to the notebook on a question. It never made a new wrong answer on any suite. It
  kept every 221 right answer, and it did not slow questions down.
- The demo question now works. After "Kim's boss is Lee." and "Lee lives in Oslo.", "Where does
  Kim's boss live?" answers "Kim's boss is Lee, and Lee lives in Oslo."

## What it doesn't mean
- It does not show that 231 meets the panel bars. Only 14 of 72 blind items could even be set up,
  so the panel mostly measured the base's teaching gap (two-word names with "lives in / works at /
  speaks").
- It does not show how 231 does on the blocked 58 items once 232 lands. That needs a fresh
  registered run on a 232 base, not a re-score of this one.
- My dev score (54 of 54) is my own cases, written by the same person who wrote the code. It is
  evidence the code does what I meant, not independent evidence.
- First-name questions ("Where does Ysolde's boss live?" when she was taught as "Ysolde Marr")
  and "Who's ..." contractions are not handled.
