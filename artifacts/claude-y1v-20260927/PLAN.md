# y1v: y1t's trained doubt on plain LFM2.5-1.2B. Can LFM learn when to say "I don't know" from its own graded drafts? (Answering-from-memory thread, rules fixed 2026-09-27 19:30 UTC, before any LFM draft or adapter exists; sealed in SEAL.sha256.txt)

**Why:** y1u (VERIFY-y1u.md, main f78c2b8d2): plain LFM2.5-1.2B on y1t's DEV check scored 35 of 56 right, 18 wrong
and "don't know" on 1 of 10 never-told asks. Plain MiniCPM5-1B on the same CPU scored 26 / 24 / 2. LFM answers
better but never declines. y1t (trained doubt on MiniCPM) was NO-GO at 22 / 20 / 5. The Thread manager (19:09 UTC):
seal y1t's trained-doubt recipe on plain LFM2.5-1.2B, one change against y1u (the adapter), with the same training data
and no Claude-written text. LFM as the talker is Ben's call; this is a test only.

**The one change against y1u:** an adapter trained with y1t's recipe (artifacts/claude-y1t-20260926/PLAN.md steps 3 to
5), on LFM2.5-1.2B-Instruct at commit 0f604ada3f766f9f257460c4c9f0b5d6f69d431b instead of MiniCPM5-1B.
1. **Items:** y1t's, unchanged (glm2/items: items_train sha256 47e2e295..., items_dev c0288f2c..., GATE-PASS). The chats
   were written by GLM; the answers are checked by code. Nothing is written by Claude.
2. **Drafts** (scripts/claude_y1t_data.py drafts, unchanged): plain LFM answers every training item, greedy plus 4
   samples. Code grades each. Targets: LFM's own right greedy draft, else its first right sample, else "I don't know.";
   never-told twins "I don't know."; "I don't know" rows capped at the answer rows; at most 3000 items; rows repeated
   up to 3 times to about 1500 passes. So the answers LFM trains on are its own.
3. **Training:** scripts/claude_bm398r_train.py unchanged (rank 16, alpha 32, dropout 0.05, 1 epoch, AdamW 2e-4,
   batch 8, loss on the answer tokens and <|im_end|>, seed 3992), run through scripts/claude_y1v_train.py. That wrapper
   changes only where the LoRA goes. The recipe puts it on the attention q/k/v/o projections. LFM has attention in 6
   of its 16 layers, and there the output projection is named out_proj. The other 10 layers are short convolutions
   with no attention. So the LoRA goes on q_proj, k_proj, v_proj and out_proj inside each self_attn block: 24 modules,
   1,277,952 parameters. MiniCPM's y1t adapter had 96 modules and 4,128,768 parameters. The unchanged trainer would
   have missed out_proj. Adding the name "out_proj" globally would also have caught the 10 convolution layers' out_proj.
   Checked here on CPU before sealing: the wrapper's selftest (tiny LFM2) and a 16-row smoke run on the real LFM
   (y1t's rows, no DEV bank) with --no-save: 24 LoRA modules, loss falls, merge works, and the practice dev check runs.
4. **DEV check:** scripts/claude_y1g_doubt.py unchanged, on the merged LFM (seed 4024). The trained config is A1.
   The same script on plain LFM on the same card is the reference (report only; y1u's CPU run gave 35 / 18 / 1).

**Machine:** one vast 1-GPU card with the best TFLOPS per $/h that fits (Ben's standing order, 14:05 UTC 09-27), at
least 16 GB, at most $0.70/h. The kit is handoff/kit/y1vvast, a copy of y1t's tested vast kit (ADDENDUM-9 to 11),
with the model, the adapter wrapper and these four steps: drafts, train, eval, eval_plain. There is no H1 step.
Cap $1.00 for the task; estimate $0.15 to $0.40 (y1t's four matching steps took 20 minutes on an RTX 5000 Ada at
$0.35/h, plus about 10 minutes of setup; LFM's speed on GPU is a guess).

## Decision rules (fixed before the run; y1t's bars)
- GO if the merged LFM's A1 on DEV has answerable right >= 22 of 56 AND answerable wrong-candidates <= 8 AND
  never-told "don't know" >= 8 of 10.
- Report: how many of plain LFM's right DEV asks stay right (the two rows files of this run, same asks); per ask type;
  practice-dev before and after (bm-398r's dev_check); draft counts (own greedy, own sample, "I don't know" targets,
  corrected asks); C3, C4 and V on the merged LFM (report only).
- GO: the Thread manager takes "LFM plus this adapter, A1" as the candidate answerer. The talker or answerer switch is
  Ben's call, and bank E stays unused until its marks are sealed.
- NO-GO: report; the next step is decided after.

## Proved wrong
y1t's line, unchanged. "Trained doubt transfers from practice chats to other chats" is wrong if the practice-dev
never-told "don't know" rises by at least 30 points (bm-398r's dev_check, before against after) while DEV never-told
"don't know" (A1) rises by fewer than 3 of 10 over plain LFM on the same card: the model learned GLM chats, not doubt.

## Predictions (thread, before the run)
GO: 0.1. DEV never-told "don't know" >= 8 of 10: 0.3. DEV right >= 22: 0.8. DEV wrong <= 8: 0.15. Proved wrong: 0.3.

## Limits
DEV has 56 answerable and 10 never-told asks, so a difference of 1 or 2 is noise. The practice questions are all of
one kind (asking back one stored fact); DEV also has two-hop, reversal, yes/no and edit asks. The LoRA is a quarter
of MiniCPM's in size and sits in 6 of 16 layers; a NO-GO could come from that, and this plan does not separate the two.

## Plain summary for Ben
LFM answers more of your memory questions right than MiniCPM (35 against 26 of 56), but it almost never says "I don't
know": it made something up for 9 of the 10 things it was never told. Here LFM gets the same practice MiniCPM got:
GLM-written chats, where each question comes once with the answer in the chat and once with it taken out. Code marks
LFM's own answers, and LFM trains on its own right answers plus "I don't know" where it was wrong or never told. It
passes if it still gets at least 22 right, gives at most 8 wrong, and says "I don't know" to at least 8 of the 10.
