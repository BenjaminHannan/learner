# 0.2d gates, ADDENDUM-29: build draft, D0 grid data, "I don't know" slot. Written 2026-09-26 18:57 UTC, before any seal or run

1. **Build draft.** scripts/claude_e2e02d.py (b5740b64d, log copy 260da42b7) is the ADDENDUM-24 path, nothing else. Its slots
   (reader sha, 358b3 checkpoint, sleep adapter, doubt) stay empty until H-A, H-B and H-R each have a verified PASS
   (ADDENDUM-18), and the build refuses to run a grid turn or a sleep adapter while they are empty. CPU selftest 17 of 17.
   Disclosed plumbing in it: one value per owner and relation with the newest winning (0.2c's notebook rule), the date
   line read by ep-382's date pattern, and one fixed sentence that hands the reasoner's checked square (or "could not
   find one") to the talker. The talker writes every reply.
2. **D0 grid turns.** The DEV chat bank has no number squares, so D0.5 runs on a DEV grid bank made by 358b3's
   generator with DEV seed 47201 (4 per size 5, 6, 7; 12 items; read_latin reads all 12). Seed 47201 is no TEST seed and
   shares no generator seed with row A (47311), the demo (47399), 358b2 or the rival smoke. Counter:
   scripts/claude_e2e02d_d0.py (selftest 5 of 5). D0.6 is counted in the H-B recipe's own sleep run.
3. **"I don't know" slot, changed from ADDENDUM-24.** If y1t has no verified PASS, 0.2d runs with **no** doubt step,
   not y1g's agreement check. Reasons, both checked: y1g's check needs a hand-written "is this a memory question" gate
   on every turn (a rule route, which the Redirect stops), and on DEV it cut right answers from 26 to 10 of 56
   (artifacts/claude-y1g-20260926/VERIFY-y1g.md). S1/H3 are then reported, not claimed, as ADDENDUM-24 already says.
   If y1t passes, its trained doubt fills the slot. No bar changes.
