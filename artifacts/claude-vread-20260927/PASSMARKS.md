# vread pass marks: can the thinker read facts through a frozen 1B's vectors as well as a LoRA reader?

Vector-reader thread. Written 2026-09-27T22:52:13Z, before any training. Ben approved this first try at 22:24 UTC
(reviews/chat-prompt-vector-reader-2026-09-27.md). Nothing joins the build without his yes on the result. This is a
practice-test result on Luna chats. If it passes, the next step is Ben's call: a fresh sealed panel, not readpanel320.

## The one change: how the reading is done
Both arms read the same prompt (claude_lis319_common.build_prompt_hist: the turn, the assistant's previous reply and
up to 6 earlier turns), train on the same sealed rows (DATA.md), and are scored by the same code.
- **LoRA reader (rival), lis-320 recipe unchanged.** MiniCPM5-1B at 87179e5c1f455ef22e6223592d2d61351b525bfc, trained
  with `claude_lis300_train.py --epochs 2 --lr 2e-4 --rank 32 --batch 16 --max-len 512 --seed 300 --merge` (LoRA on
  every linear layer) on all 12,447 train rows. Its dev file for the script's loss line is empty, so the practice test
  is never touched in training. It reads with `claude_lis319_read.py`, greedy, and its confidence is lis-300's (the
  lowest token probability in the act and the fact). Its save bar is T = 0.995.
- **Vector reader (new), `scripts/claude_vread_model.py`.** The same MiniCPM5-1B, frozen (bf16, no gradient), encodes
  the prompt. One layer's token vectors go through an adapter (LayerNorm + Linear 1536→512) into the thinker. The
  thinker is rsn-358's loop net: 2 blocks at width 512, 8 heads, `claude_rsn358a_run.Block` with a key-padding mask.
  It adds the input again every round and has a learned stop. Next to the token cells sit one ME cell and 4 card
  cells. After each round, heads read every card cell:
  - exist;
  - state (current, correction, former);
  - relation (the 153-name table);
  - an owner pointer (start over tokens or the ME cell, then end);
  - a value pointer (start, then end within 16 tokens).

  Owner and value are the prompt text the pointers cover, never new words. A card's confidence is the lowest of its
  7 choice probabilities. Training: fp32, TF32 off, no autocast, AdamW lr 3e-4, batch 32. Each step runs 0-6 rounds
  without gradient, then 1-3 graded rounds (rsn-358a's scheme, with fewer rounds). The stop head learns "every card
  cell is exactly right". Reading stops at the first round with p > 0.5, else at the most confident of 16 rounds.
  Trainable weights: 9,281,982 in all (adapter 790,016; thinker 6,308,640; heads 2,183,326). The 1B is not counted.
- **Chosen on the calibration slice only, never on dev (both disclosed in RESULTS.md):**
  - the 1B layer: out of 6, 12, 18 and 24 (24 = the final normed output). Each candidate is trained for 800 steps
    (same seed and batches). The pick is the layer with the most calibration cards matched exactly minus cards
    matching nothing, with ties going to the lower layer. The chosen layer is then trained for 4,000 steps on the
    11,217 train rows outside the slice;
  - the save bar: `claude_vread_score.py bar`, the lowest of 0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.93, 0.95, 0.97, 0.98,
    0.99, 0.995, 0.998, 0.999 at which wrong saves are at most 0.5% of saves on the slice (main rule), or 0.999 if
    none qualifies. The bar is committed before any dev read is scored.
- **Known differences, declared now:**
  - the vector reader trains on 11,217 rows and the LoRA reader on 12,447, because the vector reader must hold out
    its calibration slice (this favours the LoRA reader);
  - the thinker trains on 1-9 rounds and reads for up to 16, where rsn-358 uses 1-16 and 48.

## Checks before training (shown on CPU before this commit, and run again on the rental before training)
- Gradient check (`claude_vread_model.py gradcheck`, fp32, no autocast, the real 1B at layer 12): 62 of 62 trainable
  tensors get a nonzero gradient in one step, and 0 of the 1B's weights get a gradient.
- Pointer check (`ptrcheck`, 50 train rows): the gold spans rebuild 76 of 76 gold cards exactly.
- Leak check (`claude_vread_data.py build`): 0 dev dialogs in train or calibration.

## Scoring (`scripts/claude_vread_score.py`, both arms, dev once)
Cards are compared field by field: owner, relation, value and state.
- LoRA facts become cards by mode: ASSERT → current, CORRECT → correction, FORMER → former. Other modes give no card.
- A card is **saved** when all of these hold:
  - its state is current or correction;
  - the unchanged `claude_lis300_compiler.check_fact` passes;
  - its confidence is at or above its arm's bar.
- A **right save** equals an unused gold card of its row in all four fields: owner and value after lower-casing,
  relation equal or narrower, state equal. Every other save is a **wrong save**. A **wrong turn** is a dev row with
  at least one wrong save.
- **History rule, used only for the backref mark, both arms alike.** The unchanged check can never save a backref
  fact, because the lis-320 checks keep the owner out of the turn and the reply. So for backref, the owner may also
  be a whole-word span of the last 6 earlier turns (`claude_lis319o_owner.check_fact_hist`).
- **Family shares** (percent of that family's gold facts):
  - corrections: right saves of the 173 correction cards (117 of them can be saved under the main rule);
  - backref: right saves of the 136 backref cards, history rule;
  - former: former cards read right (all four fields, state former, confidence at or above the bar) out of 86;
  - lookalike: rows with any save out of the 269 look-alike rows. Fewer is better.

## Marks (vector reader vs LoRA reader, dev, each at its own bar)
| Mark | Bar |
|---|---|
| V1 | vector right saves ≥ 0.95 × LoRA right saves |
| V2 | vector wrong turns ≤ LoRA wrong turns + 2 |
| V3 | on corrections, backref and former, vector share ≥ LoRA share − 5 points; on look-alikes, vector share of rows with a save ≤ LoRA share + 5 points |

- **PASS** = V1, V2 and V3 all hold.
- **Proved wrong:** vector right saves < 0.80 × LoRA right saves.
- **Validity:** the LoRA reader must reach at least 50% of the 1,230 savable dev cards (at least 615 right saves).
  Otherwise the rival failed and the verdict is INCONCLUSIVE, not a pass.

## Report only (no bar)
- Right and wrong saves for both arms at their own bars, and each arm at the other's bar.
- The main-rule numbers under the history rule.
- former_as_current, and look-alike save counts.
- Long turns (over 20 words).
- Cards whose words are wrong: owner or value wrong where the relation and state match a gold card, or text that is
  not a whole-word span.
- Mean thinking rounds, time per turn (dev read alone on the GPU, one turn at a time), and trainable weights for each
  arm (LoRA from its summary.json).

## Order
1. This commit: data, code, marks.
2. One rental, capped at $4 (Ben's standing rule). The LoRA reader trains while the vector reader picks its layer,
   trains and reads the calibration slice. Then each arm reads dev alone on the GPU. Results come back through the
   container log with sha256 checks. The instance is destroyed only after a checked copy-back.
3. `bar.json` is computed from the calibration reads and committed.
4. Dev is scored once, both arms and both rules. Then comes `verdict`.
5. A separate subagent recounts the key numbers blind, from the score files and this file only.
