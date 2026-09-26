# mu-406 plan, draft 2 (written 2026-09-26, committed 23:45 UTC by date -u; not sealed; for the Thread manager's review)

PLAN-draft.md (19:29) and PLAN-review-1.md (9f3639a96) stay as written. This draft changes the plan after mu-405b
(VERIFY.md 00816bdbe). The test is still rejection-sampling fine-tuning: the 1B trains on its own replies that a
marker calls clean. Three things change: the input, the labels and the test panel. A named fallback is added for the
case where GLM cannot be the marker.

## What mu-405b changed
- Shown (DEV, plain MiniCPM5-1B, greedy): the talker makes up much more about the user when it can read its memory.
  - Memory block in the latest user message (U): 166 claim flags; in the system message (W): 31; no memory (N): 46.
  - U answers 12 of 60 stored-fact questions, against W's 4 and N's 0.
  - U's extra flags appear on every turn kind, small talk included (39 vs 4).
- Suggested (post-hoc, not registered):
  - 75 of U's 300 replies name a stored value, and they carry 58 of the 166 flags. The other 225 carry 108 flags,
    against 26 in W's replies that name no stored value.
  - Only 1 of U's 300 replies names a slot value the user never gave. The code filter from review 1 would therefore
    remove almost none of U's made-up claims.
  - I read 10 of the 52 U replies that both judges flagged and that name no stored value. In most, the talker answers
    the memory block, not the user's turn. Examples:
    - To "hello again", after a user who said "long week already", it replied "I'm glad to hear that you're having a
      good week".
    - Asked for their cat's name, it replied to the grandmother's texts from the old chat.
    - To a question about a cavity, it answered "you're feeling a bit embarrassed".
    - To "whats my tortoise called", it replied about "stepping on your partner's feet", built from the user's salsa
      dancing.
  - So the 1B seems to treat what it remembers as what is happening now.
- Brain (a guess): this resembles spontaneous confabulation, where a patient acts on memories that do not belong to
  the present moment. Schnider's account puts the fault in an orbitofrontal filter that normally suppresses memories
  that don't fit the present. That filter is learned. The engineering analogue is to train the talker to use a memory
  only when the present turn calls for it.

## Draft design (one change: a LoRA trained on the 1B's own clean replies, against the same plain 1B)
- Input: the U form for both practice and test, because that is where the plain 1B reads its memory. U is
  claude_y1f_layout.L1_HEAD, then session 1's 'User said, "..."' lines, then a blank line, then the user's turn, all
  in the latest user message (scripts/claude_mu405b_talk.py).
  - 0.2d keeps the block in the system message for now (Month-end ADDENDUM-36).
  - A mu-406 PASS would give Month-end a talker that can use the U form. Whether to adopt it stays Month-end's call.
- Practice chats:
  - 200 two-session chats. GLM writes the user turns only; code picks the facts, using claude_mu405_facts.py's slots
    on a new seed range.
  - Fictional names; the same five session-2 turn kinds, ending in a stored-fact ask. No Claude text anywhere.
- Practice replies:
  - 4 independent sampled conversations per chat, temperature 0.7, each continuing its own history.
  - Every transcript has exactly g406b's packet form (earlier user messages plus session 2), so the marker sees what
    it was gated on.
  - Sampling runs on BensPC through the Director's queue.
- Labels, applied to each reply:
  - GLM's two-session marks, at reasoning effort low. This needs g406b PASS; see artifacts/claude-g406-2-20260926.
  - On ask turns, a code check that the reply contains the asked value.
  - Review 1's code drop for invented slot values, kept although it will remove little.
  - A turn with no kept sample gives no training row.
- Training: LoRA on the kept replies only, all of them the 1B's own words. The loss is on the reply tokens, with the
  reply's own history and the U input. It runs on BensPC with torch 2.11.
- Test panel (fixed, sealed and kept blind before any practice data exists):
  - 60 fresh two-session DEV chats. GLM writes the user turns; code picks the facts on a separate seed.
  - GLM wording keeps the registered test clear of the 16:39 rule on Claude-worded rows.
- Arms on the test panel (greedy):
  - P: plain 1B with the U input.
  - T: the trained LoRA with the U input.
  - Report only: N (plain, no memory) and W (plain, block in the system message).
- Transfer check (report only): T on mu-405's own DEV panel, whose user turns were written by Claude agents. It is
  compared with mu-405b's U 166 and N 46 on the same chats. This checks whether a gain survives wording that GLM did
  not write.
- Checks:
  - Blind claims judges: two per packet, arms mixed and shuffled, private folders.
  - Pair judges (P vs T) for chat quality.
  - Stored-fact asks right, by code.
  - A small MMLU-Redux and GSM8K no-harm check on the LoRA.

## Draft marks (fixed before sealing; the Thread manager's review first)
- PASS needs all of the following:
  - C_T <= C_P - 10 and C_T <= 0.67 x C_P, and per chat T has fewer flags than P more often than more (one-sided sign
    test, p <= 0.05).
  - Asks right: T >= P - 3.
  - The pair judges do not prefer P: a one-sided sign test for "P better" has p > 0.05.
  - MMLU-Redux and GSM8K each within 2 points of the plain 1B.
- Proved wrong: C_T >= C_P.
- Report: C_T against C_N. The real goal is a talker that uses its memory and invents no more than one without it.

## If GLM cannot be the marker (g406b FAIL or INCONCLUSIVE), named now
- Code-only labels cannot catch this failure (1 of 300, above).
- The fallback is one change on the same practice chats: GLM writes the assistant replies. It sees the same memory
  block, and its prompt asks it to reply to the present turn and use a memory only when that turn needs it.
- The 1B trains on those replies (distillation). The code checks stay: the ask value must be present, and no
  invented slot values.
- GLM's own replies are not marked by anyone before training. The test panel's blind judges are the only check,
  after training.

## If mu-406 FAILs
Preference training (DPO) on the same samples, as the first draft named: kept against dropped replies of the same
turn. One change, on the same data.

## Cost and order
- $0 if BensPC takes the sampling and the LoRA; the Director orders its queue. A rental would need an ELI5 plan and
  Ben's own yes first.
- Order:
  1. g406-2 and g406b.
  2. Test panel written, checked and sealed.
  3. Practice chats.
  4. Samples.
  5. Labels.
  6. Seal.
  7. Train.
  8. Test.
