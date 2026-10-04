# Round 6: report / ledger / receipt / spreadsheet practice, scored on a second independent layout set (2026-10-04, fast lane). Marks fixed before training

Base = round-5 TABV recipe (copy path + composed wording + extra table variety + contextual reader, real modules, fresh weights, 4 loops, 3000 x 16, seeds 0-5).
**One change: RLV = TABV's frames plus about 3,700 composed report / ledger / receipt / spreadsheet-style frames** (`gen_two_v.rl_extra`: audit/memo/incident openers with inflow-outflow clauses; ledger pages with brought-forward, credit/debit entries and carried-forward asks; CSV/pipe/cell sheets with header rows; delivery-note and packing-slip lines).
Written knowing only the KIND names (report, ledger, receipt, spreadsheet) from the coordinator's request, and **before the second blind set existed in readable form: I have never opened `eval_layouts_r6_blind.json`** (I only ran a script that prints counts and registry-check failures).
Control: TABV re-run (its frames are re-filtered against the new set, so round 5's TABV is not reused).

## Evals (each run scores all three)
- **Blind-2** `eval_layouts_r6_blind.json`: 12 families (3 report, 2 ledger, 2 receipt, 2 spreadsheet, 3 other) x 4 op pairs x 3 wordings, written by a separate Claude worker given only the task description (no repo access, no sight of any training or earlier test wording). 192 questions: 12 x 4 x (2 unseen + 2 seen finals). Still a Claude model, unchecked grammar; a GPT/Astra set would be more independent.
- Blind-1 (round 5 set) and the old self-written 192: guards.
Training frames that share a sentence or 6-gram with any of the three eval sets are dropped (0 left sharing, checked); operand triples of all three are excluded from training. 12,576 sampled rows pass the registry check.

## Marks (6 paired seeds, t = 2.571)
HEADLINE = chain, all 192 Blind-2 questions, paired gain RLV minus TABV. PASS: mean gain >= +5 AND interval lower bound > 0 AND neither guard (Blind-1 all, old all) loses more than 3 points. FAILS: Blind-2 gain < +2. Otherwise partial, no claim.
Reported with no mark: TABV's own Blind-2 level; the four target kinds (report + ledger + receipt + spreadsheet, 144 q) vs 'other' (48 q); per family; call 1 / call 2 given call 1; seed SD.
Gate: train fit (last 192 two-step training items, chain) >= 70% for both arms, else UNDERFIT-VOID.
Wrong-if: RLV gain <= 0 on the four target kinds says style practice does not transfer to a new author's style (then the limit is not seen styles).
Budget cap ~$3 (expected < $1; 12 runs on six 5090s). Credit must stay > $1 (shared).
