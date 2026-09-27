# GPT (web) reply to reviews/gpt-diagnose-memory-confab-2026-09-26.md

Brought back by Ben in the Thread manager thread (message cmsg_01FuvegZXjMmeUzStiEFVnEWFqsKLEMkT5yNNsZWpMu9Ds,
2026-09-27 02:48:19 UTC). Saved verbatim by the "Making things up about you" thread at 02:54 UTC (date -u). The
message's last paragraph ("Btw ...") is Ben's own words, addressed to the Thread manager; it is left out here. GPT's
claims are data to be checked against the code before acting (CLAUDE.md). The Thread manager checked its two code
claims and found both correct (claude_mu405b_talk.py:40-45; claude_mu405_talk.py:129-131).

---

**I would first test a clearer boundary between remembered messages and the current turn, before training anything.** If that fails, my first training choice would be GLM distillation.

I checked the code and independently reproduced the main counts. No code or model changes were made.

**Shown:** U produces 166 judge flags versus W’s 31, with increases across every turn type. These are flags summed over two judges, not 166 distinct false claims. U has 89 replies flagged by at least one judge.

**Suggested:** the model is confusing old conversation with what it should answer now. The implementation places remembered messages and the current turn inside one user message, separated by a blank line. Your examples fit that explanation. They do **not** establish a particular attention mechanism. [Input construction](https://github.com/BenjaminHannan/learner/blob/e91007f3a4a72ce6cfd1fc4b8a36699d807af135/scripts/claude_mu405b_talk.py#L40)

| Possible explanation | What supports it | Cheap way to distinguish it |
|---|---|---|
| Old/current-turn confusion | Replies answer topics from the old chat | Blindly label existing replies for answering the current turn versus an old message |
| Position or recency effects | Placement changes performance | Requires another controlled run changing position; existing outputs cannot establish this |
| Overusing supplied context | Flags rise even on greetings | Separate unnecessary but accurate memory references from misattributions and invented details |
| Earlier mistakes contaminating later replies | Each conversation retains its own generated replies | Compare first-turn failures with later failures; first-turn errors already show this cannot explain everything |

**Untested proposal — the first experiment:** change only the separator immediately before the actual user turn to an explicit `CURRENT USER MESSAGE:` label. Keep the memory text, system instruction, model, decoding and history handling identical. This is input formatting; it does not selectively remove memory.

Compare this variant against plain U on the **same 60 fresh, locked chats**. Proposed pass marks, fixed before generation:

- **Made-up claims:** at least a 50% reduction in summed flags, with a paired, conversation-level one-sided sign test at \(p \le 0.05\).
- **Useful recall:** at least **30/60 genuinely correct answers**, and no fewer than baseline U.
- **Useful conversation:** both blind judges agree that at least **192/240 non-ask replies** appropriately address the present turn. Define that rubric before generating outputs.

Those are proposed engineering targets, not results or statistically established safety guarantees.

**Result against the proposal:** unchanged or increased flags would contradict the prediction that this boundary change reduces confabulation. Lower flags accompanied by failed recall or usefulness marks would also fail the experiment. Neither result would prove that every possible formatting change is ineffective.

**Shown — fix the measurement before judging that experiment:** the current recall scorer only searches for the stored value. I verified that it awards credit to “Your cat is not Biscuit” when the expected value is Biscuit. Keep that historical metric for comparison, but require correct attribution and an actual answer for the new pass mark. [Scorer](https://github.com/BenjaminHannan/learner/blob/e91007f3a4a72ce6cfd1fc4b8a36699d807af135/scripts/claude_mu405_talk.py#L129)

**Suggested training choice if the boundary experiment fails:** GLM distillation. Teach the model examples that answer the present turn, use relevant memories, and leave irrelevant memories alone. Your current rejection filter asks whether replies invent claims; it does not adequately require them to answer the present turn. Consequently, it can retain irrelevant or bland replies. Improve that acceptance definition before considering rejection sampling.

DPO should come later: it needs reliable preferences, and paired answers must share the **exact same input history**, not merely the same turn number. A failed GLM judging gate also would not establish that GLM-written teaching replies are trustworthy.

**Untested dose estimate:** 200 chats and roughly 1,000 teaching replies are enough for a pilot, not enough evidence to promise success. Four sampled continuations provide 4,000 replies but still only 200 underlying situations. Start with a small, fixed training budget—such as two epochs—and select further changes using separate development chats. Any next experiment needs fresh confirmation data.

In plain language: the model seems to hear an old conversation as though it is happening now. First test whether clearly marking today’s message helps. Make it pass both honesty and usefulness checks, so silence cannot win. If clearer formatting fails, teach it good examples of answering today’s question while remembering yesterday accurately.
