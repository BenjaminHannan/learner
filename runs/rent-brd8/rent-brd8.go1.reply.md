Starting brd-8 — fetching branches and checking gates.
Credit passes, but I see live rent-brd8 instances — checking for duplication.
No exact duplicate found — checking the other branch before renting.
Found a cheap 5090 — renting it now.
First rental stalled — destroying it and trying another host.
Second rental is running — streaming code and setting up.
Setup checks pass — launching the 35–50 minute run.
Run is active (CPU 99.9%) though logs pause during training — continuing to monitor.
Lost SSH contact — checking instance status.
Host can't restart — destroying the dead instance and weighing a final rental against the $1 budget.
Third rental is up — redeploying and relaunching.
Launch command hung (as before) — verifying the run started.
Final seed in progress, budget nearly exhausted — watching closely.
Run finished — copying results back.
Files secured locally — destroying the rental.
Run complete and instance destroyed — writing up results.
Verdict: NOT SHOWN for compounding; G7 MET (separate line).

Credit gate: 6.67843962726986

Run: registered brd-8 command completed unmodified on rental 3 (RTX 5090, KR). Base cov@30 108/240; ITER 143, 161, 166; CTRL 152, 152, 167. Per-seed ITER−CTRL: −9, +9, −1 (needed +12 each) — PASS fails. CI ITER−CTRL [−3.96, +3.33], not above 0. Upper bound 3.33% = 8 puzzles of 240, not below the 6-puzzle proved-wrong bar — so NOT SHOWN, not proved wrong. ITER−base: +35, +53, +58 (needed +24 each), CI [+14.66, +25.65] — G7 MET. Round-1 wins 165; ITER round-2 wins 200/215/185 vs CTRL 171 every seed — question posed, not inconclusive. Script wall 31.2 min; model commit 87179e5c1f455ef22e6223592d2d61351b525bfc.

Integer counts: rentals 3 (max 3), files copied back 4, test puzzles 240, seeds 3, practice puzzles 800 (400+400), example passes each arm 1107, live rent-brd8 instances remaining 0.

Deviations (5): (1) strict DUPLICATE gate was clear (no exact rent-brd8 label, no gpu artifacts on either branch), but 3 live rent-brd8-s0/s1/s2 instances were running an unregistered script (claude_brd8_week.py, absent from origin/main) — proceeded with the registered script; (2) rental 1 (52750932) stuck in loading past the 6-min rule, destroyed, $0; (3) rental 2 (52752114) host died mid-seed-1 (exited/stopped, restart unavailable) — partial output discarded, full registered command rerun on rental 3, code never edited; (4) run log copied back as gpu/log.txt per repo convention; (5) spend is estimated dph×hours: ~$0.05 + ~$0.47 + ~$0.36 ≈ $0.88 of $1.00 — under budget, $0.90 kill never triggered.

Pushed (staged for watcher): artifacts/claude-brd8-20260926/gpu/{brd8_summary.json, streams.json, practice.json, log.txt}, artifacts/claude-brd8-20260926/RESULTS-gpu.md, ledger line appended. Instance destroyed and confirmed gone.
