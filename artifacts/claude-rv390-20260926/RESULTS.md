# rv-390 results (thought-memory thread; written 2026-09-26 17:38 UTC by date -u)

Raw output: run/, copied from builder-outbox e4db701ba (rent-rv390, RTX 5090, runs 17:04-17:16 UTC). The builder's
push was blocked. These files reached main inside commit c3542bb56, whose message names only rv-388; the files are
byte-for-byte the builder's. Marks: PASSMARKS.md, sealed at 86a7ddfd1. The seal checked 15/15 on the rental. The nets
are 358i's loop-s1..s4, and their sha256 on the Mac, on the rental and in 358i's SEAL-run agree (run/SOURCES.txt). The
selftest matched rv-387's GUESS on 30 of 30 practice puzzles for every net. Blind recount: VERIFY-recount.md (agrees on every count and verdict; it also checked every saved answer against
the day puzzles without the net: givens kept, grids valid, answers equal the targets).

CAVEAT: 358i's loop nets were probably trained with a torch 2.8 bug that left most loop weights without a gradient
(Sleep research, 17:08 UTC: reproduced on CPU at 14dc0c013; the rental check is queued). Every count below comes from
possibly undertrained loop nets. Comparisons within a net stay fair. The rental ran torch 2.11 for inference: its
image had 2.2.1 with no 5090 kernels, so the builder upgraded the environment and left the code untouched.

SCOPE (added 17:47 UTC by date -u, at the Thread manager's 17:44 ask): every verdict below covers 358i's four loop
nets only. Getting stuck on a wrong answer may be a symptom of loop blocks that were barely trained, not of looping
itself. So "start fresh by default" is PROVISIONAL. rv-390 is rerun unchanged on the retrained rsn-358i2 nets
(ADDENDUM-358i2-rerun.md) before any default is set.

## Verdicts (hard grids7 puzzles: unfinished, and no round of the day's 48 accepted)

| seed | hard | KEEP | RESTART | GUESS | KEEP - RESTART | GUESS - KEEP |
|---|---|---|---|---|---|---|
| 1 | 183 | 5 | 17 | 24 | -12 | +19 |
| 2 | 223 | 1 | 18 | 34 | -17 | +33 |
| 3 | 177 | 11 | 24 | 32 | -13 | +21 |
| 4 | 275 | 0 | 17 | 14 | -17 | +14 |

- H (carrying on vs starting over): PROVED WRONG. KEEP solved no more than RESTART in 4 of 4 seeds; the mark needed 3.
  Carrying on for 480 rounds from where the day stopped solved 0 to 11 hard puzzles. Ten fresh 48-round starts from
  small noise solved 17 to 24.
- G (writing guesses while working): PASS. GUESS beat KEEP by 19, 33, 21 and 14; the mark needed 10 in 3 of 4 seeds.
- I (interruptible): PASS. In all 4 seeds:
  - with 5 pauses, each answering a message, KEEP's every round and all 40 GUESS results equal the run without pauses;
  - every message answer (175, 180, 180 and 180) equals the answer with no worker running;
  - the longest wait was 0.087, 0.089, 0.133 and 0.005 s, measured on the rental's GPU with 4 nets sharing it. The
    Mac and BensPC are untested.

## Report only
- GUESS vs RESTART on hard grids7: 24 vs 17, 34 vs 18, 32 vs 24, 14 vs 17, so 104 vs 76 in total. GUESS is ahead in
  3 of 4 seeds, and the two solve mostly different puzzles (blind recount).
- 51 of GUESS's 104 hard grids7 solves came within the first 48 rounds. So about half of its gain would come from
  writing guesses during the day's own 48 rounds, not from working between messages. Shown.
- KEEP solved 17 of 858 hard grids7 puzzles (2%) and 0 of 487 hard sums puzzles. Every KEEP solve of a hard puzzle came
  by round 149; rounds 150 to 480 added nothing. Shown (blind recount).
- Hard grids6 (hard 108, 141, 81, 226): KEEP 4, 3, 15, 0; RESTART 29, 13, 39, 22; GUESS 17, 69, 30, 52.
- Sums, the transfer row:
  - GUESS wrote 0 guesses on sums6 and sums8 in every seed, so the transfer row never acted and equals KEEP.
  - Why is untested: GUESS only writes when q < 0.5 at a check round and some open cell is below 0.99 sure.
  - KEEP solved 0 hard sums puzzles in every seed. RESTART solved 19 and 31, 11 and 22, 27 and 27, and 7 and 9 (sums6
    and sums8).
- Most of KEEP's grids7 solves came by round 48: 11 of 16, 7 of 8, 5 of 16 and 7 of 7. Those are the checker catching
  an answer the stop rule passed over.
- RESTART's sigma, picked on practice grids per net: 0.3, 0.3, 1.0, 0.3.
- Checked answers saved for Sleep research's night pool (run/rv390-sN.finds.jsonl, givens kept exactly): 323, 385,
  328, 225.
- Cost: the builder reports about $0.37 of the $0.90 cap, including 2 failed rentals. The Director's ledger has the
  booked figure.

## Predictions
- P390.1 (H not a PASS; KEEP ahead of RESTART in most seeds but by under 15): WRONG as written. There was no PASS,
  but KEEP was behind RESTART in every seed, not ahead.
- P390.2 (GUESS beats KEEP in at least 3 of 4 seeds): RIGHT (4 of 4).
- P390.3 (I passes): RIGHT.
- P390.4 (on sums, GUESS solves no more than KEEP in most seeds): right in count (equal in all 4), but only because
  GUESS never wrote a guess on sums. So the transfer question itself is untested.
- Seed 4 has the most unfinished grids: RIGHT (282 of 300 on grids7).

## What it means (plain words)
When this small loop net gets stuck, it stays stuck. Letting it keep thinking between messages almost never finishes
a hard puzzle. Starting it fresh a few times does better, and writing down its best guess and carrying on does better
still. The worker can stop for a message at any round and pick up exactly where it was, and a message waited at most
0.13 s. All of this is on possibly undertrained nets.

Brain first: this looks like fixation. In psychology, a person stuck on a wrong approach often stays stuck until
something breaks the set: a break (incubation) or a new cue. A fresh start from noise is like the break, and a
pencilled-in guess is like the new cue. This is suggested by textbook-level psychology; that the net follows it is
untested.

## Next (fixed before the result in NOTE-fallback-before-result.md)
- H proved wrong: the worker starts fresh by default, PROVISIONALLY, until the rerun on rsn-358i2 (see SCOPE). G
  passed: the worker writes guesses by default, also provisionally.
- So the next single change is RESTART + GUESS against RESTART: guesses written during each fresh 48-round start. It
  runs on a new day seed with the same hard-puzzle marks, on the retrained nets (rsn-358i2) if they exist.
- Going back is then built on top of that, with the trigger rv-391's measurement picks.

## CAVEAT 2 (added 19:04 UTC by date -u): how much the code parts solve alone
GUESS has hand-written parts. On grids, the guess candidates skip symbols already in the cell's row or column. An
unregistered control on PRACTICE grids only used an untrained loop net running this same GUESS worker for 480 rounds
(artifacts/claude-rv392-20260926/dev-untrained/). It solved 28 and 20 of 300 7x7 puzzles and 63 and 49 of 300 6x6
puzzles (init seeds 0 and 1), none within 48 rounds. KEEP has no such code part, so G (GUESS against KEEP) compares
"net plus the code's candidate filter" with "net alone". Part of G's margin (+14 to +33) may come from the code, not
the net. That is suggested; the puzzles differ. The rerun on rsn-358i2 adds an untrained-net row on the same puzzles
(artifacts/claude-rv392-20260926/ADDENDUM-1-untrained-net-control.md). Until it lands, G's PASS says only that
writing guesses with this code helps, not that the net learned to guess.
