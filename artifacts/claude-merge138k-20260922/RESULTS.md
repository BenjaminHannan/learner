# RESULTS — Merge 138k (138j + 228 guard + 220 restart index): **PASS**

All eight registered marks passed. The seal was re-checked after every run: 13/13 files OK, and nothing was edited after the seal. Exactly 4 things changed compared with 138j, and all 4 were predicted by id before the runs. The 228 guard was installed in every 138k process (at import and again by `SrcGuardMixin228`).

Agent: `scripts/claude_loop138k_agent.py`, built as `Loop138kDaemon(SrcGuardMixin228, RestartIndex220Mixin, Loop138jDaemon)`. Config: `loop138k-config.json`. Rows and reports: `run/`. Scorer output: `run/score138k.json`.

## Marks

| Mark | Bar | Got | Verdict |
|---|---|---|---|
| K1 ghost dialog + restart duplicates | 0 ghost replies, 0 ghost stored, audit OK at every restart, snapshot and dialog end, only predicted moves | 0 ghost replies; 0 ghost stored; 9/9 audits OK; 3 moves, 3 predicted | PASS |
| K2 exp 220's own marks re-run on 138k | R1 60/60, R2 11/11, R3 20/20 | R1 60/60, R2 11/11, R3 20/20 | PASS |
| K3 frozen suites vs 138j's saved rows | 0 new WRONG, WRONG-WRITE or junk; GATE clean; every move predicted | rt136 0, rt143 0, sessions152 0, bench (800 items) 0, marks123 0 moves; GATE clean; 0 suites skipped; verifier's rt143 no-gate run 0/124 moves | PASS |
| K4 verifier's 15 fresh dialogs | replies identical except predicted; 0 bad writes | 0 reply moves; 1 stored move (d11, predicted); 0 changes in per-turn event counts; 0 bad writes | PASS |
| K5 sleep smoke | same marks as 138j | both: 1 sleep, 1 install, 20 episodes, probes 5/5, 0 wrong, broken chain abstains, taught 50/50, 0 overwrites; 0 fields differ | PASS |
| K6 soak + p2 vs 138j's sealed marks138j | identical | soak: 2000 turns, 3 kill-9s, 0 lost, 40 wrong, 0 doubled, 0 in all 3 audit counts (same as 138j); final notebook 200/200 taught triples identical; p2 0/64 row moves | PASS |
| K7 median latency | ≤ +5 ms | 138j 1.860 ms, 138k 1.817 ms (delta −0.043 ms; 624 turns each; 3 alternating process pairs) | PASS |
| K8 3 back-to-back bench runs | byte-identical | 4/4 row files identical (800 rows) | PASS |

## Every move against 138j (all predicted)

1. **K1 p3d-ghost d00 t05** "Whose boss is Tavish?"
   - 138j: "Oriel's boss is Tavish." This was the ghost, a stale answer left behind after the restart.
   - 138k: "I don't know anyone whose boss is Tavish."
2. **K1 p3d-ghost d00** stored triples (read from the index)
   - 138j: [Oriel boss Tavish, Tavish city Drumlow, Tavish city Drumlow]
   - 138k: [Tavish city Drumlow]
3. **K1 p3c-restart2 d01** stored triples
   - 138j: [Marl city Osterby, Marl city Osterby]
   - 138k: [Marl city Osterby]
4. **K4 p3-dialogs d11** (the restart dialog) stored triples
   - 138j: [Oriel boss Tavish, Oriel boss Tavish]
   - 138k: [Oriel boss Tavish]
   - Every reply in this dialog is unchanged.

## Coverage check (asked for in the brief)

- **Where the notebook is built.** The notebook is built in one place only, `Loop138dAgentLoop.__init__`, and 220's swap covers that place. 138f's own `__init__` hands off to it. The daemon mixin and `build_agent138k` check that the notebook they get really is `FixedIndexedLoopNotebook`, and stop with an error if it is not.
- **Reverse lookup (190/190b).** It reads fix170's cached `notebook_triples`. That cache is rebuilt from `inner._triples`, which is the index 220 fixes.
- **Retraction (154f).** It reads `nb.facts` and `nb.active` (the source of truth) and writes through `nb.retract`.
- **Named replacement (154g, "Updated … (it was …)").** It reads the same source of truth and writes through `listening._teach` and `nb.retract`. Both update the index through `_apply`.
- **192.** It reads `nb.facts` and `nb.events`.

No 138j path keeps its own cache that 220 does not cover, so nothing needed reporting.

## Deviations

- **220 had no mixin.** Exp 220 applied its fix by swapping the notebook class while `build_agent220` runs. I wrapped that same swap in `RestartIndex220Mixin`, which the daemon uses, and in `build_agent138k`. The fix itself is 220's own code.
- **K5 base.** 138j has no saved sleep-smoke record: its marks123 sleep suite was skipped. So I ran sleep smoke on 138j myself as the reference, the same two-arm design exp 220 used.
- **K6 and the other marks123 suites.** K6 compares against 138j's sealed marks123 soak and p2 results; I did not re-run 138j for these. The suitediff marks123 suite covers p4, q1, bench, rt81 and q4. I did not re-run p3 or rt110.
- **Pre-seal changes.** Before the seal I made two small changes to my own scorer: the notebook loader, and pointing K6 at 138j's sealed folder. Nothing changed after the seal.
- **Time.** The whole job took about 22 minutes, including the pilot.

## What it means

138k gives the same answers as 138j everywhere except where 138j was wrong after a restart. After a restart, every fact is now held once in the fast index. So when you replace or retract a fact, the old one really goes away, and "Whose boss is Tavish?" no longer answers with a replaced boss. Three bench runs in a row came out byte-for-byte the same, so the 228 fix for the random flip holds on this merge too.

## What it doesn't mean

- It does not fix any older behaviour that 138j also has. Examples: "Tell me about Oriel." still declines, and "No, it's Aldgate." still does not replace the city. Soak still counts 40 "wrong" only because its frozen check looks for the word "Saved:" and 138j answers "Updated:".
- It was tested only on these suites, the verifier's dialogs and 220's cases. It is not proof that there are no other restart bugs.
- It changes nothing about sleep learning.
