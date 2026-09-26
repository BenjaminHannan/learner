# g406 ADDENDUM-4: the resume will not run; g406-2 replaces it (written 2026-09-26, committed 23:45 UTC by date -u)

The resume (handoff/held/claude-madeup-g406r-mac.md, ADDENDUM-3) was held until the reading thread's opencode
diagnosis. That diagnosis (lis-320 ADDENDUM-6) found that opencode's default reasoning effort makes a call take
88-460 s. With `--variant low`, calls took 5-15 s, and pilot 4 made 60 calls with 0 failures. The resume used the
default effort, so it would likely repeat run 1's failures. Changing the call is a change to the marker, so under
ADDENDUM-3's rule it becomes a new gate: g406-2 (artifacts/claude-g406-2-20260926/PASSMARKS.md). Its only change is
reasoning effort low. It is joined by g406b, the two-session check this gate's PASSMARKS already named, on mu-405b's
240 judged packets.

g406 itself stays INCONCLUSIVE on the route (VERIFY-run1.md). Its 80 rows are not merged into g406-2. The held resume
file stays in handoff/held/ and is not moved to the queue.
