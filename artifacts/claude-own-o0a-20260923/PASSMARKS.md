# own-O0a ORACLE-COVERAGE CHECK — pass marks (sealed before the run)

Question: if the reader were PERFECT (oracle gold frames), how many real facts in
ordinary chat would the planned v0 write rules (plan §4.1) let through automatically?
If under 85%, no training can reach the 85% recall target under these rules.

Data (sealed first, never edited after):
- `artifacts/claude-own-o0a-20260923/turns.jsonl` — 300 hand-written dev turns
  (180 statement, 80 no-save, 40 mixed), fictional names only.
- `artifacts/claude-own-o0a-20260923/gold.jsonl` — hand-written oracle frames.
- Seal: `SEAL-data.sha256.txt`. Totals fixed at seal time: 272 gold facts in
  ASSERT/CORRECT/DENY mode, 76 gold facts in no-save modes
  (ASK/CHECK/SUPPOSE/PLAN/REPORTED).

Compiler: `scripts/claude_own_o0a_compiler.py` (v0 write compiler of plan §4.1,
fed oracle readings). A gold fact is AUTO-WRITABLE only if ALL hold:
1. mode is ASSERT, CORRECT or DENY;
2. owner is ME, or a whole-word span of the turn equal to the gold owner string
   (case-insensitive; the `'s` possessive splits off in tokenisation);
3. value is a whole-word span of the turn equal to the gold value string
   (typo'd values are NOT writable automatically);
4. relation is in relation table v2 (not OTHER) and some whole-word span of the
   turn is one of that relation's names or aliases (the relation cue; strict
   exact-word match, case-insensitive — plurals such as "sisters" do NOT match
   "sister", verb paraphrases such as "lives in" do NOT match "city");
5. WE owners are counted both ways: WE->ME allowed, and WE->ME not allowed.

## Marks (fixed now, before the run)

- **Pown0a.1**: auto-writable share of the 272 ASSERT/CORRECT/DENY gold facts with
  WE NOT allowed is **>= 85%**. This is the bar for the strict rules.
- **Pown0a.2**: same share with WE allowed (report only, no bar).
- **Pown0a.3**: writable count among the 76 no-save-mode gold facts is **= 0**
  (must be 0 by construction: the mode gate).

## Predicted outcome (registered before the run)

Everyday wording keeps facts out of the strict compiler's reach: verb
paraphrases with no table cue ("lives in", "works at"), plural cues ("sisters"),
typo'd values, OTHER relations (star sign, wifi password, ...), possessives with
no relation word ("Mira's Pip"), old values dropped in corrections, and WE
subjects. Expected auto-writable with WE not allowed is roughly 65–75%, i.e.
**Pown0a.1 FAILS below 85%**, which is the result that proves the strict rules
wrong: no ear training can recover facts the writer refuses on principle.

Run: `uv run --offline --no-project --python 3.12 --with torch --with numpy
python -B scripts/claude_own_o0a_compiler.py` (CPU only, no model, no downloads).
Output: `artifacts/claude-own-o0a-20260923/RESULTS.md` + counts to the ledger.
