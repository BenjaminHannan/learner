# Exp 189 RESULTS — say-again verbatim repeats on loop138g (Muse)

**Result: PASS (in the open).** The repeat-request layer echoes the agent's
previous reply word-for-word on 13/13 repeat turns, answers the fixed line
on 3/3 no-previous turns, leaves all 10 Say/repeat traps and 12 teach/ask
turns byte-identical to loop138g, and moves nothing on any frozen suite
(0 moves, 0 new wrong, 0 new writes everywhere).

## Post-seal driver edit (reported, not hidden)

`shasum -a 256 -c` on the sealed set: PASSMARKS.md OK, agent OK,
cases189.json OK, loop189-config.json OK, **driver
`scripts/fable_fix189_sayagain.py` FAILED** (edited 09:54:16, after the
09:51:52 seal; the previous session died 09:54 in an opencode database
lock, unrelated to this code). Agent, config and cases189.json were NOT
changed (agent sha still `7a77d798…`; director's condition met).

What the driver change does: it fixes the R1 trap/base comparison to use
a **triple snapshot** — reply AND stored triples AND facts AND
events.jsonl lines, each taken AFTER both loops have turned. The sealed
driver compared the post-189 snapshot against the PRE-base snapshot, so
every turn that writes (4 teaches: S04, S16, S25, S26) FAILED despite
byte-identical replies (sealed r1 file: 34/38). Current comparison code
(lines 96–102 of the driver):

```python
else:  # trap / base turns: byte-identical to loop138g
    ok = (r9 == rb and e9["triples"] == eb["triples"]
          and e9["events"] == eb["events"]
          and e9["facts"] == eb["facts"])
```

where `eb = _snap(base)` is taken after `base.turn(turn)` and `e9`
after `agent.turn(turn)` (lines 82–86). Repeat/noprev checks
(`s9_after == s9`) are unchanged. All marks below were re-run in the
open on the final code; nothing was re-run silently (one open R1 run,
one open run per R2 suite).

## Marks (all re-run in the open, final code)

| mark | n | result |
|---|---|---|
| R1 sealed 38-turn session | 38 | 38/38 OK (noprev 3/3, repeat 13/13, trap 10/10, base 12/12), 1.4 s |
| R2 junk: redteam136 | 145 | 0 moves, 0 new wrong (OK 136, WRONG-WRITE 6, MISSED 3 — as sealed) |
| R2 junk: cases150 | 57 | 0 moves |
| R2 junk: f1 | 46 | 0 moves |
| R2 junk: cases139b | 101 | 0 moves |
| R2 redteam143 | 124 | 0 moves (OK 107, MISSED 7, WRONG-ANSWER 10 — as sealed) |
| R2 sessions152 | 180 turns | 0 moves, 0 new wrong, 0 new writes |
| R2 bench121 ×4 splits | 800 | 0 moves, 0 new wrong (194/198/150/196 correct), 29.5 s |
| R2 marks123 (stock runner) | 10 suites | per-case scrubbed-identical all 7 reports; suite statuses identical (incl. inherited p3-l5z1 FAIL and overall FAIL, same as base); only metadata diffs: agent/config paths, seconds, sleep SKIP agent filename. 259.1 s |

R1 detail: "Say that again." echoes instead of taking the Say-pretend
path (repeat wins); "Repeat after me: Lee is kind." and "Again, Kim's
boss is Lee." stay base-identical; a repeated "Saved:" echo writes
nothing (events.jsonl lines identical before/after). Nearest frozen
trap "Sorry, I meant Mira's pet is Rex." never matches (whole-turn
only), as predicted.

G4: slowest registered invocation 259.1 s < 1500 s; OMP/MKL threads = 1;
daemon wrappers use idle_seconds=3600.0. Fictional names only.

## Reproduce (one suite at a time, from the repo root)

```sh
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
uv run --offline --no-project --python 3.12 --with torch --with numpy \
  python -B scripts/fable_fix189_sayagain.py --only r1|junk|rt143|sessions|bench|marks123
```

## Deviations

1. Post-seal driver edit (above): reported, comparison code shown, all
   marks re-run in the open. No rule changes; agent/config/cases sealed
   and untouched.
2. The sealed 34/38 r1 file was overwritten by the open 38/38 re-run
   (same path); the 34/38 is preserved in this note, not in a file.

Questions for Ben: none.

What it means: asking the agent to repeat itself now echoes exactly
what it just said, never saving or re-doing anything.
What it does not mean: the agent still cannot translate, rephrase, or
obey new "Say X" orders — those stay pretend, exactly as before.
