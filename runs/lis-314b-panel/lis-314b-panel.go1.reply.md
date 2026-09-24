Re-running the blocked panel — assembling the sealed stack.
The referenced files aren't in this worktree — checking the source branches.
Found the sealed spec on the remote — now verifying preconditions.
Test is stub-only (no model) — safe anytime. Building the combined tree now.
Base layer done (1 GB). Overlaying main now.
Panel seal: all OK. Checking code seal and model hash.
Seals and model hash all pass. Running the stub test suite.
16/16 passed. All checks green — now verifying the sibling job is done before touching the reader.
Arm A done (354 rows). Waiting on the sibling before reader arms.
Sibling arm C finished; waiting through its arm D.
Sibling reader jobs done — starting my reader arms.
Arm C done. Launching P.
Arm P done. Launching K.
Arm K done. Launching S.
Arm S done. Launching G (last arm).
All six arms done. Scoring.
All marks computable. Confirming device and ledger format.
Sibling is done and logged. Assembling the worktree artifacts.
All data in hand. Writing RESULTS.md.
## VERDICT: MIXED — P314 5/5 PASS, P316 3/3 PASS, P315 2/3 (P315.3 FAIL by 2)

Crash fix works: all six arms finished 354/354 turns, zero MPS out-of-memory errors. Neither idea-killer fired.

### Marks (sealed confirm panel, 40 dialogs / 354 turns / 175 final facts, reader lis-301 T=0.995 on MPS)

| Mark | Bar | Counts | Result |
|---|---|---|---|
| P315.1 wrong saves | P ≤ C+1 | P 0, C 0 | PASS |
| P315.2 facts saved | P ≥ C+5 | P 165, C 144 (+21) | PASS |
| P315.3 questions | P ≤ C | P 61, C 59 (+2) | **FAIL** |
| P314.1 wrong saves | K ≤ C+1 and ≤2 | K 0, C 0 | PASS |
| P314.2 saved-or-pending | K ≥ 85% | K 169/175 = 96.6% | PASS |
| P314.3 turns/question | K ≥ 8 | K 11.06 (32 q) | PASS |
| P314.4 asks right | K ≥ C+5 | K 60, C 51 (+9) | PASS |
| P314.5 never-told answered | K ≤ C | K 0, C 0 (20/20 abstained both) | PASS |
| P316.1 wrong saves | G ≤ S | G 0, S 0 | PASS |
| P316.2 saved-or-pending | G ≥ S−2 | G 170, S 170 (+0) | PASS |
| P316.3 questions | G ≤ S+3 | G 32, S 32 (+0) | PASS |

Full summary.json counts for all six arms, device (MPS reader, CPU-only arm A ms_median 4.2; reader arms ms_median 1227–1388, p90 2000–2208, max 3233–3427), and wrong-saved-facts for K/S/G (none — 0 in all three, nothing to list) are in `artifacts/claude-lis314b-20260924/RESULTS.md`.

### Moves, misses, deviations
- Checks all green: panel seal 6/6 OK, code seal 9/9 OK, model sha `b4fd93a2…890` match, 16/16 stub tests passed, 57 GB free. Sealed code never edited; panel files never opened/printed/quoted.
- One ordering deviation (logged in RESULTS.md): arm A is reader-free/CPU-only, so it ran while lis-313b-f0 was on its arm A; all five reader arms started only after lis-313b-f0's last reader arm wrote its rows — one reader job at a time. ~60 min of the 240 min cap used.
- Miss: P315.3 — per-fact release saves 21 more facts with zero wrong saves but asks 2 more questions (61 vs 59).

### Plain English
Confirm-at-use asks half as often (32 vs 59 questions), keeps 97% of facts saved-or-parked, answers 9 more questions right, never invents untaught answers. Guards cost nothing (G ≡ S on every count) — G is the join deliverable. Per-fact release's only flaw: 2 extra questions.

PUSH: `artifacts/claude-lis314b-20260924` (PASSMARKS, SEAL, RESULTS, run/ 6×354-row arms + summary.json, 6 arm logs) + `artifacts/fable-predictions-ledger.md` (3 lines appended, 0 deletions; watcher to push — `artifacts/` is gitignored here).
