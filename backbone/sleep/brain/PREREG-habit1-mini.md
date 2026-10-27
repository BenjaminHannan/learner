# Habit-1 mini: a shrunk stage 2 that runs free on a Mac with MLX, 3-bit vs 4-bit Qwen3.6 (written 2026-10-27 ~06:35Z, before any mini code or run)

Labels: shown / suggested / untested. Week-2 world. Not the card experiments. Ben (06:12Z via coordinator): don't wait on paid boxes. A Vast run after
Nov 1 (addendum 2) is only for confirmation.

## What is kept and what is cut (against stage 2 / addendum 12)
Kept: Week-2 diary, the habit spotter's question and parser (habit.py, addendum 1), the NREM dream prompt (sleepb.af_prompt: paraphrases + Q&A from the
diary messages), weights-only scoring (sleep1.SYS "Answer with just the name.", sleepb.has_ans), and replay of the base model's own answers.
Cut: the tagger and names pass. The fact notes are fixed: addendum 12's own eligible items (made by the 4-bit model), the same for both arms. Also cut:
nights (one sleep at the end of the week), REM, update detection, the KL guard, the morning gate, and the full test set.

## Data (built in the cloud, habit1_mini.json; fixed rule, no model)
- 40 facts: the first 40 Week-2 C2/C4 forward tests (by test order) whose two names an eligible addendum-12 item links. Each comes with its fact
  sentence (that item) and up to 4 diary user turns that contain both names.
- 20 routines: the spotter's question with all of the pair's days (the stage-1 "Rall" prompt).
- Eval: the 40 fact questions, the 20 routine questions ("Where does Sam usually have X with A?"), and ARC-Easy items 1-60 of the same 500 file.
- Replay: 30 of sleep1.generic_prompts().

## Run (one arm = one model; habit_mini.py, mlx_lm, the same settings for both arms)
1. Score before (greedy, max 12 tokens; ARC: the first generated letter).
2. Ask the 20 spotter questions. Each valid yes (parser of addendum 1) becomes a habit item: its sentence plus the pair's diary turns.
3. Dream once per item (40 facts + the habit items) with af_prompt (K = 4), greedy, max 400 tokens. Training samples are its Q&A pairs, plus each
   paraphrase as the answer to "What do you remember about A and B?". Replay = the base model's own answers to the 30 generic prompts (max 120 tokens).
4. Train with `mlx_lm.lora`: LoRA on the last 8 layers (to keep DeltaNet backward memory small), rank 8, lr 1e-4, batch 1, max length 320,
   prompt masked, gradient checkpointing, 300 iterations, adapter saved every 50. A 4-hour wall cap uses the last saved adapter.
5. Score after, with the adapter.

Arms: **m3** = NexVeridian/Qwen3.6-35B-A3B-3bit (Ben's M1 assistant model). **m4** = mlx-community/Qwen3.6-35B-A3B-4bit.
They run on whichever Mac has the memory free and the coordinator's slot. Ben's chats come first.

## Pass marks (fixed now; n = 40 facts / 20 routines / 60 ARC, so 1 question = 2.5 / 5 / 1.7 points)
- **M1 (3-bit can sleep):** m3 fact recall after >= before + 25 points AND ARC after >= before - 5 (no more than 3 questions lost).
- **M2 (3-bit about as good as 4-bit; only if m4 runs):** m3's fact gain >= m4's fact gain - 10 points.
- **MH (the habit spotter works through sleep, on 3-bit):** m3 routine after >= 60% AND >= before + 25 points.
- **Wrong if:** m3's fact gain < 10 points while m4's is >= 25. Then 3 bits blocks learning, and the assistant should sleep on a 4-bit copy.
- Reported: the spotter's yes count per arm, dreams kept, seconds per iteration, peak memory, and wall time.
- Expectation (not a mark): facts before ~0-10%, routines before ~0-10%. LoRA on 8 layers may learn less than the full recipe (suggested).

## Safety on the Mac
Stop if swap grows past 4 GB or memory pressure turns red. Respect PAUSE_OTHERS and ASSISTANT_RUNNING. Run only in a slot the coordinator hands out.
