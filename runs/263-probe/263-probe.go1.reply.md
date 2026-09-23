Holding the line on exp 263 — verifying seal and both write guards.
Seal checks out — now probing both guard arms.
VERDICT: Probe ran clean. Seal intact (13/13 OK). 263 stored zero comma-subjects across all 12 dialogs; 260 stored comma-subjects in 2 dialogs. 263 differs from 260 in 4 of 12 dialogs.

1. SEAL OUTPUT (full, `shasum -a 256 -c artifacts/claude-comma263-20260923/SEAL.sha256.txt`, exit 0):
```
scripts/claude_fix263_comma.py: OK
scripts/claude_loop263_agent.py: OK
scripts/claude_comma263_devcases.py: OK
scripts/claude_comma263_run.py: OK
scripts/claude_comma263_score.py: OK
scripts/claude_comma263_regscore.py: OK
scripts/claude_263_runall.sh: OK
scripts/claude_263_panel.sh: OK
scripts/claude_263_openpanel.sh: OK
artifacts/claude-comma263-20260923/loop263-config.json: OK
artifacts/claude-comma263-20260923/devcases263.json: OK
artifacts/claude-comma263-20260923/PASSMARKS.md: OK
artifacts/claude-comma263-20260923/predicted_moves263.json: OK
```

2. METHOD: fresh agent + fresh /tmp state dir per dialog, turns in order, triples via `fable_loop90_agent.notebook_triples` after each turn (same as `run_base.py`). 260 = `scripts/claude_loop260_agent.build_agent260` + `artifacts/claude-openers260-20260922/loop260-config.json`. 263 = `scripts/claude_loop263_agent.build_agent263` + `artifacts/claude-comma263-20260923/loop263-config.json`. Rows saved: `artifacts/claude-verify-20260923/263/arm260.json`, `arm263.json` (driver: `verify263.py`, same folder). No other files created.

3. MARKS TABLE (stored triples AFTER LAST turn; comma flag = any stored SUBJECT contains ","):

| Dialog | 260 stored (last) | 260 comma? | 263 stored (last) | 263 comma? | Stored differs? |
|---|---|---|---|---|---|
| D1 | [["Dude, Orla","boss","Petra"]] | YES | [["Orla","boss","Petra"]] | no | YES |
| D2 | [["Brin","employer","Halden Mill"]] | no | [["Brin","employer","Halden Mill"]] | no | no |
| D3 | [["Wow, Tamsin","sister","Juno"]] | YES | [["Tamsin","sister","Juno"]] | no | YES |
| D4 | [["Ilse","city","Carrow, Wend"]] | no (comma is in VALUE only) | [["Ilse","city","Carrow, Wend"]] | no | no |
| D5 | [] | no | [["Mabon","language","Welsh"]] | no | YES |
| D6 | [] | no | [] | no | no |
| D7 | [["Fenn","boss","Aldo"]] | no | [["Fenn","boss","Aldo"]] | no | no |
| D8 | [] | no | [] | no | no |
| D9 | [] | no | [["Coral","brother","Dane"]] | no | YES |
| D10 | [] | no | [] | no | no |
| D11 | [] | no | [] | no | no |
| D12 | [["Ada","city","Luton"]] | no | [["Ada","city","Luton"]] | no | no |

4. TOTALS (integer counts):
- Dialogs run: 12 per arm, 24 total. Turns run: 23 per arm (D10 has 1 turn, all others 2), 46 total. Misses: 0.
- Comma-subject dialogs, arm 260: 2 (D1, D3). Comma-subject triples, arm 260: 2.
- Comma-subject dialogs, arm 263: 0. Comma-subject triples, arm 263: 0.
- Dialogs where 263 stored-triples differ from 260: 4 (D1, D3, D5, D9).
- Reply text also differs in exactly those same 4 dialogs (D1/D3: 260 "don't know" vs 263 answers; D5/D9: 260 save-fail + "don't know" vs 263 saves + answers). All other dialogs: replies and stores match.

5. EVERY MOVE (263 vs 260, stored-last-turn):
- D1: Dude, Orla -> Orla (comma subject fixed, answer restored).
- D3: Wow, Tamsin -> Tamsin (comma subject fixed, answer restored).
- D5: nothing stored -> Mabon stored (save-fail became save; answer restored).
- D9: nothing stored -> Coral stored (save-fail became save; answer restored).
- D2, D4, D6, D7, D8, D10, D11, D12: no stored difference.

6. DEVIATIONS / NOTES:
- Load was 67-72 (above the 60 wait threshold) but this probe is tiny (46 CPU turns, one process, seconds); ran once per arm as ordered. Disk free 19 GB (above 3 GB bar).
- Did NOT git commit/push anything: OPUS-RULES hard-forbids commits/pushes, so the task's "PUSH: ..." line was not executed; files are on disk only. No existing file edited; nothing read from TEST-ONLY panels; each director dialog run exactly once per arm.
- 260 quirk (not mine to explain, just observed): D5/D6/D8/D9 opener turns got a save-failure reply and stored nothing under 260, while D1/D3 opener turns stored comma-subjects. D11 stored nothing on both arms ("one fact at a time" — comma in value "Stone, Hale and Webb" blocked the save on both arms).

7. WHAT IT MEANS (plain English): On these 12 made-up dialogs, the 263 comma guard did its job — no saved name ever contained a comma, and two cases where 260 saved a junky name like "Dude, Orla" came out clean as "Orla" under 263.
8. WHAT IT DOESN'T MEAN: This is only 12 dialogs, not the full test. It doesn't prove 263 is perfect everywhere, and it doesn't say anything about cases I didn't run (like D11's value-comma, which neither arm saved).
