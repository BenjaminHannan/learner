# Why B2's C1 tries break the rules, and a fix to try (2026-10-06)

Thread "Ultracode: creative rules blocker". Answers the coordinator's two questions: (a) why only about a quarter of B2's tries follow the rules when the value-blind follower manages 58%, and (b) why variety sits near 4.4 legal programs per puzzle against the follower's 18.7.
DEV only (128 puzzles, 32 kept tries, first-step branching on unless said). Nothing sealed was read. Warmed parents were re-made here on CPU with the pilot's own recipe and skills replay (data rebuilt here, hashes match). They reproduce the Mac exactly: 1,500 rung on s100 gives rules share 0.289 / luck 4.67% / reach@4 0.161 (Mac pilot 0.291 / 4.69% / 0.160); the 6,000 rung gives greedy rules 0.367, hit 13.3% (Mac diagnose: the same to 3 places).
New files only (nothing the Mac's pilot 2 uses was changed). Code: `creative/legal.py` (masked sampler), `creative/legal_probe.py` (this probe), `creative/tests/test_legal.py`, on branch `claude/project-thread-4aqhtv`. Numbers: `creative/results/legal-probe/`.

## Plain summary for Ben
B2 solves these puzzles in two steps, like "3 x 5 = 15, then 15 + 7 = 22". Its mistake is almost always the same one: in the second step it grabs a number it already used in the first step. It does that because nothing in B2 marks a number as used. After a step, B2 sees the new result, but every starting number still looks fresh. So it has to remember on its own, and when the first step was picked by chance (which is what searching does), it remembers wrong.
The fix we tested is a "used numbers are greyed out" rule while B2 makes its tries. B2 still picks every step itself; it just can't pick a number that's gone. That makes every try legal, nearly triples how often it hits the target, and lets the extra tries become new ideas instead of illegal ones.

## (a) Why most tries break the rules
**Shown.** The broken rule is "each number once", and nearly always one way. First rule break in the order B2 writes it, s100, 1,500 rung, T 0.21, kept tries:

| first break | share of all tries |
|---|---|
| step 2 reads a number step 1 already used | 51% |
| step 1 reads the same number twice | 16% |
| step 2 reads the same slot twice | 3% |
| inexact division | 1.4% |
| a constant, the target, or a wrong op | 0% |

The 6,000 rung and T 0.7 / 2.0 look the same (step 2 re-read 46-51%, step 1 same number 16-19%). Constants, the target and wrong ops show up only on the raw, unwarmed parent and at T 2.0 (about 3% together).

**Shown: it is B2's own choice, not the sampler.** The greedy first try follows the rules only 39% of the time (1,500 rung); its first break is a used number at step 2 in 51%. When step 1 is forced to ADD of the first two numbers (or the first and third), greedy step 2 reads a used number 82-84% of the time and the fresh number only 15-16% (6,000 rung, no replay; `forced_step1_probe.py`).

**Suggested, not measured directly:** step 1 picking the same number twice (16%) comes from the two pointer heads being sampled independently. For + and x the training loss accepts either operand order, so both heads learn to like both numbers.

**Shown, from the code** (`custom_io/models/ledger.py`, `run`; `creative/sampler.py`, `sample_run`): a step writes its op and its result's value into a new result slot, but nothing records which slots it read. A given number's slot is the same before and after it is used. So at step 2 B2 can only guess from its own control state what step 1 meant to pick. When step 1 was sampled or forced by branching, what was picked often differs from what it meant, which fits legality falling at higher temperature and with branching (branching costs about 5 points).

**Shown: not the skills prior.** In the 200k skills rows B2 trained on, a later step reads a fresh prompt number 94% of the time; re-reading a used number happens only in `list_stats` (4.3% of multi-step programs). Only 3.4% of skills steps read a constant, and 0% of warmed tries do.

**Shown: why the follower looks better.** The follower can't reuse a number by construction. Its 42% illegal tries are all inexact division. So 58% vs 27% compares two different failures.

## The fix tested: a used-number mask while sampling
`creative/legal.py` copies the sampler's loop. B2's op and pointer heads are unchanged; each written step is drawn from them, restricted to steps the puzzle allows. Level 3: operands only from unused numbers and unused results, + - x / on the k-1 real steps, then stop, answer = the last result. Level 4 adds exact division. The mask never reads the target (tested: two prompts that differ only in target get identical masks), so it cannot aim. The value-blind follower is uniform sampling under the same rules, so the aim comparison stays fair. Both checkers still judge every try. Tested: level 4 tries always pass both checkers, at T 0.3-3, with and without branching, for 2-, 3- and 4-number puzzles.

s100, 1,500 rung (the recipe the roadmap chose), skills replay on:

| sampler | T | legal share | legal programs per puzzle | luck | reach@4 | reach@32 | first try hits | twin-target luck |
|---|---|---|---|---|---|---|---|---|
| plain (now) | 0.21 | 0.29 | 4.4 | 4.7% | 16% | 51% | 10.2% | 1.3% |
| used-number mask (L3) | 0.21 | 0.86 | 10.0 | 11.4% | 39% | 77% | 18.8% | 3.9% |
| + exact division (L4) | 0.21 | 1.00 | 10.5 | 13.1% | 42% | 77% | 18.8% | 4.4% |
| plain (now) | 0.7 | 0.27 | 5.7 | 3.5% | 13% | 50% | | |
| + exact division (L4) | 0.7 | 1.00 | 16.2 | 10.3% | 35% | 89% | | 5.3% |
| value-blind follower | | 0.58 | 18.7 | 2.4% | 9.1% | 51% | | |

6,000 rung, T 0.21: plain 0.27 legal, 4.1 programs, luck 5.9%, reach@4 22%, first try 13.3%; L4 1.00, 10.2, 14.4%, 47%, first try 26.6%, twin 5.3%.


| s101, 1,500 rung | T | legal share | legal programs per puzzle | luck | reach@4 | reach@32 | first try hits | twin-target luck |
|---|---|---|---|---|---|---|---|---|
| plain (now) | 0.21 | 0.29 | 4.3 | 4.6% | 16% | 51% | 8.6% | 1.6% |
| + exact division (L4) | 0.21 | 1.00 | 10.6 | 13.4% | 42% | 74% | 20.3% | 4.1% |
| plain (now) | 0.7 | 0.27 | 5.6 | 3.9% | 14% | 57% | | |
| + exact division (L4) | 0.7 | 1.00 | 15.3 | 11.0% | 37% | 87% | | 5.4% |

The plain s101 row matches the Mac pilot's rung 1 (0.285 / 4.3 / 4.64% / 0.161). The first-break mix is the same as s100 (step 2 re-read 49%, step 1 same number 17%).

**Aim survives (shown on s100 and s101).** Under the mask, own luck is 13.1% against 4.4% when the tries are made for the twin target (2.9x; plain sampler 3.7x); s101 13.4% vs 4.1% (3.2x). The twin luck sits at the follower's luck among legal tries (2.4% / 0.58 = 4.1%), so the mask itself makes no hits.

## (b) Why variety is low
**Shown: the same cause.** At a warmer temperature the plain sampler spends its extra tries on illegal programs, so legal variety stays near 4-6 at every temperature. With the mask the extra tries become other legal programs: 16.2 at T 0.7 (s100, 1,500 rung), 15.3 (s101), 16.9 at T 1.0 (6,000 rung, no replay), against the follower's 18.7, while luck stays 4-5x the follower's.

## Proposal for the roadmap thread (one change)
Use the level-4 mask as C1's try sampler for every arm, the first try and the temperature choice. Gates, marks, both checkers and the sleep recipe stay as they are. Keep reporting the plain sampler's legal share beside it, as a B2 measure.
- Pass marks, written before I saw any s101 number (DEV, s100 and s101, 1,500 rung; the roadmap thread may keep or change them before any arm runs): masked luck >= 1.5x plain luck on both parents; masked own luck >= 2x masked twin-target luck; >= 8 legal programs per puzzle.
- What would prove it wrong: masked twin-target luck rising as much as own luck (the mask, not B2, would be making the hits), or masked luck below 2x the follower's.
- Status: s100 meets all three (shown). s101, checked after these marks were written: luck 13.4% vs 4.6% plain (2.9x), own vs twin 13.4% vs 4.1% (3.2x), 10.6 legal programs; all three pass (shown). Both at T 0.21; the temperature choice under the mask has not been run.

**Untested, for later (owned by the B2 thread, not needed for C1):** let B2 learn the bookkeeping itself by feeding back which slots each step read (a "used" mark on workspace slots, started at zero so the parent is unchanged). A mask needs the task's rules written down; C2's program rules are different, so C2 would need its own mask or this learned mark.

Outside opinion: if you want one on mask-versus-learn before deciding, I can write a GPT prompt.
