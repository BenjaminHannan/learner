# Experiment 120c (talker silence fix) — PASSMARKS (sealed BEFORE any run)

THE ONE CHANGE vs exp 120/120b: new mouth module
`scripts/fable_talker120c_mouth.py` (subclass of `fable_talker120_mouth`,
which is NOT edited) whose fallback for any status outside the six
talk-training statuses uses the same notebook-contract template as wire51's
`TemplateMouth` (`C.Result(status, fields).say()`), never `""`.
Drivers: `scripts/fable_talker120c_replay.py`, `scripts/fable_talker120c_score.py`
(copies of the 120 drivers pointing at the new mouth; wire51 files untouched).
Checkpoint: `artifacts/claude-talker120b-run-20260922/fable_talker120b_ckpt_last.pt`
(the mask-fixed talker). Tokenizer:
`artifacts/fable-talker101-20260921/fable_talker101_tokenizer.json`.
Qwen ears expected at `http://127.0.0.1:18081`; ears must never fall back
silently (`ears_source` starting with "english" on >= 39/40 turns per run).

Step-1 confirmation (before sealing): "Where is Zed's city?" produces status
UNKNOWN_ENTITY (`fable_notebook_contract.py` ask lines 395-397, resolve miss);
"Where is Ana's city's mother?" produces BROKEN_CHAIN
(`fable_notebook_contract.py` lines 404-407, literal Porto is not an entity).
`fallback_say` (`fable_talker120_mouth.py` lines 177-208) returns `""` for both
(line 208 catch-all); the contract gives "I don't know anyone called Zed."
(TEMPLATES line 81) and "Ana's city is Porto, which is not someone I can look
up." (line 83) — the exact wire51 sentences. The raw-decode path also returns
`""`: `say_raw` lines 397-404 and `say` lines 406-422 return `""` for
non-answer kinds, and `brake_check` lines 215-216 rejects empty decodes.

| mark | threshold (per run unless noted) | note |
|---|---|---|
| R1 wire51 replay x3, new mouth: wrong_writes | [0, 0, 0] | mouth returns strings; writes bypass it |
| R1: empty `said` on answer turns | 0 on all 3 runs | 5 smalltalk `""` are by design in BOTH arms (wire51 replay-report.json shows them too); "0 empty replies" = 0 empty on the 15 question turns |
| R1: abstentions / correct / two-hop / missed | identical to `artifacts/fable-wire51-20260921/replay-report.json` on all 3 runs, i.e. correct [12,12,12], abstentions [3,3,3], missed_abstentions [0,0,0], two_hop_correct [6,6,6] | per-run vectors reported, never averaged |
| R1: ears_source english* | >= 39/40 turns each run, reported per run | never a silent fallback |
| R2 score of the sealed 500 held-out records, new mouth: after-brake unfaithful | 0 | raw (before-brake) count reported too, not gated |
| R2: status recoverable | >= 486/500 | raw number reported |
| R2: OK answer present | 250/250 | raw number reported |
| R3: wall-clock | each run (replay, score) < 25 min Mac CPU, OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 | timed per run |

A registered FAIL stays a FAIL (recorded, never re-run into a pass).

## Seal

    shasum -a 256 PASSMARKS.md > SEAL.sha256.txt
