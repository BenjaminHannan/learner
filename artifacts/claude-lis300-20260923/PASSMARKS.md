# lis-300: our own reader (MiniCPM5-1B fine-tuned) + write compiler, first registered test

Written by the listener thread (Opus), 2026-09-23, **before** any fine-tuning run. Ben's decisions: an own ~1B reader (10:55 UTC); base model openbmb/MiniCPM5-1B, Apache 2.0 (11:01 UTC).

## The one change

The borrowed ear (v4.1 + 27B yes/no gate, 261b/264) is replaced by **one fine-tuned 1B reader + the plain-code write compiler**. Everything after the notebook write is unchanged. Chat-page wiring is a separate later experiment.

## System under test

- **Reader:** `scripts/claude_lis300_train.py` is LoRA (rank 32, alpha 64, every linear layer) on MiniCPM5-1B. It runs 2 epochs at lr 2e-4, batch 16, max length 256, with seed 300, and the LoRA is merged before reading. The prompt and frame text are in `scripts/claude_lis300_common.py`, and the frame format is `design/v3/60-listener/frame-spec.md`.
- **Data:** `scripts/claude_lis300_data.py` builds it. It uses 3,000 own-O0b rows per family, dropping the whole `binding` family, because its pronoun owners are either the pronoun itself or a guess from assumed gender (found here, confirmed by the own-model thread). It adds the Opus-written rows (`data/opus_w{1,2,3}.jsonl`) that a blind second Opus labeller reproduced (`scripts/claude_lis300_agree.py`), each repeated 4 times, with 10% held out as dev.
- **Confidence:** `scripts/claude_lis300_read.py` scores each fact by the lowest token probability over the act and that fact's JSON.
- **Compiler:** `scripts/claude_lis300_compiler.py` is the only writer. A fact is written only if:
  - its mode is ASSERT or CORRECT;
  - its owner is `me` or a whole-word span of the turn or previous reply (never a pronoun);
  - its value is a whole-word span of the turn, or of the assistant's question for a short answer;
  - its relation is in the table;
  - its confidence is at or above the threshold T.

  Writes are all-or-nothing per turn. `we` triggers ask-whose.
- **Threshold rule (fixed now, computed on dev only):** T is the smallest value on the grid in `claude_lis300_score.py --sweep` that gives **0 wrong-save turns** on the whole dev set (o0b L2 sample + Opus dev + the 300 fresh own-O0a2 turns). If no grid value reaches 0, T = 0.995.
- **Scorer:** `scripts/claude_lis300_score.py` grades gold and predicted frames through the same compiler. Ruling 1 applies: a narrower relation counts as a hit.

## Registered test

`artifacts/claude-lispanel300-20260923/`: 240 turns written blind by a separate Opus agent from the spec, with names from N to Z only (training names run A to M). The key is audited by a second blind Opus labeller and adjudicated, and the key version used is sealed before the run. It is run **once**, after the seal.

## Marks (arm A = reader + compiler at T)

| Mark | Bar |
|---|---|
| P300.1 wrong-save turns (any written fact not in the gold writes) | ≤ 1 of 240 |
| P300.2 exact recall of gold writes (hits / gold writable facts) | ≥ 85% |
| P300.3 ASK turns read correctly (owner, relation, inverse, via) | ≥ 90% |
| P300.4 our/we turns that ask whose | ≥ 90% |
| P300.5 unparseable outputs | ≤ 2% of turns |
| P300.6 median read time on the GPU used (device reported) | ≤ 1,500 ms |

Report only, with no bar:
- wrong facts per saved fact and per turn;
- wrong-save turns and recall at T = 0, to show what the threshold buys;
- misses by family, at category level only;
- training loss and tokens per second;
- held-back (asked-back) facts.

**Proved wrong if:** P300.1 fails (≥ 2 wrong-save turns), since the reader is then not safe enough to write even with the threshold; or P300.2 comes out < 75%, since the threshold or compiler is then too strict to be useful.

A FAIL gets exactly one diagnosis-driven follow-up (lis-301+).
