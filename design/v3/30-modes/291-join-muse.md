# Merge 291: 138nb + 260 (openers) + 252c (corrections) — Muse build

**Base:** 138nb (`scripts/claude_loop138nb_agent.py`,
`artifacts/claude-merge138nb-20260923/loop138nb-config.json`, saved rows in
`artifacts/claude-merge138nb-20260923/run/`). 138nb = 138n + one outermost
reply-text rule (label 190-reverse subject answers
" (worked out backwards)"; VERIFIED PASS).

**Added (same pieces, same order as 138p, on 138nb instead of 138m):**
- 260 openers/greetings (PASS): `scripts/claude_loop260_agent.py`,
  `scripts/claude_fix260_openers.py`, `artifacts/claude-openers260-20260922/`
  (built on 138m).
- 252c corrections (registered FAIL, ruled a merge candidate):
  `scripts/claude_loop252c_agent.py`, `scripts/claude_fix252c_merge.py`,
  `scripts/claude_fix258_comment.py`, `scripts/claude_fix259_boundary.py`,
  `artifacts/claude-merge252c-20260922/` (built on 138k, from 252b/252).

**Agent:** `scripts/claude_loop291_agent.py`, config
`artifacts/claude-join291-20260923/loop291-config.json`.

**Evidence:** `artifacts/claude-join291-20260923/` (PASSMARKS.md,
predicted_moves291.json, SEAL.sha256.txt, run/, RESULTS.md).

**Why this join exists.** 138p (138m + 260 + 252c) passed M1–M6 and failed
M7 only on reply-wording rows: where 252c's 138k base says the glued long
decline, 138p says 224's Q2 / 138m's save-failure. 290-diag traced that
wording to exp 224's decline rewrite; the director ruled (board 06:50):
keep 224's wording, predict those moves by id, and re-prove the PASS claim
on a fresh blind correction panel (corrpanel291). 291 repeats the 138p
join on top of 138nb, so it also carries 138nb's table stages and the
190-answer label. The join adds no new behaviour.

**Method note.** The interaction analysis below is written from reading
the piece sources (no blind-panel item was opened). The build follows it;
pilots on M1–M6 then confirm or correct it before the seal, and any
pilot-found interaction is added here only as a dated amendment (never by
editing a sealed file).

## Layer order (outermost first) and why

### Instance (whole-turn) layers, outside in

| # | Layer | What | Why here |
|---|---|---|---|
| 1 | 260 `turn260` (`install_openers260`) | Strips ≤2 listed openers/greetings and runs the rest through the whole head; bare greetings get the head's "Hello." reply; opener-comma write guards at inner ears and `_act`. | Same place as on 260's own stack and on 138p: outermost, outside 224/224c, so a stripped turn runs through the entire head exactly as if typed alone. Nothing else changes. |
| 2 | 224c `turn224c` + 224 `turn224` | Exact glued decline → one sentence per turn type; Q1 only when confirmed. | Same place as on 138m/138nb/138p (inside 260, outside the class turn). They only touch the exact glue, so every 252c/260/table/label reply passes through untouched. Director ruling kept: unparsed "?" turns get Q2. |

### Loop classes (class MRO, outermost first)

| # | Layer | Why here |
|---|---|---|
| 3 | `Correct252LoopMixin` (dynamic class swap, outermost on the loop) | Remembers the previous reply (`_prev252`, for contextual denial/correction) and routes the `negate252` action through 154f's retraction path. It wraps the whole 138nb class turn, inside the 224/260 instance wrappers. Its `turn` only records and returns the reply unchanged, so the label applied inside still reaches the user verbatim, and `_prev252` records the labelled reply the user actually got. |
| 4 | `Label138nbMixin` (138nb's own outermost class) | Appends " (worked out backwards)" to subject-naming replies whose answering stage is exactly `loop190-reverse`. Text only; no writes; abstains untouched. Runs inside Correct252's recorder and inside 224/260, so labelled replies are recorded and pass the wrappers unchanged (a labelled reply is never the exact glue). |
| 5 | 233 `Loop233AgentLoop.turn` | Rewrites polite negatives at entry, as on 138m/138nb. Every layer below (incl. 252c's ears and the table readers) sees the plain question. |
| 6 | 226 `Source226Mixin` | Unchanged; sees the final reply of everything below. Read-only classification. |
| 7 | 234 `Loop234Mixin` | Post-swap on whole-turn how-are-you with 0 writes, above name/identity, as on 138m/138nb. |
| 8 | `NameLine230cMixin` (219 + 230/230b/230c) | As on 138m/138nb. |
| 9 | `Identity227cMixin` (227/227b/227c ahead of 187) | As on 138m/138nb. |
| 10 | 212, 216, 209 loop layers, then `Loop138jAgentLoop` chain | Unchanged from 138m/138nb. 209's `_act` backstop sits below 252's `_act`, so a 252 removal (which 252's `_act` handles without calling `super()`) never passes through 209. |

### Inner ears (outermost first)

`Comment258 > Merge252c > Boundary259 > Correct252 > Loop138nEars`
(221c QNorm > FirstName138n(+G1) > 221b StoredRel > 237 TableAsk > 229
TableTeach(+G2) > Loop138lEars(209 > 223 > layer C > 222/215 …) with
232c Verb232Mixin after 174/165, before 167b).

This is 252c's own order (258 > glue > 259 > 252), with the base swapped
from 138k's plain 138j ears to 138nb's 138n ears. 252 still sees the raw
turn first (outermost), exactly as on its own stack; what `super().hear()`
does underneath changes (see below).

Install order in `_build291` (matters because the instance wrappers
capture `loop.turn` bound at install time): 138nb classes (plain build,
no wrappers) → 252 loop/ears class swaps + 259 + glue + 258 → 224 → 224c
→ 260 last. The 252b value screen (`install_screen252b`, a module-global
rebind) is installed at import, as on 252c/138p.

## What 252c never ran with (built on 138k, not 138nb)

Every 138l layer, every 138m layer (same list as 138p), plus every 138n
reading layer and 138nb's label:

- **138l:** 209 write screen (ears outermost + loop `_act` backstop),
  212 statement gate, 216 decline-cue gate, 222 a/an of-teach gate (with
  the 215 of-teach rewrite), 223 cant-do negation-screen bypass,
  226 source questions.
- **138m:** 219 D8 notebook check, 230/230b/230c name-line rules,
  227/227b/227c identity sheet, 224/224c one-sentence declines,
  233 polite-negative rewrite, 234 how-are-you fixed reply.
- **138n (reading line, new vs 138p):** 221c question normalisation,
  236 first-name resolution (+G1 particle guard), 221b stored-relation
  fallback, 237 relation-table v1.1 question reader, 229 table teaches
  (+G2 no-save reason), 232c multi-word verb names (+232c subject rule).
- **138nb:** the 190-reverse label (outermost class rule, text only).

## Which turns both could claim, and who wins

- **224c declines vs 252 contextual denial ("That's wrong.").**
  Different stages: 252 acts at ears level using `_prev252` (the
  *previous* turn's reply, now the labelled reply); 224c rewrites only
  the exact glued decline in the *current* reply. If 252 claims the turn
  the reply is not glue and 224c passes through; if 252 passes (no
  one-fact context) the base glue stands and 224c rewrites it. **224c's
  decline stays the fallback.** No overlap by construction (as 138p).
- **227c identity vs 252.** 252 never touches questions
  (`is_question252` → `None`), and identity answers are reply-only with
  0 writes. Name statements ("Your name is Hedda." → 227c RENAME) carry
  no negation, no 252 prefix, no pronoun-now shape, so 252's `_hear252`
  returns `None`. **Identity wins; 252 passes** (as 138p).
- **230c name line vs 252.** Name checks are questions (252 skips).
  "My name is X." matches 252's `_ME_RX` and stays on the base confirm
  flow (rule 7). **Name line wins; 252 passes** (as 138p).
- **233/234 fixed replies vs 252.** 233 rewrites questions (252 skips
  questions). 234 claims whole-turn how-are-you with 0 writes; those
  turns are questions or zero-write small talk, never 252 denials.
  **234/233 win their turns; 252 passes** (as 138p).
- **212/216 gates vs 252.** The gates swap `route127` for the turn
  (self-router path); 252 acts earlier at ears `hear` and returns its
  own actions directly, so a claimed correction/denial never reaches
  the router. Unclaimed turns behave exactly as on 138nb. **252 wins
  claimed turns; gates keep everything else** (as 138p).
- **209 write screen vs 252.** 252's own actions (`negate252`,
  `clarify`-asks) return without calling `super().hear()`, so 209's
  ears screen never sees them; 252's `_act` handles `negate252`
  without calling `super()._act()`, so 209's loop backstop never sees
  it. 209 only affects 252's *canonical hand-offs* (`_read252` /
  `_canon252` re-parse a positive/canonical sentence through the full
  base ears, now the 138n stack including 209/223/222). **A layer that
  answers from the notebook never overrides a gate that stops a write:
  removals go through 154f's own retraction path, unchanged** (as 138p).
- **226 sources vs 252.** 226 only classifies the final reply.
  Read-only; no write change possible (as 138p).
- **222 teaches vs 252 corrections (the one real 138p overlap, kept).**
  252's explicit-correction path hands the canonical sentence to the
  base ears. On 291 the base is the 138n stack (222 a/an gate, 215
  rewrite, 223 bypass, 209 screen, plus the readers below). A canonical
  correction whose value has an "a/an … of" shape, a cant-do verb, or a
  screened value may parse differently. Every such case is listed by id
  in the sealed predictions (M1); the pilot decides the exact records.
- **233 rewrite vs 252 prefixes.** 233 rewrites the raw text before
  252 sees it. Polite-negative corrections ("Couldn't you mean …?")
  are questions → 252 skips either way. Statement corrections pass
  233 unchanged. No overlap found in the piece dev texts; pilots
  confirm (as 138p).

## 138nb's table/label stages vs 252c's correction layers (new vs 138p)

- **Table question readers (221c, 236, 221b, 237) vs 252.**
  252's ears mixins sit outermost on the inner ears and return `None`
  on questions; the readers act only on turns ending in "?" and emit
  only ask/clarify actions (questions never write). On a "?" turn 252
  passes and the readers answer exactly as on 138nb. On a statement
  correction the readers pass (no "?") and 252 acts exactly as on
  252c/138p. **No turn is claimed by both: "?" goes to the table,
  correction-statements go to 252.** The one place 291 differs from
  138p by design: a backwards/table question 138p declined, 291 answers
  (with the label where the stage is 190-reverse). Every such case is
  predicted by id in M1.
- **229 table teaches vs 252.** 229 fires only on statements the whole
  138m ears stack missed (not-understood clarify only). 252 acts
  earlier at ears `hear` and returns its own actions, so a claimed
  correction/denial never reaches 229; gates that stop a write (209
  split clarify, 222/215 refusals, 167b no-write clarify, 150 subject
  veto) return their own clarify, never the not-understood one 229
  needs. Unclaimed statements behave exactly as on 138nb. **252 wins
  claimed turns; 229 keeps everything else.**
- **232c verb names vs 252.** 232c reads verb turns (questions and
  statements) for multi-word names; 252's correction frames carry the
  names 232c was sealed on. 232c never writes by itself (it re-hears
  through the stack); where a canonical correction re-parse now
  resolves a two-word name that 138k's ears missed, the correction
  still performs the same removal/add the pilot records by id.
- **190-reverse + label vs 252.** 190 sits inside the base ears below
  252; 252 skips questions, so backwards questions ("Whose R is V?",
  "Who lives in V?") reach 190 and the label appends afterwards,
  exactly as on 138nb. Statement corrections never hit 190. **No
  190/table answer is lost on 291; the label lands exactly where 138nb
  puts it.**
- **224/224c vs table/label.** 224 rewrites only the exact glue; table
  and 190 answers are never glue, so they pass through (label first,
  then the wrappers see a non-glue reply). Unclaimed "?" turns with
  glue get Q2, as on 138m/138p — the 15 M7 wording rows stay moved,
  predicted by id.

## 260 vs 252c: an opener in front of a correction or denial

Example: "Oh, actually Kim's boss is Fig, not Moss."

**260 runs first (outermost), 252c runs inside it — on both paths**
(same as 138p):

1. The *original* turn runs first through the whole head, 252c and the
   table readers included, with 260's write guard on. 252's own prefix
   lists already contain "oh" and "actually" as correction signals, so
   where 252c acts on the original, its write/removal stands and 260
   keeps the original reply verbatim (260 never overrides a write).
2. Only when the original did not write does 260 strip the opener
   ("Oh,") and run the rest ("Actually Kim's boss is Fig, not Moss.")
   as if typed alone. 252c then sees the clean rest and performs the
   same correction it performs on its own dev items.
3. "Actually" is strippable by 260 but the original runs first, so
   252c's own correction reading of "Actually, …" always wins when it
   acts.

**260 vs table readers.** The original runs first with the table
included: a table question with an opener ("Hey, whose boss is Fig?")
is answered by the table (+label) on the original when the head gives
a non-clarify reply; else the stripped rest re-runs through the same
head. Either path gives the same answer 138nb gives without the
opener. Bare greetings get the head's "Hello." reply (the readers pass
on non-questions).

**Questions never write:** a "?" rest run only lets ask/clarify/
namecheck/unsure pass `_act` (260's `question_rest` block), so a
correction-shaped question can never store through the rest path.
**Inferred facts are never stored** (252 rule 6, unchanged).
**A correction never removes a value the user did not deny** (252
removes only the exact stored match of the denied span, now with
258's cut and 259's boundary; the glue only fires on turns 258
shortened).

## Standing rules (from the briefs, restated for the seal)

- A layer that answers from the notebook never overrides a gate that
  stops a write or a ghost answer.
- Questions never write.
- 224c's decline stays the fallback.
- Inferred facts are never stored.
- A correction never removes a value the user did not deny.
