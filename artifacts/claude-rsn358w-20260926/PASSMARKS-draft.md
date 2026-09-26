# rsn-358w DRAFT: carry-over on text games (sleep research thread, 2026-09-26 16:00 UTC; not sealed, nothing runs)

Ben 15:55 UTC (cmsg_01FuvegZXjMmeUzStiEFVnEW2Gc1fFtFXhSD8xGuRj93XR): "What if we gave the model text based games to train on?"
This is ranked next after 358x. It uses the same measure as 358x (Ben 15:42, the driving example): how many examples a new kind takes to learn after practising other kinds.

## Games (built: scripts/claude_textgames.py, selftest passes)
The games are code-made, seeded, and use fictional names only. No outside game sets and no downloads.

| kind | what the player does | shortest plan, levels 1 / 2 / 3 (mean) |
|---|---|---|
| keys | Walk rooms and passages, pick up coloured keys, open matching doors, reach the goal room. | 4.8 / 6.2 / 7.2 |
| recipes | Combine items by rules "A + B -> C" (which uses up A and B) to end holding the goal item. | 4.5 / 6.1 / 7.5 |
| switches | Press switches that each flip a fixed set of lamps until the goal pattern shows. | 2.4 / 3.5 / 4.5 |

- Every game has an exact simulator, a unique canonical shortest plan (breadth-first search in a fixed action order), and a checker. The checker accepts any valid plan and reports separately whether it is shortest.
- Two forms per game: `text` (a chat prompt, one action per line in the reply) for the 1B later, and `state` for the small nets.
- **Still to build before sealing:** the small nets' token-grid encoding of `state` and of the plan, as fact rows and answer rows over one shared symbol set for all kinds.

## Proposed test (the same shape as 358x v2)
- **Practice:** loop and plain nets (358i sizes, ~6.3M each, 4 seeds) practise keys and recipes at levels 1-2 for 60,000 steps.
- **Held-out kind:** switches, fixed now, because its logic (flip parity) is the most unlike the practised kinds.
- **Arms on switches:**
  - pre (the practised net), for loop and for plain;
  - fresh (random weights), for loop and for plain;
  - all at 4,000 steps, checked at 0 / 125 / 250 / 500 / 750 / 1000 / 1500 / 2000 / 3000 / 4000 steps.
- **Bar:** 150 of 200 fresh level-2 switch games solved with a shortest plan.
- **Primary:** steps-to-bar.
  - X1: loop-pre reaches the bar in <= 0.75x loop-fresh's steps, and faster on >= 3 of 4 seeds.
  - X2: loop-pre reaches the bar in <= 0.75x plain-pre's steps, and faster on >= 3 of 4 seeds.
  - Proved wrong: loop-pre's mean steps are at or above plain-pre's.
- **Report only:** cold solving at 0 steps; level-3 games; the other two held-out rotations, if budget allows.
- **Public game sets** may only ever be benchmarks, never trained on.

## Cost (estimate, before the Director's figure)
One rental: 8 practice trainings like 358i (~80 min), then 16 short carry runs like 358x (~20 min), plus setup. That is about 2 h at ~$0.49/hr, so ~$1.00, with a cap of $1.40. All of it is over the thread's $2, so it needs Ben's yes.

## Predictions (to be fixed at sealing)
- X1 about 40%.
- X2 about 20%, in line with 358x.
