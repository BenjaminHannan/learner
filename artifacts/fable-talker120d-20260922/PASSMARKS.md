# Experiment 120d (talker don't-know routing) — PASSMARKS (sealed BEFORE any run)

THE ONE CHANGE vs exp 120/120b: new mouth module
`scripts/fable_talker120d_mouth.py` (subclass of `fable_talker120_mouth`,
which is NOT edited) that routes any answer record whose status is NOT in
the six talker-training statuses (OK, UNKNOWN, ABSTAIN, CLARIFY, SAVED,
FORGOT — `scripts/fable_talker120_data.py:251-252`) STRAIGHT to the
notebook-contract template `C.Result(status, fields).say()` with no talker
decode and never an empty string. The six trained statuses go through the
talker + brake exactly as now (inherited). Drivers:
`scripts/fable_talker120d_replay.py`, `scripts/fable_talker120d_score.py`
(copies of the 120 drivers pointing at the new mouth; wire51 files
untouched). Checkpoint:
`artifacts/claude-talker120b-run-20260922/fable_talker120b_ckpt_last.pt`
(the mask-fixed talker). Tokenizer:
`artifacts/fable-talker101-20260921/fable_talker101_tokenizer.json`.
Qwen ears expected at `http://127.0.0.1:18081`; ears must never fall back
silently (`ears_source` starting with "english" on >= 39/40 turns per run).

Step-1 confirmation: "Where is Zed's city?" produces UNKNOWN_ENTITY
(`fable_notebook_contract.py:238`, resolve miss); "Where is Ana's city's
mother?" produces BROKEN_CHAIN (`fable_notebook_contract.py:405`, literal
Porto is not an entity). `fallback_say` (`fable_talker120_mouth.py:208`
catch-all) returns `""` for both; the contract (lines 81/83) gives exactly
wire51's sentences. The brake passes the unfaithful decode because it is an
allowlist (porto/city/mother from the record, beyond/taught in FUNCTION_WORDS
`fable_talker120_mouth.py:94-98`); nothing compares classify() to the record
status. Pure-Python check (no weights): 120d fallback gives both wire51
sentences verbatim; old fallback gives `""` on both; six-status fallbacks
byte-identical.

| mark | threshold (per run unless noted) | note |
|---|---|---|
| R1 wire51 replay x3, new mouth: wrong_writes | [0, 0, 0] | mouth returns strings; writes bypass it |
| R1: correct / abstentions / missed / two-hop | identical to `artifacts/fable-wire51-20260921/replay-report.json` on all 3 runs: correct [12,12,12], abstentions [3,3,3], missed [0,0,0], two_hop_correct [6,6,6] | per-run vectors reported, never averaged |
| R1: empty `said` | no higher than wire51's 5 per run (the silent teaching turns) | 0 empty on answer turns |
| R1: ears_source english* | >= 39/40 turns each run, reported per run | never a silent fallback |
| R2 score of the sealed 500 held-out records, new mouth: after-brake unfaithful | 0 | raw (before-brake) count reported too, not gated |
| R2: status recoverable | >= 486/500 | raw number reported |
| R2: OK answer present | 250/250 | raw number reported |
| R3: wall-clock | each run (replay, score) < 25 min Mac CPU, OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 | timed per run |

A registered FAIL stays a FAIL (recorded, never re-run into a pass).

## Seal

    shasum -a 256 PASSMARKS.md > SEAL.sha256.txt
