# 150d — case-sensitive hedges (design)

One-change fix for the bench132-152 miss on loop138b: the exp-150 subject
guard matches its hedge list case-insensitively, so the Title-Case song
name "I Believe I Can Fly" refuses as "i believe" and the 4-hop chain
answers short. The fix is case-sensitive hedge matching in a subclass of
loop138b; no loop138b/loop138 file edited.

## The rule

On the subject span, after the 129 strip (same two levels as the 150
guard), a hedge phrase counts only when its content word is lowercase as
typed, or the whole span is all-caps:

- "i think / i guess / i believe / i suppose": the content word is the
  word after "i". "I believe Kip Dune" (lowercase) stays a hedge;
  "I Believe I Can Fly", "I Think We're Alone Now" (capitalised) are
  names. Rationale: phones capitalise only the message's first letter, so
  a capitalised second word is Title-Case, not hedging.
- Single-word hedges (maybe, perhaps, probably, possibly, likely,
  presumably): the hedge word itself is the content word. Lowercase
  ("maybe Kip") stays a hedge; comma ("Maybe, Kip") stays a hedge; a
  2+-token remainder ("Maybe Kip Dune", "Maybe the capital of Peru")
  stays a hedge — these are the sealed exp-150 H-shapes, and phone-form
  hedging with a full phrase behind it must keep refusing; all-caps
  ("MAYBE KIP DUNE", "I BELIEVE TOM'S BOSS IS ANN") stays a hedge. Only a
  lone Title-Case token remainder ("Maybe Tomorrow", "Perhaps Love")
  reads as the title itself and stores. Anything else capitalised
  ("Maybe kip", "Maybe TOMORROW") conservatively refuses, exactly as
  before.
- Reporting openers, discourse-filler stripping, rule (c), and both
  clarify replies are byte-identical to 150.

## The possessive carve-out (the one judgment call)

The 137-upgrade path keeps the 150 case-insensitive veto for possessive
owners. "Maybe Tom's boss is Ann" (sealed redteam136 C081, group hedge,
expect nowrite) parses to owner "Maybe Tom", which is indistinguishable
from a title possessive ("Maybe Tomorrow's author") at the subject level
— same two tokens, same shape. Freeing one frees both; C081 would become
a polluted write ("Maybe Tom" entity), a junk-write regression on a sealed
case. So both refuse exactly as on loop138b. Title frees happen only on
the direct copula / of-shape paths ("X was created in…", "The author of X
is…"), where bench132-152 lives. Verified live: C081 nowrite with zero
stored triples; O11 pins the limitation (refused on both arms).

Adjacent scope (verified same-on-both, not changed): Maybe/Perhaps-led
VALUES ("famous for Maybe Tomorrow") hit the separate 139b value guard on
both arms — a different guard, out of this brief.

## Where it sits

`scripts/fable_fix150d_subjectguard.py` (`screen_subject_150d`,
`guard_action(s)`, `SubjectGuard150dMixin` — the rule). 
`scripts/fable_loop150d_agent.py` subclasses loop138b
(`Loop150dEars` + `Loop150dAgentLoop` with the 150d mixin,
`Loop150dMouth`/`Loop150dDaemon` unchanged) and repoints
`S150.screen_subject_150` process-wide at import so the inherited
137/144-upgrade and `_act` paths use the same rule (the process-wide
pattern loop138b itself uses for WM149/_APOS; this process only).
`Loop150dEars._upgrade137` pre-checks the 150 ci hedge on possessive
owners (the carve-out). L2 turn(), sleep145, settle daemon, and config
plug points are inherited unchanged.

## Evidence (registered, sealed pre-run, ledger P150d.1–6)

44-case probe 44/44 with 0 wrong writes (16 Title-Case names save/answer
like neutral twins; 16 real hedges byte-identical refusals; 12 others
identical); bench132-152 wrong→correct exact; bench per-item identical to
loop138b rows except that flip (0 new wrong); marks123 per-case 0 moves
(p3-l5z1 and rt81 FAIL labels inherited byte-identical); junk/143/
sessions 0 moves (rt136 135/7/3, cases150 57/57, f1 t14-only, cases139b
101/101, 143 106/11, sessions 129/2); slowest run 307 s. No post-seal
edits; no re-runs.

## What it means

Hedge-named titles teach and chain exactly like neutral names while every
real hedge shape refuses exactly as before — the change is invisible
everywhere except its target (one bench flip, zero suite moves).

## What it does not mean

No truth judgement; possessive-of-title still refuses (documented above);
Maybe-led values are 139b's scope; all-lowercase pollution still stores
by 150 design.
