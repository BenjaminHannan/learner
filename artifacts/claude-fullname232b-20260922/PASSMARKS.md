# 232b PASSMARKS (sealed before the 232b panel existed)

232b is a diagnosis-driven follow-up to the registered 232 FAIL. It re-registers the **same code** under a corrected wrong-write definition, on a fresh blind panel (artifacts/claude-namepanel232b-20260922/, built by a separate writer).

## Code: unchanged from 232
The following files must match artifacts/claude-fullname232-20260922/SEAL.sha256.txt. I checked this before writing this file, and it is checked again before and after the runs:
- scripts/claude_loop232_agent.py
- artifacts/claude-fullname232-20260922/loop232-config.json
- artifacts/claude-fullname232-20260922/dev232.jsonl
- scripts/claude_fullname232_run.py
- scripts/claude_fullname232_score.py

If any hash differs, the 232b verdict is FAIL.

## The one change: scorer definition (scripts/claude_fullname232b_score.py)
The new scorer imports the sealed 232 scorer unchanged and replaces only two rules:
- **Wrong write:** any fact the agent stored during the item (every triple in the last turn's cumulative `all` list, active or superseded) that matches no entry in the item's `stated_facts`.
  - Subject and value are compared case-insensitively, with spaces collapsed and trailing periods dropped.
  - Relations are compared after the alias map below. An entry with no relation matches on subject and value only.
- **Trap write:** on trap items (`pair` empty/None, or `family` starting with "trap"), **any** stored fact is a trap write. Trap items get no separate wrong-write count.

### Relation mapping (stated word → the relation 232's code stores)
| Stated relation word | Canonical relation |
|---|---|
| lives in / live in / living in / lives_in / city / residence / home / home_city | city |
| works at / work at / works for / work for / works / work / employed_by / workplace / employer | employer |
| speaks / speak / language / languages | language |
| was born in / born in / born / birthplace / place of birth | place_of_birth |
| anything else (sister, dog, boss, …) | itself (lowercased, spaces → "_") |

## Marks (unchanged from 232 except M1a's definition)
- **M1 (new panel, primary A runs):**
  - M1a: 232 wrong writes = 0 (new definition).
  - M1b: 232 trap writes = 0 (new definition: any write on a trap item).
  - M1c: 232 multi-word right ≥ 232 one-word right − 2.
  - M1d: 232 multi-word right ≥ 138i multi-word right + 20.
  - M1e: 0 items right on 138i but not on 232.
  - M1f: one-word items' replies on all turns byte-identical between 232 and 138i.
  - "Right", gold and other-value rules: 232's sealed code, unchanged.
- **M2, M3, M4:** the code hashes match 232's seal, so these re-use 232's registered results, which were all passes:
  - M2: dev 54/54; parity 207/210 with only the predicted misses.
  - M3: GATE clean, the only move rt143 K5 reply-only.
  - M4: sleep smoke passed.
  - If the hashes don't match at run time, these are re-run and must meet 232's bars.
- **M5:** pooled per-turn median ms over the new panel's A+B runs: 232 − 138i ≤ +5 ms.

## Runs (one registered attempt)
- Check `uptime` first.
- Panel order: 138i A, 232 A, 138i B, 232 B. Each run uses its own fresh workdir, and each item gets a fresh notebook.
- The 232 arm has the 228 guard installed, as before.
- The A runs are primary. The B runs are for latency and the rerun-identity check only.
- Flake rule as in 232: if 232 flips toward an abstain or "Was that a question?" in a way the predictions don't cover, or A and B differ, that item is run alone 5 times and reported.

## Predictions
- 232 multi-word items right ≈ all clear multi-word answer items. 138i multi-word right ≈ only abstain-gold items.
- 0 wrong writes and 0 trap writes for 232 under the new definition.
- Possible 232 misses are limited to the known out-of-scope forms: possessive yes/no questions, of-chains through a multi-word name, and typed particle possessive teaches.
- One-word replies identical. Trap question replies may change to "I don't know anyone called X." (reply-only).
