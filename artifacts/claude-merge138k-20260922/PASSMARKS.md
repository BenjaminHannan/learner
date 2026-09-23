# PASSMARKS — Merge 138k (138j + 228 guard + 220 restart index), Opus

Sealed BEFORE any registered run. Agent: `scripts/claude_loop138k_agent.py`
(`Loop138kDaemon(SrcGuardMixin228, RestartIndex220Mixin, Loop138jDaemon)`,
`install_srcguard228()` at import). Config:
`artifacts/claude-merge138k-20260922/loop138k-config.json`. Base for every
comparison: 138j (`scripts/fable_loop138j_agent.py`, its sealed rows in
`artifacts/fable-agent138j-20260922/`). Predicted moves:
`artifacts/claude-merge138k-20260922/predicted_moves138k.json` (sealed).
Scorer: `scripts/claude_merge138k_score.py` (sealed). Verdict = PASS only if
K1–K8 all pass.

## Coverage audit (done before the seal)

The only notebook construction site in the 138 lineage is
`Loop138dAgentLoop.__init__` (reads the module global `IndexedLoopNotebook`);
138f delegates to it, 138g/h/i/j and every 138j layer-C mixin have no
`__init__`, and nothing else builds a notebook (grep over the lineage, sleep145,
daemon108/141). 138j's paths:
- reverse lookup (190/190b) -> `L90.notebook_triples` = fix170 cache built from
  `inner._triples` (the 220-rebuilt index), keyed by (inner, len(events));
- retraction "X's R is not Y" (154f) and named replacement "Updated … (it was …)"
  (154g) -> `M154.taught_current154b` over `nb.facts` + `nb.active` (source of
  truth) and `nb.retract` / `listening._teach` (which update the index through
  `_apply`);
- 192 Updated replies -> `nb.facts` / `nb.events`;
- 142 compose paths -> `inner._sr` / `_sro` (220-rebuilt).
No 138j path keeps a cache outside the 220 rebuild. Nothing to report.

## Marks and bars (integer counts)

| Mark | What | Bar |
|---|---|---|
| K1 | verifier ghost dialog `p3d-ghost.json` + `p3c-restart2.json` through `claude_merge138k_probe.py` | 0 positive "Oriel's boss is …" replies after the restart; 0 stored Oriel triples at the end of p3d; duplicate audit OK at every restart, snapshot and dialog end (fast index == full-scan truth, no repeated triple, no repeated fact id) in all audits; every move vs 138j (same driver) predicted by id |
| K2 | 220's R1/R2/R3 via `claude_merge138k_marks220.py` (220's scorer, `fixed` = 138k) | R1 60/60, R2 11/11, R3 20/20 (220's level) |
| K3 | `fable_suitediff218.py --base-dir artifacts/fable-agent138j-20260922 --only rt136,rt143,sessions152,bench,marks123` + verifier rt143 no-gate (`claude_merge138k_rt143nogate.py none`) vs `rt143-138j-g1.json` | 0 new WRONG / WRONG-WRITE / junk / lost OK; GATE clean; no suite SKIPPED; every move predicted by id (predicted: none) |
| K4 | verifier's 15 fresh dialogs `p3-dialogs.json`, 138j and 138k through the same driver | replies identical except predicted; 0 bad writes (per-turn event counts identical, no stored triple 138j lacks); stored moves only as predicted (d11 duplicate) |
| K5 | `fable_sleepsmoke206.py` on 138j and 138k (same seed, idle 5 s) | every report field equal except labels/paths/timings |
| K6 | `fable_marks123_all.py --suites p2,soak --workers 1` on 138k vs 138j's sealed `marks138j` | soak completed/kill9s/lost/wrong/doubled/audit counts equal; soak final notebook taught triples identical (plain log load); p2 64 rows identical |
| K7 | `claude_merge138k_latency.py`, p3+p3c+p3d dialogs, 3 alternating process pairs (j,k,j,k,j,k), 2 reps each | median per-turn latency 138k − 138j ≤ +5 ms |
| K8 | `fable_suitediff218.py --only bench` 3 back-to-back runs | 4/4 row files byte-identical across the 3 runs (800 rows) |

## Predicted moves (full text in predicted_moves138k.json)

- K1 p3d-ghost:d00t05 reply "Oriel's boss is Tavish." -> "I don't know anyone whose boss is Tavish." (ghost gone).
- K1 p3d-ghost:d00 stored [Oriel boss Tavish, Tavish city Drumlow ×2] -> [Tavish city Drumlow].
- K1 p3c-restart2:d01 stored [Marl city Osterby ×2] -> [Marl city Osterby].
- K4 d11 stored [Oriel boss Tavish ×2] -> [Oriel boss Tavish].
- K3, K5, K6, K8: no moves. K7: within noise.

## Registered commands (after the seal; one heavy suite at a time; `uptime` first)

```
R=artifacts/claude-merge138k-20260922/run
py scripts/claude_merge138k_probe.py <agent> <config> <wd> artifacts/claude-verify-20260922/138j/{p3-dialogs,p3c-restart2,p3d-ghost}.json $R/probe/{j,k}-<name>.json
py scripts/claude_merge138k_marks220.py --mode r1|r2|r3 --agent fixed --cases artifacts/fable-restartindex220-20260922/cases220.json --out $R/m220
py scripts/fable_suitediff218.py --agent scripts/claude_loop138k_agent.py --config <cfg> --base-dir artifacts/fable-agent138j-20260922 --out $R/sd --only rt136,rt143,sessions152,bench,marks123
py scripts/claude_merge138k_rt143nogate.py none $R/rt143nogate-k.json
py scripts/fable_sleepsmoke206.py --agent <j|k> --config <cfg> --root <wd> --report $R/smoke-{j,k}.json --label {j,k} --idle-seconds 5.0
py scripts/fable_marks123_all.py --agent scripts/claude_loop138k_agent.py --config <cfg> --out $R/mk-k --suites p2,soak --workers 1
py scripts/claude_merge138k_latency.py <agent> <cfg> <wd> 2 $R/lat-{j,k}-{1,2,3}.json <p3 p3c p3d>
py scripts/fable_suitediff218.py ... --only bench --out $R/bench{1,2,3}
py scripts/claude_merge138k_score.py $R artifacts/claude-merge138k-20260922/predicted_moves138k.json $R/score138k.json
```
