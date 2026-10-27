# Exp 154d RESULTS — grounded yes/no on loop138f (Muse)

Loop154d answers the director probe: after "Zuri's sister is Bela.",
"Is Bela Zuri's sister?" gets "Yes, Zuri's sister is Bela." and
"Is Ama Zuri's sister?" gets "Not that I know of. I have Bela as
Zuri's sister." All marks PASS with zero moves outside the sealed
predictions.

## Marks table (integer counts, every case reported)

| mark | bar | got |
|---|---|---|
| T1 sealed 38-turn dialogue | 38/38 OK, 0 wrong, 0 question writes | 38/38 OK (8 teach identical to 138f; 9 yes exact; 7 no-single exact; 4 multi exact, never "No"; 10 fall-through identical to 138f); 0 wrong; 0 writes on all 30 question turns |
| T2 marks123 per-case vs marks138f | identical, empty yes/no move set | identical in p2, p3 l1/l2/l3/l4/l5z1/l5z2, p4, q1, q4, bench, rt81, sleep, soak; l6 identical except timing-volatile replied_before_kill; rt110 one log-only flake (below) |
| G3 redteam136 | 135 OK / 7 WW / 3 MISSED, 0 moves, seven identical | same counts, 0 moves vs 138f, 0 new wrong vs 138b, seven C124/C127/C129/C142 identical |
| G3 cases150 | 57 OK, 0 moves | 57 OK, 0 moves |
| G3 f1 | 46 OK, 0 moves | 46 OK, 0 moves |
| G3 cases139b | 101 OK, 0 moves, seven identical | same, seven C10/C21 identical |
| G3 redteam143 | 107 OK / 7 MISSED / 10 WRONG-ANSWER, M3 identical to 138b | same counts, 0 moves vs 138f, M3 identical |
| G3 sessions152 | 165 OK / 15 UNHELPFUL, 0 new writes | same counts, 0 moves and 0 new writes vs 138f |
| G1 bench 4 splits | per-item identical to 138f, 0 new wrong vs 138b | identical (new_121 194/2/4, old_s2fresh 198/2/0, edit200 150/50/0, bench132 196/3/1); 0 new wrong |
| G4 time | each run < 1500 s | max 332.7 s (marks123, --workers 2); T1 1.4 s; suites ≤ 58.8 s |

## The one deviation (sealed F3 flake, resolved in the open)

Registered rt110 R5 msg_03: verdict, reply ("I already have that.") and
writes identical to the sealed 138f row; only the harness-observed
`statuses` metadata read `[]` instead of `['write']` (known mailbox race
class). Re-ran the rt110 suite once in the open
(`rt110-report-open-rerun.json`): byte-identical to the sealed 138f rows.
Both runs reported; no silent re-run.

Inherited labels (per-case identical to 138f, as sealed): p3 l5z1 FAIL
(turns 42/43 stale expectation, status_match 58/60), rt81 FAIL (59 ok /
15 unclear). No sealed file was edited after the seal (`shasum -c`
SEAL.sha256.txt: 7/7 OK after all runs).

## Reproduce (Mac CPU, offline)

```
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix154d_probe.py --out artifacts/fable-yesno154d-20260922/probe154d-loop154d.json
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_fix154d_suites.py --suite <name>
uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_marks123_all.py --agent scripts/fable_loop154d_agent.py --config artifacts/fable-yesno154d-20260922/loop154d-config.json --out artifacts/fable-yesno154d-20260922/marks154d --workers 2
```

## What it means

Yes/no questions over taught single-mention frames now answer honestly
from the notebook, with "No" restricted to single-valued relations.

## What it does not mean

It does not restore the old wh-run answering (of-forms, two-hop and
unknown frames still abstain exactly as on loop138f), and it teaches
nothing new.

## Questions for Ben

None.
