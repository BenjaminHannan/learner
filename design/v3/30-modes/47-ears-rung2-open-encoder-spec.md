# 47 — Ears rung 2: borrowed encoder vs tape vs BiGRU (spec, 2026-09-21)

Status: spec. Ruling that licenses it: Ben, 2026-09-21 — "for now it's fine to have ears' weights that would be someone else's. My biggest concern was mostly just that it wouldn't be as good for our model." Earlier: "if the transformer turns english into thought, then its fine."

## 1. Goal (one sentence)

Ears that read open-vocabulary English (eventually research-paper sentences) and output the reasoner's frame, with the same safety-first marks as rung 1, so that a fine-tuned open-weight encoder can be compared honestly against our from-scratch tape and BiGRU ears.

## 2. What is fixed from rung 1 (unchanged)

- Frame = act ∈ {STATE, ASK, RETRACT, UNSURE, NO_FACT} · relation · subject span · object span · direction · confidence.
- Five brakes (act≠unsure/multi/quote; confidence = min over heads ≥ τ_exec; three-ear agreement; leftover check; validator) and the EXECUTE / ECHO / REPHRASE verdicts.
- Safety mark first: **0 silent wrong writes** on the full panel, or the arm fails.
- Marks sealed (hash) before any registered run; every seed reported; deviations listed.

## 3. Three arms, same marks, same panels

| arm | body | trained by | params |
|---|---|---|---|
| A tape ears (rung 1, 12,000 updates this time) | skills + router | Ben, from scratch | ~0.24 M |
| B BiGRU tagger (rung 1) | 2-layer BiGRU | Ben, from scratch | ~0.24 M |
| C **borrowed encoder** | open-weight pretrained encoder (choice below) + our frame head | body: someone else; head + brakes: Ben | 100–150 M body, < 1 M head |

Arm C is the new arm; A and B are re-run only so the three share panels and seeds. The rung-1 finding "EXECUTE-correct sub-marks unreachable" is fixed by defining them per act (statements only).

## 4. Encoder choice (arm C)

Constraints: permissive licence (Apache-2.0 / MIT; no NC, no community licences); ≤ 150 M so full fine-tune fits 16 GB with Qwen stopped; **BERT-family architecture** so we can load the weights with our own ~150-line PyTorch loader (safetensors is 8-byte header + JSON + raw tensors; WordPiece tokenizer is ~40 lines). Reason: `transformers` is not installed on BensPC and the standing rule is "do not install anything" there; also keeps every line of code around the borrowed weights ours.

Candidate shortlist pending GPT scout C (encoder ranking, licences, fine-tune recipe): BERT-base / SciBERT (scientific vocabulary, simplest architecture), RoBERTa-base, DeBERTa-v3-base (stronger but disentangled attention = more loader work), ModernBERT-base (rotary + alternating attention = most loader work). Decision rule: the best-ranked model whose architecture we can load in plain PyTorch in one day; scientific vocabulary breaks ties.

## 5. Data

- **WebRED** (CC BY 4.0, `data/open/webred/`): parsed without TensorFlow (`scratchpad/webred_parse.py`, protobuf decoder). `webred_21`: 107,819 sentences, 521 relations, 50,023 majority-positive; `webred_5`: 3,898 sentences (1,806 positive) — held out as dev. SUBJ{}/OBJ{} markers are stripped and turned into character spans, so the head learns to point from raw text. The ~50 k **negatives** (sentence does not state the relation) train the NO_FACT act — this is the brake-relevant part.
- Rung-1 synthetic panels (frames + traps, incl. hearsay) regenerated with the missing hearsay markers ("rumour has it", "word is", "supposedly", "allegedly") added **additively** in the rung-2 script, not by editing `fable_listening_english.py`.
- Qwen-written practice sentences under the four fences (E.5 of doc 43), for our closed relation list only.
- Closed-list mapping for the reasoner: WebRED `mother`, `father`, `child`, `sibling`, `spouse`, `employer`, `place of birth`, `educated at`, `member of sports team`, `owned by` → our 8 relations where a clean map exists; everything else stays an **open relation** (string kept, not executed) until the thought format widens (track 3, doc 48).
- Held-out relations: 40 WebRED relations never seen in training → R2-NEWREL (does it point correctly and abstain on the relation, rather than guess a seen one?).

## 6. Marks (to be sealed in PASSMARKS.md before the run)

- R2-SAFE: silent wrong writes = 0 on the full gated panel (all arms).
- R2-NEG: WebRED-dev negatives executed as facts ≤ 2 % (new — the paper-reading failure mode).
- R2-SEEN, R2-NEW (unseen frames), R2-NAMES (unseen names), R2-ASK: as rung 1, EXECUTE-correct redefined per act.
- R2-WEB: WebRED-dev positives, closed-list subset, exact (subject, relation, object, direction) ≥ 85 % of executed, executed ≥ 60 %.
- R2-NEWREL: on 40 held-out relations, executed-with-a-wrong-seen-relation ≤ 1 %.
- R2-PAPER (recorded only, no verdict): 200 arXiv-abstract sentences labelled by Qwen and checked by a second model; report executed / correct / echoed. This is the first look at "research papers".

## 7. Compute plan

- Arm C fine-tune on BensPC (RTX 5070 Ti, 16 GB): Qwen stopped first (it holds ~15 GB). Full fine-tune fp16, batch 32, seq 64, 2 epochs ≈ 7 k steps — expected 15–30 min per seed (unmeasured; measure at 200 steps and abort the plan if > 40 min). Three seeds sequential ≤ 90 min. Arms A/B on the Mac in parallel (≤ 6 single-thread jobs).
- No rental. No new installs on BensPC: weights fetched with the already-installed `huggingface_hub`, loaded by our loader.

## 8. Predictions (to append to the ledger before the run)

- P205 arm C R2-SAFE = 0 in 3/3 seeds (brakes carry over).
- P206 arm C beats A and B on R2-NEW and R2-WEB in 3/3 seeds.
- P207 arm C R2-NEWREL ≤ 1 % in ≥ 2/3 seeds; A and B cannot be scored on it (closed lexicon) — recorded as N/A, not a fail.
- P208 R2-PAPER executed fraction < 40 % for every arm (papers are still mostly out of format).

## 9. What this does and does not claim

- Does: whether borrowed English + our head + our brakes is safer and covers more than from-scratch ears at the same task.
- Does not: that the ears "understand papers". R2-PAPER is recorded only; the thought format for papers is track 3 (doc 48, to write).

## 10. Open items

- Scout C result → pick encoder, fill §4.
- Loader + tokenizer self-test: our loader must reproduce the reference model's hidden states on 20 sentences (max abs diff < 1e-3) before any training — else the arm is void.
- Track 3 spec (thought format widening: open relations, numbers, conditions, "claimed by P" tags).
