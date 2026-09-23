# Experiment 42 — automatic sleep (no lesson, no rule search). Fixed 2026-09-21 before any run.
Question: if sleep is only a fixed mathematical procedure over RAW experience (Ben's ruling), how much experience does it need, and do squeeze pressure (weight decay), surprise-ranked replay, or longer sleep reduce that?
Script: scripts/fable_autosleep42.py (hash in SEAL). Bases: registered CardFold base.pt for 4101–4103; new bases 4104, 4105 trained by the unchanged CardFold script.
Arms: R20, R100, R400 (wd 0.01, uniform, 3000 updates); R100-squeeze (wd 0.10); R100-surprise (replay ∝ prediction error); R100-squeeze-long and R20-squeeze-long (wd 0.10, 12000 updates).
Seed validity: base old-skill accuracy ≥ 0.95 (same M5 as CardFold). Invalid seeds are shown but carry no claim. Every seed reported; no averaging.
Marks (each judged on VALID seeds only, need ≥ 3 valid seeds for any claim):
- A1 REPRODUCTION: R20 fresh < 0.20 in every valid seed. If not, the pipeline differs from the registered run and nothing else is claimed.
- A2 ENOUGH EXPERIENCE WORKS: R400 fresh ≥ 0.80 AND old-skill drop ≤ 0.03 in every valid seed.
- A3 SQUEEZE HELPS: R100-squeeze fresh − R100 fresh ≥ 0.20 in at least 2/3 of valid seeds.
- A4 SURPRISE REPLAY HELPS: R100-surprise fresh − R100 fresh ≥ 0.20 in at least 2/3 of valid seeds.
- A5 LONGER SLEEP HELPS: R100-squeeze-long − R100-squeeze ≥ 0.20 in at least 2/3 of valid seeds.
- A6 TINY-LOG GROKKING: R20-squeeze-long fresh ≥ 0.50 in at least 2 valid seeds.
- A7 LENGTH: any arm with long-input accuracy ≥ 0.50 in at least 2 valid seeds.
Allowed wording on success: "on this toy, plain replay of N raw episodes put the new skill into the weights". Not allowed: "the model understood", any claim about language or the village task.
Note fixed in advance: R400 is mathematically the same kind of data the registered S arm practised on (400 correct input→answer pairs), so A2 passing would mean the software lesson's only job in CardFold was to manufacture examples.
