# rsn-358k DRAFT for the Thread manager: can the loop reasoner learn to call a card store while it thinks? (sleep research thread, 2026-09-27 12:48:55 UTC; not sealed; no code yet; nothing run)

**Ben's ask** (TM thread cmsg_01FuvegZXjMmeUzStiEFVnEWVSkFy4otRUu9cBaNkZxpmT): 12:40:36 "was there a temporary card store that acts as a short term memory?", 12:41:48 "should we?", 12:45:39 "but for the reasoner to do work with it. It can call the cards".

**Brain first (a guess, not checked against papers in this session):** a person doing a lookup problem holds the question in working memory (prefrontal cortex) and uses it as a cue. The hippocampus completes the cue into the stored episode, and the answer comes back into working memory for the next step. A second cue built from the first answer gives a chain. The machine version: each loop round, the reasoner's state makes a query, the store returns the best-matching cards into the next round, and the next query can use what came back.

**What went wrong before (toys on made-up words, kept separate from the village model; design/research/2026-09-18-decisions-log.md:140-200, :330-358):** reading a supplied card was solved. Choosing among look-alike decoys was never learned from the answer loss (<= 182/512, below the question-blind 275). The measured cause: one softmax pool per card put 70-98% of its weight on one or two tokens, so a card's key lost either the person or the relation. Hand-built address keys fixed choosing (503/467), but they are a stand-in and not allowed as the answer. Own retrieval was partial: 356/512 one-hop, 14/189 held-out two-hop, one seed.
**What is different here:** (1) the reasoner is the 358 loop, which already beats plain on sums and grids (358i3); (2) the query is remade every round from the loop state, so a second call can use the first card (chaining); (3) each card key is multi-head (4 heads, each its own attention pool over the card's tokens), so one head can match the name and another the place. That is a learned encoder choice, not an address rule. Whether it avoids the single-pool collapse is exactly what this tests.

## Task (code-made, fresh random worlds every item, fixed env: no kind label)
- **A world:** 12 names (drawn from 40 name tokens) and 4 places (from 8 place tokens). The store holds 16 cards, each one token row: `name place = d d` (a two-digit value) or, for chain cards, `name place -> name' place'` (a pointer to another card).
- **Look-alike decoys, built in:** every asked (name, place) has at least 2 cards with the same name and another place, and 2 with the same place and another name. A reader that matches only one field can be right at most 1 time in 3.
- **The puzzle input shows only the question**, never the answer. Kinds, in equal shares:
  - **Q1 one card:** `name place ?`. The answer is the card's two digits.
  - **Q2 two cards chained:** the asked card is a pointer; the answer is the value on the card it points to.
  - **Q3 two cards summed (report only):** `name1 place1 + name2 place2`. The answer is the 3-digit sum.
- Values, names and places are reshuffled in every world, so nothing can be memorised. The test worlds use sealed seeds that training never draws.

## Arms (one change: whether the store can be called)
- **store:** the 358 loop net (2 x d256 on CPU; the same code path as 358e's small nets, fixed env) plus the store parts: a card encoder (shared token embedding, 4 attention-pool heads into 64-d keys, and a value projection), a query projection from the loop state, and a NULL card. Each round: query, score all 16 cards, soft top-4 read, and the 4 read rows are added as extra rows the next round attends to.
- **no-store:** the identical net with identical weights; the store holds only the NULL card. **Weights are equal exactly, not just within 1%:** the store parts exist in both arms, and I will report their count.
- **Report only, not graded: cards-in-input.** The same net with the 16 cards pasted into the input as extra rows (full attention, no calls). It asks whether calling beats reading everything. At 16 cards, reading everything is cheap, so this arm may win. A store only earns its keep when the cards don't fit in the input; that is a later test.
- **No hand-written routing, address or key rule.** The only training signal is the answer loss (no retrieval labels). Training: 4 seeds per arm, same steps and data order.

## Marks (fresh test worlds, 300 items per kind, answer at the loop's own stop)
| mark | pass |
|---|---|
| V leak check | no-store is at most 15/300 on Q1 and on Q2 on every seed. The answers really need the cards. Otherwise INCONCLUSIVE. |
| G1 choosing | store, mean over 4 seeds: Q1 >= 240/300, AND >= 200/300 on at least 3 of 4 seeds. 200 is double the one-field ceiling (100/300). |
| G2 chaining | store, mean over 4 seeds: Q2 >= 150/300, AND >= 100/300 on at least 3 of 4 seeds. |
| G3 uses the rounds | on Q2, store right with its own stop >= store right at a fixed 1 round + 50, mean over seeds. One call can't fetch a card it hasn't seen the pointer for. |

**PASS = V, G1, G2 and G3.** Anything else with V met is a FAIL, and it stays a FAIL.
**Proved wrong** (for "answer loss alone teaches the store's keys, at this size"): V met and the store's Q1 mean is <= 100/300, i.e. no better than matching one field.
**Report only:** Q3; cards-in-input on every kind; the attention weight each key head puts on the name vs the place token (the 09-18 collapse measure); which cards the top-4 read picks per round on Q2; torch version, minutes per run.

## Overlap with Sol's numbers task (reviews/gpt-sol-numbers-2026-09-27.md:38)
Sol's option is a scratchpad: the net writes and revises its own partial results inside the make-24 puzzle. Here the store is read-only and filled from outside (facts the puzzle input lacks), and the test is choosing among look-alikes and chaining two lookups. Different puzzle, folder (artifacts/claude-rsn358k-20260927) and machine. Seeds will avoid 5-16 (358i3, 358s, 358u).

## Cost and place
$0. CPU in this container: 12 runs of the small 2 x d256 net. Steps TBD from a dev pilot (not graded; a dev world seed only) that sets the step count before sealing. About 2-3 h per run, 4 at a time (estimate). BensPC later if needed.
**Predictions (before any code):** V 95%; PASS 30%; proved wrong 30%. Why low: the 09-18 toys never learned choosing from the answer loss alone, and the multi-head key is the only new defence.
**A PASS is a test result only.** Putting a card store into the build is an architecture change and needs Ben's yes.
