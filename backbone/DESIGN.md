# Borrowed backbone: design and feasibility (2026-10-23)

Labels: **shown** = checked in code, configs or prices today; **suggested** = reasoning or literature; **untested** = nobody has measured it here.
Village model only. The small card experiments are not part of any claim below.

## 1. What we would borrow (shown, Hugging Face configs)
`Qwen/Qwen3.8-27B` (Apache 2.0): 64 layers, width 5,120, vocab 248,320. Three of every four layers are
Gated DeltaNet "linear attention" (a fixed-size running memory updated by a delta rule, the same family as
premonition's 2026-09 delta-rule memory) and every fourth is ordinary full attention. ~55.6 GB in bf16, ~15 GB
at 4-bit. Same-design small models for prototyping: `Qwen/Qwen3.5-0.8B` (width 1,024, 24 layers) and
`Qwen/Qwen3.5-2B` (width 2,048, 24 layers), same tokenizer.

## 2. Ways to plug it in (suggested), best first
1. **Sandwich (recommended).** Bottom layers of Qwen = the ear (reads English into vectors). Middle = premonition's
   thinking board: a block that loops, with registers, a stop signal, and notebook lookups. Top layers + output
   head = the mouth. Start the middle block as a copy of Qwen's own middle layers (so it begins already
   trained), then loop it. LoRA everywhere, so only ~0.5% of weights train. This is the Huginn / "recurrent
   depth" layout (prelude, looped core, coda) applied to borrowed weights. Stage 1 arm B tests the cheapest
   form of this.
2. **Whole model + LoRA, notebook as text.** Facts stay in premonition's notebook and get pasted into the
   prompt at answer time. Simplest and probably strongest at first; it is the baseline every fancier option
   must beat.
3. **Teacher only.** Qwen writes practice data and answers; premonition's own small model learns from them.
   Keeps "Ben's own weights" fully true, but gives the smallest gain.
4. Embeddings only: not recommended; most of what a pretrained model knows lives in its layers, not its
   word table.

How the existing pieces map (suggested):
- Story half D (d128, own 7,289-word vocab) → replaced by the sandwich. D's cards/notebook become the
  notebook the board looks up. Taught facts stay explicit and are never overwritten by training.
- Thinking board → the looped middle block. The internal-state thread's findings (loop use, input
  re-injection, registers) carry over directly.
- Bridge → fixes REPORT F3 (the v1 bridge is a constant): the creative half gets the Qwen question state
  per question instead of a frozen average.
- Creative half B2 → keep for now; later Qwen itself can generate and check programs.

## 3. What fits where (prices shown from Vast offers 2026-10-23; memory figures suggested)
| Job | PC 5070 Ti 16 GB | Mac M1 Pro 36 GB | Vast |
|---|---|---|---|
| 27B answer (4-bit) | yes, already runs (llama.cpp IQ4_XS) | yes (MLX/llama.cpp, slower) | any 24 GB+ |
| 27B LoRA train, 4-bit (QLoRA) | no (weights alone ~15 GB) | possible, slow (untested for qwen3_5 in MLX) | RTX A6000 48 GB ~$0.32/h |
| 27B LoRA train, bf16 | no | no | A100 80 GB ~$0.60/h (tight, short sequences) |
| 0.8B / 2B LoRA | yes | yes | RTX 4090 ~$0.34/h |

A 27B QLoRA run of ~10 hours is ~$3-6 on Vast, inside the weekly cap.

## 4. How sleep makes the borrowed model better (answer to Ben's question)
Today's sleep (shown, v1 `creative_sleep.py` / C2b): the model tries puzzles, keeps the tries that fit the
examples, trains on them with a KL guard (G1) so it doesn't forget, and replays old material.
Known limits (shown, `design/research/sleep-design-2026-09-28/MAP.md`): our small solver cannot *write* new
practice problems, so sleep only replays what it already saw; distilling on the same stored items added little;
long nights at full step size hurt.

With a borrowed model (suggested, untested here):
1. **Dream new problems.** Qwen can write fresh puzzles and questions in the style of the day's material (the
   missing "fake replay" generator). A program or checker labels them, not the model's opinion.
2. **Try, check, keep the right ones.** Sample several answers, keep only the ones a checker verifies (the
   STaR / ReST recipe; on v1 data "fits the examples" was a perfect check, REPORT F2).
3. **Learn into a nightly LoRA, not the whole brain.** Each night trains a small add-on (~0.5% of weights)
   with the KL guard to last night's model. Small, gentle steps (the long-night lesson).
4. **Gate before keeping.** Merge the night's add-on only if held-out checks don't drop; otherwise throw it
   away. A bad night can't damage the model.
5. **Move notebook facts into skills, never into facts.** Sleep practises *using* taught facts (multi-hop,
   reversal) while the facts themselves stay in the notebook.
6. Optional teacher: during sleep a stronger model (Claude API, credit available until ~2026-10-28) can grade
   or explain, as quarantined training data.

## 5. Stages
1. Stage 1 (now): 0.8B on the village task, arms A0/A/B, marks in `PREREG-stage1.md`.
2. Stage 2: sandwich with registers + notebook lookups on 2B; first sleep night (dream, check, LoRA, gate).
3. Stage 3: the same recipe on Qwen3.8-27B with QLoRA on a rented 48-80 GB card; answering on the PC.
