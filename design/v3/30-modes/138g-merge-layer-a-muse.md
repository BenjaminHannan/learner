# 138g — merge layer A: four verified fixes onto the clean stack (design)

One new file (`scripts/fable_loop138g_agent.py`) subclasses the frozen
loop138f stack. Every rule body is imported read-only; no existing file is
edited. Drivers are `scripts/fable_fix138g_*.py`.

## Step 1: one change per piece + composition

- 139e tail words: strip at `scripts/fable_fix139c_tail.py:46`
  (`strip_chat_tail`/`sanitize_action`), trigger+reply at
  `scripts/fable_fix139d_tail.py` (unknown_tail_split, clarify_text,
  CONNECTORS), gate at `scripts/fable_fix139e_tail.py:68-98`
  (LISTED_RELATIONS + check/guard_action), wired at
  `scripts/fable_loop139e_agent.py:66-80` (ears) and `:90-100` (_act).
  Composes with 138f with no collision (138f has no tail stage); the
  guard runs outside the 138f ears stack and outside its _act chain
  (mirroring 139e). Side effect by construction: guard_action always
  returns the 139c-sanitized action, so every teach also gets the 139c
  closed-list strip — intended (fixes "Ivy too"/"Leeds btw"/", actually").
- 137e framing: hypo list at `scripts/fable_fix137c_hypo.py:42-60`,
  wired at `scripts/fable_loop137c_agent.py:77-84`; say/hearsay groups at
  `scripts/fable_fix137d_frame.py:67-98+178`, wired at
  `scripts/fable_loop137d_agent.py:87-100`; hearsay unification at
  `scripts/fable_loop137e_agent.py:91-99` (HEARSAY_MSG from
  `scripts/fable_loop102_agent.py:70-71`). One new outermost ears stage
  (say > hearsay > hypo, mirroring 137d-then-137c), early clarify, else
  super. No _act/turn collision. The 137b discourse upgrade is NOT
  ported (it is a base-chain piece, not the verified change); the six
  M1 discourse-lead diffs this causes are listed in PASSMARKS.
- 158c wh-city: shapes+gate at `scripts/fable_loop158c_agent.py:84-108`
  (`rewrite_whcity`, pure over notebook triples via 158b helpers),
  wiring at `:115-150` (all-clarify gate, second pass, ask-only,
  never writes). New ears stage between framing and tail guard; no
  _act/turn collision. Adaptation (open): the sealed target "Where does
  X live?" is answered on 158c's agent by the 158b (d) table, which 138f
  lacks (verified live). Porting 158b's whrel base would exceed the
  verified change, so the stage tries the verbatim target first, then
  "What is X's city?" (city path, how the 158b base answers town shapes).
  Same gate, same never-write rule, same final replies on the probe.
- 168 self: gate at `scripts/fable_fix168_ground.py:129+221`, wiring at
  `scripts/fable_loop168_agent.py:50-115`. turn() is overridden with the
  168 body verbatim; 138f's turn is loop138 verbatim so the shape
  matches. No ears/_act collision.

Ears outer→inner: Frame137g > WhCity158cPort > Tail139eGuard >
Loop138fEars (unchanged). Loop _act: tail clarify > 138f chain. turn():
168 shape. Reasoner138d, IndexedLoopNotebook, 142 patches, doubt store,
sleep145 retrofit, settle daemon unchanged.

## Left out (and why)

- 157c title guard: the verified change (`TitleGuard157cMixin`) only
  blocks 157b's capitalised-filler strip
  (`fable_fix157b_capfiller.py:59`, via `:137`). 138f carries 157
  (lowercase fillers; "Hey Jude" explicitly protected) but not the 157b
  strip, so the guard alone is a no-op here; porting 157b+157c would drag
  an unrelated feature (capitalised-filler stripping with its own
  refusal widening). "Hey Jude's singer is Paul." therefore still saves
  under the full name, 138f-identical (G3-5).
- 160c two-hop: the verified change (`TwoHop160cMixin`) intercepts 160b's
  bare-correction resolve (`fable_fix160b_laststated.py:141-151`). 138f
  has no 160/160b machinery (no bare_correct tag, no last-stated
  memory), so the interceptor alone is a no-op; porting 160b+160c would
  drag the unrelated bare-correction feature.

## Known edges

- Redteam136 C089 WRONG-WRITE→OK ("Suppose Tom's boss is Ann." now
  hypo-refused) is an improvement move, predicted.
- p4 P4-09 goes nonpass by harness strictness (expects the taught text
  echoed); the stored triple is the clean correct value.
- 158c O-arm: six 158b-base shapes clarify 138f-identically; O06/O10
  show the intended 168 grounding.
- l6 `replied_before_kill` and daemon-workdir hashes are
  timing-volatile; only verdict/reply fields are predicted.
