Building the 266b follow-up — reproducing the gap and testing the one-change fix.
I've got the design and prior results; now pulling the base implementation to build on.
Local copies check out against the sealed versions. Now mapping the multi-word gap to design the detector.
Base verified. Now probing which question forms the base answers for plain names, so the dev set only uses working forms.
Base forms confirmed. Writing the 49-dialog dev set in my own wording.
Dev set written. Now the three-arm scorer.
Gap reproduced cleanly: 26 multi-word dialogs MISS on both arms, controls behave. Building the 266b detector now.
Expected MRO difference from subclassing — fixing the assertion.
Detector selftest passes. Piloting all three arms on the 49 dev dialogs.
48/49 — one broken-chain wording to investigate before touching anything.
Dev pilot is 49/49. Writing the M2–M4 scorer and run driver.
All base rows present. Writing the run driver.
Load and disk OK. Starting the pilot run in background.
Suspiciously fast — checking for step failures.
Pilot is exactly as designed. Checking ledger format, then writing predictions + PASSMARKS.
Sealing now.
Sealed and registered. Running M2–M4 once into the registered run dir.
Run is gated on machine load as designed. Waiting for it to proceed.
Machine is busy (load 120+); the driver is correctly waiting. Polling.
Load cleared and the run is through M3a. Continuing to poll.
Registered M2–M4 all pass. Verifying details, then waiting for the blind panel.
Panel is up on first poll. Copying it unchanged.
Folder already present and byte-identical. Verifying its seal from the repo root.
Both seals OK. Reading panel docs and runner/scorer interfaces (never the items).
Scorer interfaces mapped. Writing the post-seal panel runner (mirrors each panel's `run_base.py`, prints no replies).
Load OK. Running the M1 panel once on the 266 arm.
266-arm reproduces 266's registered panel numbers exactly. Scoring the 266b arm.
M2 totals match prediction (+8). Verifying id-level moves.
M2 is exact. Final identity checks for M1 controls, then RESULTS.
All green except the known broken-chain bar. Writing counts-only JSONs and RESULTS.
One flag-neutral reply change found (052, other→other). Writing RESULTS.
**Verdict: FAIL** (M1 broken_chain 9/12 vs the 12/12 bar; all other bars pass). RESULTS.md is written. No panel item text or replies are quoted anywhere below — ids and counts only.

**Marks table (266's number beside every figure)**

| Mark | Bar | 266b (vs 266) |
|---|---|---|
| M1 multiword_chain | ≥22/24 | 24/24 (266: 6/24) PASS |
| M1 three_link | ≥7/8 | 8/8 (266: 3/8) PASS |
| M1 oneword_chain no-loss | no 266-RIGHT lost | 8/8 = same ids, replies byte-identical PASS |
| M1 broken_chain | 12/12 | 9/12 (266: 7/12) **FAIL** |
| M1 0 wrong / 0 writes | 0 / 0 | 0/70, 0/70; stored identical 70/70 rows PASS |
| M1 controls identical | 8/8 + 6/6 | 8/8 plain, 6/6 statement, identical PASS |
| M1 my_live (no bar) | reported | 4/4 = 4/4, identical |
| M2 chainpanel266 | 0 new wrong, moves only 8 cause-(b) ids | 8 moves exactly, 72/80 identical, 0 wrong, 0 writes PASS |
| M3 frozen vs 266 | moves = predicted | sessions152/bench/marks123 0; rt136 15 = C019–C031+C076+C079; direct []/145; exceptions 63/63; rt143 0/0 PASS |
| M3 probes (115 dialogs, 7 audits) | 0/0/0/0 | 0 changes, 0 ghosts, 0 dup fails, 0 writes PASS |
| M4 latency | ≤+5 ms | +0.005 ms (1.976 vs 1.971, 624 turns) PASS |

**Every move, every miss (ids only)**
- M1 lifted to RIGHT (25): 18 multiword (c266b-001–006, 013–024), 5 three-link (025, 026, 030, 031, 032), 2 broken (045, 047). Misses: broken c266b-046, 050, 052 stay other (052 reply changed 1 char, flags unchanged other→other). 0 wrong either arm.
- M2 moved OTHER→RIGHT (8, exactly predicted): c266-005, 008, 015, 031, 032, 033, 035, 036. All else identical.
- Dev (49 own dialogs, pre-seal): 26 MISS→RIGHT, 5 MISS→ABSTAIN, 4 untaught MISS on all arms, 14 identical, 0 writes.

**Diagnosis (one note):** the 12/12 bar is unreachable under the spec. Two of the three remaining others are the panel's untaught-head traps: falsifier #3 forbids lifting untaught heads, so 266b passes through by design, and the base answers that verb shape with "didn't understand," which the sealed scorer doesn't count as abstain. The third (one of 046/050/052) is a taught-head item with no counted abstain — lift refused or canonical clarified; passthrough, no guess, no write. 0 wrong / 0 writes on all 150 panel items both arms.

**Deviations:** D1 post-seal helper `scripts/claude_266b_panelrun.py` (new file, mirrors sealed run_base.py files, ids only; sealed files untouched, seal re-verified 21/21 OK). D2 chainpanel266's scorer hardcodes its rows path, so arms were scored by importing the sealed module unchanged with ROWS pointed at /tmp rows. D3 M2 266-arm run started at load 67 (above 60 gate); ~1-min light run, reproduces 266's numbers exactly. D4 panel rows in /tmp only; repo holds counts-only JSON.

**What it means:** two/three-word-headed chain questions now work (24/24, 8/8); one-word chains, my-chains and controls are byte-identical to 266; the 8 old-266 regression misses are fixed with nothing else moving; nothing ever guesses.

**What it doesn't mean:** it doesn't fix untaught-head broken chains (9/12, the FAIL above — honest non-answers, not guesses), doesn't add base-lacking forms, and proves nothing beyond these panels.

**Push set ready (not pushed, per no-push rule):** `artifacts/claude-chain266b-20260923` `scripts/claude_fix266b_detector.py` `scripts/claude_loop266b_agent.py` `scripts/claude_266b_*.py` `scripts/claude_266b_*.sh` `artifacts/fable-predictions-ledger.md` (P266b.1–6 appended).
