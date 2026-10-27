# Merge 138m: 138l plus the conversation line (Opus build)

**Base:** 138l (`scripts/claude_loop138l_agent.py` with `artifacts/claude-merge138l-20260922/loop138l-config.json`).

**Added:** 219, 230, 230b/230c, 227, 227b, 227c, 224/224c, 233 and 234.

**Agent:** `scripts/claude_loop138m_agent.py`. The config is `artifacts/claude-merge138m-20260922/loop138m-config.json`.

**Evidence:** `artifacts/claude-merge138m-20260922/` holds PASSMARKS.md, predicted_moves138m.json, SEAL.sha256.txt, run/ and RESULTS.md.

## Layer order (outermost first) and why

| # | Layer | Hook | Why here |
|---|---|---|---|
| 1 | 224c, then 224 (instance wrappers) | Replaces the exact glued decline (HONEST_DECLINE + DECLINE_SUFFIX, intent DECLINE) with one sentence: Q1, Q2 or S1. | On their own stack they wrap the whole built turn. They only touch the glue, so every other reply passes through untouched. |
| 2 | 233 `Loop233AgentLoop.turn` | Rewrites polite-negative wording at entry, before any layer reads the text. | Every layer below sees the plain question, exactly as on 233's own stack. |
| 3 | 226 `Source226Mixin` | Unchanged from 138l. | It sees the final reply of everything below it. |
| 4 | 234 `Loop234Mixin` | Post-swaps a whole-turn how-are-you match (0 writes) for the fixed reply. | Sits above identity and name. On a turn that both 234 and another layer claim, 234 wins. |
| 5 | NameLine230c (new) | Runs 219's `ground219_reply` in place of `G168.grounded_self_answer` for the turn, then runs 230, 230b and 230c's sealed turn bodies verbatim. | 230c's Yes/No rules are post-processing on top of 219's notebook check, as on its own stack. |
| 6 | Identity227c (new) | Swaps `L187.classify_self187` and `self187_answer` so the 227c gate runs first in 138j's notebook-miss branch. 187 still runs when 227c misses. | On a turn both claim, 227 wins: Ben's name and "My name is Premonition." (227b). |
| 7 | 212, 216, 209 and below | Unchanged from 138l. | |

The MRO is asserted at import. The classes are swapped in only while `build_agent138j` runs (process-local, restored in `finally`). The 228 source guard is installed at import and first in the daemon.

## Who wins where two pieces claim a turn

- **Identity (227/227b/227c) vs small talk (234) vs politeness (233).**
  - A probe of every dev-case text through each gate's own matcher found no text that both 234 and 227c claim. It also found no text that 233 rewrites and another gate claims.
  - By order, 234 would win (layer 4 is above 6).
  - On 234's own cases, the identity line answers the identity questions that were a glue decline in 234's stack: D064, D073, D074, D078, D079. For example, D078 "What is your name?" now gets "My name is Premonition."
- **Identity vs 187.** Nine texts are matched by both 227c and 187 ("What is your name?", "Who made you?", "What are you?", …). 227c wins.
- **224c stacked-decline fix vs other decline paths.**
  - 224c acts only on the exact glue.
  - 138j's 188 statement fallback runs earlier, inside the 138j turn. So on statement-shaped turns, 188's sentence already replaced the glue and 224's S1 never fires. This covers 224c's own B1 S1-01..32: 138m equals 138l there, which is 32 predicted moves in category base138l.
  - 138j's "I don't know anyone called X." also beats Q2 on Q2-03/04.
- **Name checks 230/230c vs 219's self-name.** These are one line: 219 grounds the D8 reply, and 230c post-processes it.
  - On other pieces' cases, the name line wins over identity. Examples: 227 m2:U04 "Do you remember my name?" → "Yes. Your name is Lark.", and U10.
  - The same happens on 227c c2t N02, N05, N10, N11, N12, N14, N18 and N34.
  - There are 14 moves in category nameline, listed by id in predicted_moves138m.json.
- **138l's 212/216 gates vs the name line.** This is the biggest known cost.
  - Several turns no longer reach the D8 route in 138l, so 219/230 never see them:
    - statement-shaped requests: "Tell me what my name is.", "Repeat my name.", "Remind me of my name.";
    - the cue-less question "What do people call me?".
  - They get 224's Q2, or 188's statement fallback.
  - This is 50 of 230's 52 moves (T: and U: variants):
    - 28 now get Q2 (224_on_base): WH07, WH18, WH20, WH23, WH24, IMP05, IMP06, IMP07, IMP14, IMP15, IMP16, IMP19, IMP26 and IMP28.
    - 22 now get 188's "I couldn't save that as a fact…" (base138l): IMP02, IMP04, IMP09, IMP11, IMP12, IMP20, IMP21, IMP22, IMP24, IMP25 and IMP31.
  - The same cost shows up on 227c c2u/c2t N09, N17, N23, N25, N31, N32 and N35.
  - The last two 230 moves (YN07) are plain glue → Q2.
  - 138i, j and k all route these turns to D8; only 138l's gates change that.
  - The fix would be a cue list shared between 216 and 219. That is a later piece, not part of this merge.

## Predicted-move categories (M1, 208 moves)

The categories are 224_glue, 224_on_base, base138l, nameline, identity and smalltalk234. Each is defined in `scripts/claude_138m_predict.py`, and the exact expected 138m record for every moved case is in predicted_moves138m.json.

## Known costs and observations (not fixed here)

1. **212/216 vs the name line.** See above.
2. **188 beats S1 on statement-shaped glue turns.**
3. **Q2 wording.** Q2 replaces the "I do not know…" wording on well-formed but unknown questions, e.g. "Where do I live?" → "I didn't understand that question — could you say it another way?". It is still counted as an abstain by rt143's own markers, so it changes 0 verdicts. The wording is less accurate than "I don't know".
4. **USER-key wording.** Since 138j, "Who made your notebook?" after "My name is Hedda." says "…USER's name is Hedda." This is a base issue that 138m did not cause.
5. **Two-sentence identity turns.** "Hi! What's your name?" still gives the old D8 reply in both 138l and 138m. This is a base issue.
6. **Name statements get the identity reply.** "Your name is Hedda." → "My name is Premonition." and "Is your name Hedda?" → "No, my name is Premonition." (227c RENAME). This is intended 227c behaviour.
