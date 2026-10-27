# Exp 235 RESULTS -- SmolLM2-360M ear (fine-tuned) vs the 138i rule reader

## Result
**Registered verdict: FAIL** -- only on M2 (wrong saves 3, bar <= 2). M1, M3, M4, M5 pass.
M4 passes only after a post-seal, driver-only fix to how the panel's chain-question gold is read
(sealed loader: M4 25/40 = FAIL; fixed: 40/40). Even with M4 counted as a fail, the verdict is the same: FAIL.

Headline: after the brake, the fine-tuned ear got 87/92 statement facts exactly right (94.6%); the 138i rule
reader got 29/92 (31.5%). It read every one of the 40 questions exactly and saved nothing from 24 of 25
"don't save this" turns. It made 3 wrong saves; the 138i reader made 8.

## Marks (integer counts; panel = 150 turns; A = after the brake)
| mark | bar | A_raw (no brake) | **A (registered)** | B (138i+228) | pass? |
|---|---|---|---|---|---|
| M1 no_save TEACH frames kept | <= 1 of 25 | 1 | **1** | 0 | PASS |
| M2 wrong saves, statement + no_save families | <= 2 | 4 | **3** | 8 | **FAIL** |
| M3 statement TEACH recall | >= 80% and A >= B+15 | 89/92 (96.7%) | **87/92 (94.6%)** | 29/92 (31.5%) | PASS (+63.1 pts) |
| M4 ASK recall, questions + chain | >= 80% | 40/40 | **40/40 (100%)** [sealed loader: 25/40] | not run | PASS* |
| M5 median ms/turn, RTX 5070 Ti | <= 300 | -- | **55.8** (p90 83.9, max 155.6) | 2-3 ms (rules, Mac) | PASS |
| Mac CPU 1 thread (no bar) | -- | -- | median 578.8, p90 793.0, max 1554.8 | -- | -- |

*M4 pass depends on the disclosed chain-gold fix below.

Per family, A after the brake (exact whole turns): plain_teach 25/25, varied_teach 25/30, full_names 15/15,
questions 25/25, chain_questions 15/15, no_save 24/25, corrections 15/15. Stray TEACH frames on question turns: 0.
B exact turns: plain 20/25, varied 1/30, full_names 6/15, no_save 25/25, corrections 2/15.
The brake dropped 3 frames, all "relation not in table" (little_sister, best_mate, parrot). It stopped 1 wrong save
(041) and threw away 2 correct ones (044, 046). No frame was dropped for a subject/value span failure.
CPU and GPU raw outputs agree on 149/150 turns (e235-031 differs only in the case of "Hester"; the scorer ignores case).

## The 3 wrong saves (A after the brake)
1. e235-034 "Anya teaches at Fernhill School." -> `Anya | school | Fernhill School` (gold: workplace). The table has
   `school`, so the brake cannot catch it: the right words were given the wrong relation.
2. e235-051 "My sister is Ana and she lives in Tarrow." -> `My | city | Tarrow` (gold: Ana | city). "she" was resolved to the speaker.
3. e235-126 "so Pella speaks Norrish?" (no_save) -> `pella | language | Norrish`. A question written like a statement with a "?" got saved.

## 10 most instructive panel misses
1. e235-051 (A) pronoun "she" bound to the speaker -> a wrong fact about *me*. The training data never had "X is Y and she ...".
2. e235-126 (A) statement-shaped question "so Pella speaks Norrish?" saved. The training NONE family had no echo-questions.
3. e235-034 (A) "teaches at" read as `school`: a real table relation, so the span brake cannot help. The weak spot is the relation choice.
4. e235-041 (A) invented relation `little_sister` -> brake dropped it (the brake working as designed; recall lost, no wrong save).
5. e235-044 / 046 (A) `best_mate` and `parrot` were not in the table as the model wrote them; the brake dropped frames the scorer's gold aliases count as right. The brake costs recall where the table's alias list is thinner than the gold's.
6. e235-008/012/042/064 (B) "is called Biscuit" saved as value "called Biscuit": 4 of B's 8 wrong saves come from one phrasing.
7. e235-055 (B) "born in Dunmere but lives in Saltby now" saved as a place "Dunmere but lives in Saltby"; A got both facts.
8. e235-147 (B) correction tail "Wendeline, I mixed them up" saved as the value; A handled all 15 corrections.
9. e235-050/051/052/054 (B) multi-fact turns -> "one fact at a time" (no save). A got every multi-fact turn except 051's pronoun.
10. e235-048 (B) "Ned lives in Pebbleford, by the way." -> a clarify reply about "Pebbleford, by the". A read it cleanly.

## Every move (in order)
1. Read the rules, relation table v1, and the 138i/228 agent entry points. No panel opened.
2. BensPC's `transformers` fails to import (hub-version check), and we install nothing, so I re-implemented SmolLM2-360M
   (Llama) in plain torch (`claude_smolear235_model.py`). Parity with HF on the Mac: max logit difference 0.0.
3. Wrote the generator (`_data.py`): fictional names, table teach/ask wordings plus paraphrases, multi-fact, corrections,
   questions, chains, 8 NONE kinds. 59 whole templates (14%) held out as dev. 36,000 train / 2,800 dev rows.
4. Speed work: repeat_interleave GQA, lengths padded to a multiple of 32, loss logits only at target positions, a CUDA-graph decoder.
5. Training run v1 slowed about 4x (VRAM spill). On the director's instruction: confirmed the command line, killed PID 17020 only,
   restarted with micro-batch 16 x accumulation 2 (same effective batch 32), memory logging, and a speed stop
   (steps 200-300 averaging over 1.0 s/step -> stop). v1 log kept as `train/train_log_v1_stopped_vram_spill.txt`.
6. v2 pilot trained (about 0.26 s/step, peak about 11.7 GB). Hand probes showed nested facts saved, "Whose dog is Rex?" read as ASK,
   and appositives. I added three data families (nested_none, whose_none, appos_one) and trained v3 (580 s). All before the seal.
7. v3 dev: 783/800 exact after the brake. GPU median 63 ms. Froze checkpoint sha256 2852a5c0...8f8.
8. Wrote PASSMARKS, sealed 17 files, appended P235.1-P235.6 to the ledger. Then verified the panel seal and opened the panel.
9. Arm A on the GPU (150 turns), arm B on the Mac (110 statement turns, fresh workdir each, 228 agent), Mac CPU latency run.
10. Scored with the sealed scorer + the sealed loader, then with the chain-gold fix. The fix changes M4 only.
11. Deleted the Mac checkpoint copy (Mac free space back to 8.3 GB). The checkpoint stays on BensPC `C:\Users\benja\smolear235\out_v3\`.

## Deviations
- **Post-seal driver-only fix (chain gold).** The panel writes chain questions as
  `{"relation": "city", "relation_aliases": [...], "chain": ["boss","city"]}`. The sealed loader
  (`claude_smolear235_panel.py`, `_first(f, ["relation","rel","relations","chain","r"])`) takes `relation` first, so every
  chain question became a 1-hop "city" question and A's correct 2-hop answers were marked wrong (15 of 15).
  The fix is a NEW file, `scripts/claude_smolear235_panelfix.py`. It calls the sealed loader, and then, for any gold frame with
  `chain` longer than 1: hops = chain, and relation_aliases apply to the last hop only. It then runs the sealed scorer
  unchanged. No sealed file was edited (seal re-checked: 17/17 OK after scoring). Both scores are kept:
  `run/score_sealedloader.json` (M4 25/40) and `run/score.json` (M4 40/40). The verdict is FAIL either way.
- v1 training stopped for VRAM spill and restarted with gradient accumulation (director instruction).
- v2 -> v3 retrain with 3 new data families after hand probes. This was before the seal, and the panel was not opened.
- Arm B uses `claude_loop228_agent.py` (138i + the 228 SrcGuard), as the rules require.
- Arm C (SciBERT 119h + 213 gate) was not run: optional in the brief, and BensPC's transformers is broken (we install nothing).
- The Mac CPU latency command added `--with tokenizers --with safetensors` to the standard uv line (offline, from the cache).
- The Mac checkpoint copy was made when free space was above 8 GB, but the copy pushed free space to 7.6 GB. It was deleted after the CPU run.
- The Instruct model was used, not base: it is the only SmolLM2-360M in the Mac cache (no network).

## What it means
- A small borrowed language model, trained for 10 minutes on self-made sentences, reads chat turns into memory frames far better
  than our hand-written rules. On new, blind wordings it got 95 facts in 100 right versus about 32, and every question including two-hop ones.
  It also handled corrections, multi-fact turns and full names, where the rules mostly gave up.
- It is fast enough: about 56 ms per turn on the home GPU. On the Mac CPU it is slower (about 0.6 s), still usable for chat.
- The exact-words brake does its job for invented relations. But all 3 wrong saves used real words from the turn and a real
  table relation, so the brake could not see them. The remaining risk is *meaning* mistakes (who "she" is, statement vs question,
  which relation), not made-up names.

## What it doesn't mean
- It does not pass: 3 wrong saves are more than the 2 allowed. It is not safe to write straight into the notebook yet without another check.
- One 150-turn panel from one writer. The 94.6% has a wide error bar, and the panel's wordings may be closer to my generator than real chat is.
- The model is borrowed. This is a stand-in ear, not our own architecture (allowed for now under the placeholder ruling).
- The M4 100% needs the disclosed loader fix. Under the loader as sealed it scores 62.5%.
- Arm B was scored only on statements. This says nothing about how 138i handles questions.
