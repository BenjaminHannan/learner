# 260 — openers and greetings are never part of a fact (Opus build, 2026-09-22)

Base: 138m (`scripts/claude_loop138m_agent.py` + `artifacts/claude-merge138m-20260922/loop138m-config.json`).
One change: `scripts/claude_fix260_openers.py`, installed outermost by `scripts/claude_loop260_agent.py`
(`Loop260Daemon`, SrcGuardMixin228 first). Artifacts: `artifacts/claude-openers260-20260922/`.

## Why the existing lists do not fire on 138m (diagnosis)

1. **137b (`DISCOURSE137B`)** lives only in `Loop137bEars` (the 137b/c/d/e line). That ears class was never
   merged into the 138 line, so 138m never runs it.
2. **150 (`FILLER_OPENERS`)** runs inside 138b's ears (`S150.guard_actions`) *before* 138b's fix137 possessive
   upgrade. The upgrade builds its own teach afterwards and calls `screen_subject_150` only for a yes/no
   verdict, throwing away the cleaned name. So "So, Pell's boss is Rhoda." stores the subject "So, Pell".
   "please" is not in the 150 list at all ("Please, Kestrel" is stored; verifier probe D10).
3. **157 (`Filler157Mixin`)** sits low in the ears MRO. Its re-parse of the remainder reaches only the layers
   below it, so verb teaches (167/167d), copula teaches (172), question forms (158) and every loop-level handler
   never see the remainder. It strips one filler only, has no "please"/"hi", and does not treat "!".
4. **Greetings**: no layer strips "Hi!" before a question; 156b small talk fires only when every token is
   small-talk vocabulary, so "hello there" falls through to the save-failure reply.

Patching each list in place would mean editing sealed files (not allowed) and would still leave the ordering
problem. So the fix is one outermost layer on the whole built turn.

## The rule (one closed list, fixed before the panel was opened)

- **Lists**: greetings (hello, hi, hey, hiya, heya, howdy, good morning/afternoon/evening; a greeting may carry up to
  two of "there"/"again"/"Premonition"); multi-word openers (by the way, just so you know, for the record, fun fact,
  one more thing, quick one, oh yeah, oh and, okay so, ...); single words (so, well, oh, also, and, but, okay, ok,
  alright, right, please, actually, anyway, btw, fyi, listen, look, ...); hesitations (um, uh, er, hmm, ...).
  Guard-only words (suppose, imagine, say, no, wait, sorry, anyhow) are never stripped, because stripping
  "Suppose" would turn pretend into a fact. Words that are also names (Will, Hope, Joy, May, Grace, Mark, Rose, ...)
  are not listed. At most 2 openers are stripped.
- **Original first.** The original turn runs first with the write guard on. If it wrote, it stands. If the head
  did not clarify and there was no punctuation, it stands. Otherwise the state is restored and the rest runs as if
  typed alone; if the head clarifies on the rest, the original reply stands. So the head's own readings (e.g. its
  "Actually, ..." correction reading) always win when they act.
- **Hard / soft mode (no punctuation after the opener).** Soft = the next word is capitalised and the opener is a
  greeting or 2+ capitalised words follow ("Hey Jude", "So Long Summer", "So Bram Kite"): the original is kept
  whenever the head acts (can't tell a title or a vocative from an opener). Hard = everything else: during the
  original run a teach/correct whose subject starts with this opener is turned into the ears' clarify, so the rest
  runs instead ("So Pell's boss is Rhoda." stores Pell, not "So Pell").
- **Write guard.** No stored subject may start with a listed opener followed by a comma (always), nor, in a
  hard-mode turn's original run, with that turn's opener followed by any separator ("So Pell", "Hi. Tom")
  (inner ears → the ears' own clarify; again at `_act`).
- **Questions.** In a rest run of a "?" turn only ask/clarify/namecheck/unsure actions pass `_act`: a question never
  writes through the rest path.
- **Bare greetings** get exactly the head's reply to "Hello." (computed once, state undone).
- **State undo.** An unused run is undone by restoring every plain attribute of the loop and its helper objects;
  the notebook is never written on an undone path (checked by the notebook event count).

## Overlaps

- **221c** (question normalisation on the 221 table line; drops a leading "so,"/"um,"/"hey," and trailing fillers
  from questions) is not in 138m; it is being merged in 138n. If 260 is later stacked on 138n both would strip a
  leading filler on a question; 260 runs the original first, so 221c's reading would act first and 260 would keep it.
- **137b / 150**: every word of DISCOURSE137B and of 150's FILLER_OPENERS is in the 260 lists (checked by import);
  the pretend markers (suppose, imagine, say) are guard-only here.
- **150/157**: still run inside 138m unchanged; 260 only acts when they leave an opener in a subject or fail.
- **255** (fixed-reply text mixin on 138m) and **258/259** (on 252b): different files; 260 wraps the turn outside
  224/224c, so a 255-style reply mixin would sit inside it.

## Known limits (registered, see PASSMARKS)

- Greeting + one capitalised word with no punctuation ("Hey Pell's boss is Rhoda.") keeps 138m's reply and stores
  "Hey Pell" — indistinguishable from the title "Hey Jude's writer is Fenn.".
- A no-comma opener before a 2+-word name ("So Bram Kite's boss is Rhoda.") keeps 138m's behaviour (junk "So Bram Kite").
- rt136 C122 "Hi. Tom's boss is Ann." now stores Tom boss Ann (138m stored "Hi. Tom"); rt136 wants no write for
  multi-sentence turns, so its verdict stays WRONG-WRITE and suitediff labels the changed write "new junk write".
