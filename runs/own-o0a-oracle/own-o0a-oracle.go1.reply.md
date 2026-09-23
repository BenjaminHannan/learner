Building your oracle-coverage check — 300 dev turns to test the write rules.
Plan and relation table reviewed (153 relations). Now executing: step 1 (dev turns first, no rule code yet).
300 turns written. Validating counts and gold integrity before sealing.
Data validated: 300 turns, 272 ASSERT/CORRECT/DENY facts, 76 no-save facts. Sealing data now (never to be edited after).
Sealing code + marks + data before the run, then running once.
67.6% — below the bar as predicted. Verifying the reason breakdown in detail for the report.
Seal intact (4/4 OK). Writing RESULTS.md and appending ledger lines.
**Verdict: Pown0a.1 FAIL — 184/272 = 67.6%, below the 85% bar. The strict v0 write rules are proven wrong: even a perfect reader can't reach the recall target under them.**

Marks table (integer counts):

| Mark | Bar | Got | Result |
|---|---|---|---|
| Pown0a.1 auto-writable, WE not allowed | ≥ 85% | 184/272 = 67.6% | FAIL |
| Pown0a.2 auto-writable, WE allowed | report only | 193/272 = 71.0% | report |
| Pown0a.3 no-save-mode facts writable | = 0 | 0/76 | PASS |

What was done (in order, no deviations): wrote 300 dev turns + hand gold first (180 statement / 80 no-save / 40 mixed; 272 ASSERT/CORRECT/DENY facts, 76 no-save-mode facts; fictional names only), sealed them (SEAL-data.sha256.txt), then wrote PASSMARKS.md + scripts/claude_own_o0a_compiler.py, sealed all 4 (SEAL.sha256.txt, verified 4/4 OK after the run), ran the compiler once (CPU only, no model/downloads), wrote RESULTS.md, appended Pown0a.1–3 + OUTCOME to the ledger. No TEST panel or panel folder opened, no templates copied, additive only.

Every miss (88 non-writable, WE not allowed): 58 no-relation-cue (26 plural-list facts like "sisters", 18 verb facts like "lives in"/"works at", 8 bare possessives like "Mira's Pip", 3 copula ages like "is 34", 1 relation typo "broter", 2 bare-correction facts from "Fig, not Moss."); 12 OTHER relations (star sign, wifi password, shoe size…); 10 WE-owner; 5 typo'd values; 2 DENY facts whose old value isn't repeated ("no, my boss is Tal now"); 1 owner missing apostrophe ("toms"). Full per-fact list is in RESULTS.md.

What it means (plain high-school English): the write rules are a bouncer with a guest list. We gave him a perfect photo of every guest and he still turned away 1 in 3 real facts, because everyday wording ("sisters", "lives in", "Mira's Pip", typos) doesn't match the list's exact words. Better glasses (a smarter reader) can't fix a bouncer who rejects the right photo — the list itself must change before any GPU training. Even folding plurals (77.2%) or plurals + WE (80.5%) stays below 85% by arithmetic.

What it doesn't mean: it doesn't mean the ear design is bad or 85% recall is impossible — only that THESE exact rules cap recall at ~68%, so the rules (cue matching, OTHER relations, typo handling, bare corrections) must be loosened first.

PUSH: artifacts/claude-own-o0a-20260923 scripts/claude_own_o0a_compiler.py artifacts/fable-predictions-ledger.md
