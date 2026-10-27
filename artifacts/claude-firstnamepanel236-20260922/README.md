# TEST-ONLY: first-name panel for exp 236

TEST-ONLY. Builders must not open, print or tune on this folder before sealing their own work.

60 items, each a fresh session (setup turns, then one final turn). All names are generated fictional names (no dictionary words), never repeated across items. Setup facts are all "<First> <Last>'s <relation> is <Value>." (exact_wins also has one "<First>'s <relation> is <Value>.").

| family | count | expect |
|---|---|---|
| unique_first | 20 | ANSWER |
| of_form | 10 | ANSWER |
| ambiguous | 10 | CLARIFY (name both people, give no value) |
| exact_wins | 6 | ANSWER (single-name entity's value) |
| no_match | 6 | UNCHANGED |
| last_name_only | 4 | UNCHANGED |
| statements | 4 | UNCHANGED (same reply and stored facts as base) |

## Files
- panel.jsonl: fields id (f236-001..060), family, setup, question (for statements this is a TEACH turn), expect, gold (value, list of full names for ambiguous, or null), note.
- base221.jsonl: {id, base_reply, base_setup_replies, base_stored} from base scripts/fable_loop221_agent.py with artifacts/claude-tableask221-20260922/loop221-config.json, fresh workdir per item.
- replacements.json: candidate items rejected by the base check, with reasons (not sealed; not part of the panel).
- SEAL.sha256.txt: sha256 of panel.jsonl and base221.jsonl.

## Base check (done before sealing)
Every item passed: (a) every setup sentence saved on the base; (b) the same question with the FULL name returned the gold value (ambiguous: each full name returned its own value; exact_wins: the single name returned V1 and the full name V2; statements: the full-name setup fact is answered and the full-name version of the final teach saves). 4 candidates failed (b) and were replaced.
