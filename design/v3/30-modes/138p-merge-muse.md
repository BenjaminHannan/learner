# Merge 138p: 138m + 260 (openers) + 252c (corrections) — Muse build

**Base:** 138m (`scripts/claude_loop138m_agent.py`,
`artifacts/claude-merge138m-20260922/loop138m-config.json`,
saved rows in `artifacts/claude-merge138m-20260922/run/`).

**Added:**
- 260 openers/greetings (PASS): `scripts/claude_loop260_agent.py`,
  `scripts/claude_fix260_openers.py`, `artifacts/claude-openers260-20260922/`
  (built on 138m).
- 252c corrections (registered FAIL, ruled a merge candidate):
  `scripts/claude_loop252c_agent.py`, `scripts/claude_fix252c_merge.py`,
  `scripts/claude_fix258_comment.py`, `scripts/claude_fix259_boundary.py`,
  `artifacts/claude-merge252c-20260922/` (built on 138k, from 252b/252).

**Agent:** `scripts/claude_loop138p_agent.py`, config
`artifacts/claude-merge138p-20260923/loop138p-config.json`.

**Evidence:** `artifacts/claude-merge138p-20260923/` (PASSMARKS.md,
predicted_moves138p.json, SEAL.sha256.txt, run/, RESULTS.md).

**Method note.** The brief asks for this interaction analysis before the
build is final. The layer order below is written from reading the piece
sources (no blind-panel item was opened). The build follows it; pilots
on M1–M6 then confirm or correct it before the seal, and any pilot-found
interaction is added here only as a dated amendment (never by editing a
sealed file).

## Layer order (outermost first) and why

### Instance (whole-turn) layers, outside in

| # | Layer | What | Why here |
|---|---|---|---|
| 1 | 260 `turn260` (`install_openers260`) | Strips ≤2 listed openers/greetings and runs the rest through the whole head; bare greetings get the head's "Hello." reply; opener-comma write guards at inner ears and `_act`. | Same place as on 260's own stack: outermost, outside 224/224c, so a stripped turn runs through the entire head exactly as if typed alone. Nothing else changes. |
| 2 | 224c `turn224c` + 224 `turn224` | Exact glued decline → one sentence per turn type; Q1 only when confirmed. | Same place as on 138m (inside 260, outside the class turn). They only touch the exact glue, so every 252c/260 reply passes through untouched. |

### Loop classes (class MRO, outermost first)

| # | Layer | Why here |
|---|---|---|
| 3 | 233 `Loop233AgentLoop.turn` | Rewrites polite negatives at entry, as on 138m. Every layer below (incl. 252c's ears) sees the plain question. |
| 4 | 226 `Source226Mixin` | Unchanged from 138m; sees the final reply of everything below. Read-only classification. |
| 5 | 234 `Loop234Mixin` | Post-swap on whole-turn how-are-you with 0 writes, above name/identity, as on 138m. |
| 6 | `NameLine230cMixin` (219 + 230/230b/230c) | As on 138m. |
| 7 | `Identity227cMixin` (227/227b/227c ahead of 187) | As on 138m. |
| 8 | `Correct252LoopMixin` (spliced just above `Loop138mAgentLoop`) | Remembers the previous reply (`_prev252`, for contextual denial/correction) and routes the `negate252` action through 154f's retraction path. It wraps the whole 138m class turn, inside the 224/260 instance wrappers, so `_prev252` sees the replies the user actually got. |
| 9 | 212, 216, 209 loop layers, then `Loop138jAgentLoop` chain | Unchanged from 138m. 209's `_act` backstop sits below 252's `_act`, so a 252 removal (which 252's `_act` handles without calling `super()`) never passes through 209. |

### Inner ears (outermost first)

`Comment258 > Merge252c > Boundary259 > Correct252 > Loop138lEars`
(209 screen > 223 bypass > 138j layer C > 222/215 …).
This is 252c's own order (258 > glue > 259 > 252), with the base
swapped from 138k's plain 138j ears to 138m's 138l ears. 252 still sees
the raw turn first (outermost), exactly as on its own stack; what
`super().hear()` does underneath changes (see below).

Install order in `_build138p` (matters because the instance wrappers
capture `loop.turn` bound at install time): 138m classes →
252 loop/ears class swaps + 259 + glue + 258 → 224 → 224c → 260 last.
The 252b value screen (`install_screen252b`, a module-global rebind) is
installed at import, as on 252c.

## What 252c never ran with (built on 138k, not 138m)

Every 138l layer and every 138m layer:

- **138l:** 209 write screen (ears outermost + loop `_act` backstop),
  212 statement gate, 216 decline-cue gate, 222 a/an of-teach gate (with
  the 215 of-teach rewrite), 223 cant-do negation-screen bypass,
  226 source questions.
- **138m:** 219 D8 notebook check, 230/230b/230c name-line rules,
  227/227b/227c identity sheet, 224/224c one-sentence declines,
  233 polite-negative rewrite, 234 how-are-you fixed reply.

## Which turns both could claim, and who wins

- **224c declines vs 252 contextual denial ("That's wrong.").**
  Different stages: 252 acts at ears level using `_prev252` (the
  *previous* turn's reply); 224c rewrites only the exact glued decline
  in the *current* reply. If 252 claims the turn the reply is not glue
  and 224c passes through; if 252 passes (no one-fact context) the base
  glue stands and 224c rewrites it. **224c's decline stays the
  fallback.** No overlap by construction.
- **227c identity vs 252.** 252 never touches questions
  (`is_question252` → `None`), and identity answers are reply-only with
  0 writes. Name statements ("Your name is Hedda." → 227c RENAME) carry
  no negation, no 252 prefix, no pronoun-now shape, so 252's `_hear252`
  returns `None`. **Identity wins; 252 passes.**
- **230c name line vs 252.** Name checks are questions (252 skips).
  "My name is X." matches 252's `_ME_RX` and stays on the base confirm
  flow (rule 7). **Name line wins; 252 passes.**
- **233/234 fixed replies vs 252.** 233 rewrites questions (252 skips
  questions). 234 claims whole-turn how-are-you with 0 writes; those
  turns are questions or zero-write small talk, never 252 denials.
  **234/233 win their turns; 252 passes.**
- **212/216 gates vs 252.** The gates swap `route127` for the turn
  (self-router path); 252 acts earlier at ears `hear` and returns its
  own actions directly, so a claimed correction/denial never reaches
  the router. Unclaimed turns behave exactly as on 138m. **252 wins
  claimed turns; gates keep everything else.**
- **209 write screen vs 252.** 252's own actions (`negate252`,
  `clarify`-asks) return without calling `super().hear()`, so 209's
  ears screen never sees them; 252's `_act` handles `negate252`
  without calling `super()._act()`, so 209's loop backstop never sees
  it. 209 only affects 252's *canonical hand-offs* (`_read252` /
  `_canon252` re-parse a positive/canonical sentence through the full
  138m ears, now including 209/223/222). **A layer that answers from
  the notebook never overrides a gate that stops a write: removals go
  through 154f's own retraction path, unchanged.**
- **226 sources vs 252.** 226 only classifies the final reply.
  Read-only; no write change possible.
- **222 teaches vs 252 corrections (the one real overlap).**
  252's explicit-correction path hands the canonical sentence
  "No, S's R is Z." to the base ears. On 252c the base was plain 138j
  ears; on 138p it is 138m ears including the 222 a/an gate, the 215
  rewrite, the 223 bypass and the 209 screen. A canonical correction
  whose value has an "a/an … of" shape, a cant-do verb, or a screened
  value may parse differently (ask instead of correct, or vice versa).
  Every such case is listed by id in the sealed predictions (M1); the
  pilot decides the exact records.
- **233 rewrite vs 252 prefixes.** 233 rewrites the raw text before
  252 sees it. Polite-negative corrections ("Couldn't you mean …?")
  are questions → 252 skips either way. Statement corrections pass
  233 unchanged. No overlap found in the piece dev texts; pilots
  confirm.

## 260 vs 252c: an opener in front of a correction or denial

Example: "Oh, actually Kim's boss is Fig, not Moss."

**260 runs first (outermost), 252c runs inside it — on both paths:**

1. The *original* turn runs first through the whole head, 252c
   included, with 260's write guard on. 252's own prefix lists already
   contain "oh" and "actually" as correction signals, so where 252c
   acts on the original, its write/removal stands and 260 keeps the
   original reply verbatim (260 never overrides a write).
2. Only when the original did not write does 260 strip the opener
   ("Oh,") and run the rest ("Actually Kim's boss is Fig, not Moss.")
   as if typed alone. 252c then sees the clean rest and performs the
   same correction it performs on its own dev items.
3. "Actually" is strippable by 260 but the original runs first, so
   252c's own correction reading of "Actually, …" always wins when it
   acts — the same reason 260 keeps pretend markers ("suppose") on the
   guard-only list.

**Questions never write:** a "?" rest run only lets ask/clarify/
namecheck/unsure pass `_act` (260's `question_rest` block), so a
correction-shaped question can never store through the rest path.
**Inferred facts are never stored** (252 rule 6, unchanged).
**A correction never removes a value the user did not deny** (252
removes only the exact stored match of the denied span, now with
258's cut and 259's boundary; the glue only fires on turns 258
shortened).

## Standing rules (from the brief, restated for the seal)

- A layer that answers from the notebook never overrides a gate that
  stops a write or a ghost answer.
- Questions never write.
- 224c's decline stays the fallback.
- Inferred facts are never stored.
- A correction never removes a value the user did not deny.
