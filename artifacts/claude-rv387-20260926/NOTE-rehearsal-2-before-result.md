# rv-387: second rehearsal, the fallback trigger (written 2026-09-26 15:44 UTC by date -u, before any 358i result)

Additive note. Same tiny trial net and the same 60 fresh 7x7 grids (seed 77101) as NOTE-rehearsal-before-result.md.
Fallback tried: going back on a time slice (after a guess, W rounds; if the checker has not accepted the grid, restore
the snapshot and try the next candidate; up to 3 guesses deep at 480 rounds, 1 at 48). Script (unregistered):
thread scratchpad slice/slice.py.
- 48 rounds: KEEP 28, time-slice 27 of 60.
- 480 rounds: KEEP 33; time-slice with W = 16: 32; with W = 32: 34.
- Also from the first rehearsal: the net's top symbol at the chosen cell was right in 32 of 47 guesses, yet writing a
  right symbol rarely led to a solve.
Reading (suggested, tiny net only): on this net, guessing one cell and going back does not add solves, with either
trigger; thinking longer does a little (KEEP 28 at 48 rounds -> 33 at 480). If 358i's nets behave the same, rv-387 will
not pass, and rv-390's headline will rest on KEEP-480 and RESTART, not on BACK. The time-slice trigger is not
registered anywhere and will not be unless 358i's results suggest it.
