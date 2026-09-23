# Merge 292: 291 + 266b (chain lift) + 268b (n-hop guard) + 293 (yes/no reader) — Muse build

**Base:** 291 (`scripts/claude_loop291_agent.py`,
`artifacts/claude-join291-20260923/loop291-config.json`, saved rows in
`artifacts/claude-join291-20260923/run/`). 291 = 138nb + 252c corrections
(252b + 258 + glue + 259, inner ears) + 260 openers (outermost turn) + 291
glue (R1 refusal-rerun + R2 junk-subject guards). Registered FAIL ruled
the new merge base (director, design/v3/30-modes/292-merge-onto-291.md).

**Added (all verified on their own; nothing else changes):**
- 266b chain-subject lift with multi-word names (registered FAIL ruled a
  merge candidate): `scripts/claude_loop266b_agent.py`,
  `scripts/claude_fix266b_detector.py` (ChainLift266bMixin, subclass of
  266's lift), `scripts/claude_fix266_chainlift.py`,
  `scripts/claude_loop266_agent.py`,
  `artifacts/claude-chain266b-20260923/`,
  `artifacts/claude-chain266-20260923/`.
- 268b n-hop direction guard on 138nb (registered FAIL ruled a merge
  candidate): `scripts/claude_loop268b_agent.py`,
  `scripts/claude_fix268_nhopdir.py` (question-side guard around
  `compose_n_hop`, process-local rebind),
  `artifacts/claude-nhop268b-20260923/`.
- 293 yes/no reader (verified PASS): `scripts/claude_loop293_agent.py`,
  `scripts/claude_fix293_yesno.py` (YesNo293Mixin, loop-level reader in
  the 154d slot), `artifacts/claude-yesno293-20260923/`.

Every piece file is copied unchanged from origin/builder-outbox and
imported read-only. No existing file is edited.

**Agent:** `scripts/claude_loop292_agent.py`, config
`artifacts/claude-merge292-20260923/loop292-config.json`.

**Evidence:** `artifacts/claude-merge292-20260923/` (PASSMARKS.md,
predicted_moves292.json, SEAL.sha256.txt, run/, RESULTS.md).

**Method note.** The interaction analysis below is written from reading
the piece sources (no blind-panel item was opened). The build follows
it; pilots on M1–M4 then confirm or correct it before the seal, and any
pilot-found interaction is added here only as a dated amendment (never
by editing a sealed file).

## Layer order (outermost first) and why

The three pieces live in three different slots, so they do not collide
structurally: 293's reader in the 154d slot (loop-level reader),
268b's guard on the n-hop composer frame, 266b's lift outermost on the
ears. Everything else is 291 unchanged.

### Instance (whole-turn) layers, outside in — unchanged from 291

| # | Layer | Why here |
|---|---|---|
| 1 | 291 glue `turn291` (R1 refusal-rerun) | Outermost, as on 291. Fires only on 229's exact no-save clarify on opener-led statements with no denial marker. None of the three pieces writes or returns that clarify shape, so R1 can only rerun turns 291 would rerun. |
| 2 | 260 `turn260` (openers) | As on 291: original runs first through the whole head (lift + guard + reader included), so every piece reading wins on the original when it acts; the stripped rest re-runs only when the original did not write and is itself a clarify-safe path. 260 never overrides a write. |
| 3 | 224c `turn224c` + 224 `turn224` | As on 291: exact-glued-decline rewrite only. No piece returns the glue, so every lift/canonical answer, every guarded backwards answer and every yes/no answer passes through untouched. |

### Loop classes (class MRO, outermost first)

| # | Layer | Why here |
|---|---|---|
| 4 | `Correct252LoopMixin` (instance class swap, outermost on the loop) | Unchanged mechanism from 291: records `_prev252` around `super().turn()` and routes `negate252` through 154f. It only records; the reply it records may now be a 293 yes/no answer or a lifted chain answer, exactly as it already records table/label answers on 291. |
| 5 | `YesNo293Mixin` (293's reader, in the 154d slot) | Same relative place as on 293's own stack (outermost loop reader over the base loop), now sitting inside 252's recorder and inside the 224/260/291 instance wrappers. It overrides `_listening_tick` only: peeks at the inbox head through `self.ears.hear` (the lifted, guarded ears); non-miss turns delegate byte-identical to `super()`; on the didn't-understand miss clarify it tries 154d's own parse+ground first (byte-identical replies/stage on everything 154d answers today), then the wider 293 parse+ground. Chain subjects, ambiguous owners, or/and-questions, "Is it true that…", lowercase subjects and statements all return None and keep the base reply. Read-only (resolve + current); the final record is a clarify the mouth renders verbatim. Never writes. |
| 6 | `Label138nbMixin` + 233/226/234/230c/227c + 212/216/209 + `Loop138jAgentLoop` chain | Unchanged from 291 (and 138nb below it). 209's `_act` backstop still sits below 252's `_act`. |

### Ears — 266b's lift outermost, 291's inner stack unchanged

Outer ears: `ChainLift266bMixin` outermost over 291's `Loop138nbEars`
base (same subclass pattern as 266b over 138m). Questions only, never
writes: on a `?`-turn holding a possessive chain (one- to three-word
notebook-name base, longest first; untaught multi-word bases pass
through with no shorter-span fallback; one-word/`my` bases take exactly
266's path), it dry-hears the placeholder-swapped question (ears hear
only parses to actions; no `_act`, so no write is possible), lifts only
on exactly one one-hop ask frame for the placeholder, and serves the
canonical possessive question ("Who/What is \<chain\>'s R?") through the
full stack. Every other turn passes through byte-identical.

Inner ears: `Comment258 > Merge252c > Boundary259 > Correct252 >
Loop138nEars(…)` unchanged from 291 (installed by the same instance
class swaps in the same order). On questions every 252c mixer returns
None and the turn falls to the base readers (and, on instances carrying
the swapped class, to the lift below them — same verdict, since the
lift is a pure function of turn text plus notebook names).

Install order in `_build292` (matters because the instance wrappers
capture `loop.turn` bound at install time): 292 classes (plain build,
no wrappers) → 252 loop/ears swap + 259 + glue252c + 258 → 224 → 224c
→ 260 last → 291 guards + turn291. The 252b screen, 232c rule, 228
guard and 268 guard are process-global rebinds installed at import and
at build, as on the piece arms.

### Composer global — 268b's guard (unchanged file, unchanged install)

`install_nhopdir268()` rebinds `fable_bench92_english_arm.compose_n_hop`
(the 228 pattern; no file edited). After the sealed composer returns
(start, rels), a reverse-shaped question about `start` (R1 whose / R2
married-to / R3 who-has-as / R4 what-verb, no forward marker) returns
None so the turn falls through unchanged to 190-reverse / 221-237 table
layers. Forward n-hop questions are untouched. It only suppresses a
frame; downstream clarify/ask actions on questions never write.

## Which piece claims each turn shape, and why

- **Plain chain verb question ("Where does A's boss live?", two-word A
  included).** The lift runs (outermost ears): the placeholder probe
  ("Where does Zqbex live?") yields exactly one one-hop ask frame
  through the 291 ears, so the canonical possessive is served from the
  notebook exactly as the base serves it (right, or an honest abstain
  when a link is missing). 293 never sees it: the peek hears
  non-miss acts, and the canonical is a wh-question its parser rejects
  anyway. The guard never sees it: the composer builds no reverse frame
  for a forward verb question. **Lift wins; 293 and guard pass.**
- **Yes/no about a chain ("Does Ana's boss live in Oslo?").**
  This is the turn two pieces could both claim, and the ruling is:
  **neither answers; it passes through to 291's reply.** Why, in order:
  (1) the lift probes "Does Zqbex live in Oslo?" through the ears, but
  Does-shapes are answered only at loop level (154d/293), so the ears
  probe yields no one-hop ask frame and the gate fails; (2) 293's parse
  then runs on the miss clarify and refuses structurally — every case
  (`_subject_ok`, scripts/claude_fix293_yesno.py:124-128) rejects any
  subject containing "'s", the Has path skips non-plain owners, and the
  Is path needs exactly one "'s". So no yes/no answer ever comes from a
  chain the lift did not resolve. The turn keeps 291's reply (Q2) with 0
  writes. (The mixed panel family covers these shapes; it is reported
  with no bar.)
- **Backwards question about a value with its own facts ("Whose R is
  V?", "Who is married to V?", "What did V write?").** The lift passes
  (no possessive-chain subject in the question, or its probe fails the
  gate since placeholder-about-V yields no one-hop frame). The composer
  builds the forward frame; the guard recognises the reverse shape
  about `start` and returns None; 190-reverse / table layers answer with
  the 138nb label. 293 passes (What/Who-shapes are not yes/no shapes).
  **Guard wins; lift and 293 pass.** The one documented hole travels
  with the piece: the "Who works for V?" employer shape is not in the
  guard's shape list (the 1 registered wrong on 268b), so that shape
  still walks forward on 292 — predicted, not new.
- **Plain yes/no about a taught fact ("Does A live in V?", "Is V the R
  of A?", multi-word names included).** Ears (lift + guard + base)
  return the miss clarify — the lift passes (no chain) and the composer
  builds no frame for Does/Is shapes. 293 parses a plain-name subject,
  grounds read-only, and answers Yes / No (single-valued keys only) /
  honest "I don't know". **293 wins; lift and guard pass.** 154d's own
  one-word Is-shapes keep 154d's byte-identical replies and stage tags
  (293 tries 154d first).
- **Yes/no after a correction or denial.** Corrections are statements:
  the lift passes (not "?"), 293 passes (no "?"), and 252c acts at the
  ears exactly as on 291 (removal through 154f, never 209). The later
  "?" turn then reads the updated notebook through 293. **252c wins the
  statement; 293 wins the question.** A taken-back value counts as not
  stored (293 rule), so denials verified on 293 stay denials on 292 as
  long as 252c removed them — every such case is already covered by the
  piece behaviours; pilots confirm the combination.
- **Corrections, denials, openers, tails (corrpanel291 shapes).**
  Unchanged from 291: 252c skips questions and 293 acts only on "?"
  misses, so no correction/denial turn is ever claimed by 293; the lift
  skips every non-"?" turn. 260 runs first on opener-led turns with the
  whole head (pieces included) and 291's glue sits outside it. **252c /
  260 / glue win exactly as on 291; the three pieces pass.**
- **Backwards question about a chain value; two-step after a
  correction; yes/no about a chain (mixed shapes).** Lift-first (ears),
  guard-second (composer), 293-last (loop miss only). A backwards
  question whose subject names a chain may lift to a canonical
  possessive when the probe gates; otherwise the guard decides the
  composer frame; otherwise 293 answers only a plain-name yes/no miss.
  No path writes (lift, guard and 293 are all write-free by
  construction; the canonical re-hear is ears-level only). Mixed items
  are reported with no bar.
- **Controls (plain who/what/where, one-hop, statements, table/backwards
  labels).** No piece claims them: the lift's probe gate fails (no
  chain, or the canonical equals what the base already does), the guard
  passes forward frames through, and 293 delegates every non-miss turn
  byte-identical. **Byte-identical to 291 by construction; the seal
  checks it per panel.**

## Standing rules (from the briefs, restated for the seal)

- A layer that answers from the notebook never overrides a gate that
  stops a write or a ghost answer (lift/guard/293 are read-only; 209's
  backstop stays below 252's `_act`; 260 never overrides a write).
- Questions never write (probe and canonical are ears-hear only; guard
  suppresses a frame; 293's final record is a clarify).
- 224c's decline stays the fallback (no piece returns the glue).
- Inferred facts are never stored (placeholder Zqbex is never taught;
  untaught multi-word bases never lift).
- A correction never removes a value the user did not deny (252c
  unchanged; 293 takes removals as given).
- A yes/no answer never comes from a chain the lift did not resolve
  (293 refuses "'s" subjects structurally; the lift gate needs exactly
  one one-hop ask frame for the placeholder).

## No new glue

The 291 glue (R1/R2) already covers the only 291-level interaction
(opener-led teaches vs 229/137). Phase-1 analysis finds no turn where
292 needs a new rule: the three pieces claim disjoint turn sets (lift:
wh-questions with chain subjects; guard: reverse-shaped composer
frames; 293: miss-clarify yes/no about plain names), and every overlap
resolves by pass-through order, never by a new rewrite. No
`scripts/claude_fix292_glue.py` is created; if pilots find otherwise, a
dated amendment here will say so before the seal (a new file, never an
edit).
