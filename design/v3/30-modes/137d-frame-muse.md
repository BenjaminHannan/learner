# 137d — non-assertive framings never write (design)

Exp 137's upgrade accepts 2-4 Title-case tokens as one possessive
subject. Loop137c guards sentence-initial hypotheticals
(`design/v3/30-modes/137c-hypo-muse.md`; marker list at
`scripts/fable_fix137c_hypo.py:48-60`). But non-assertive framings
still write: on loop137c "Supposedly Kim's boss is Lee." is not
hypothetical, so `Loop137cEars.hear` falls through at
`scripts/fable_loop137c_agent.py:84` into the base pipeline, which
parses "Supposedly Kim" as a subject and SAVES the junk triple
`[Supposedly Kim,boss,Lee]` (live-verified pre-seal). "Say Kim's boss
is Lee." saves `[Kim,boss,Lee]` (only "say that" is a 137c marker).
Director probe 05:16 on loop137c. Ben's ruling (2026-09-22): "Say X..."
is pretend (or a request for the agent to say it), never a fact;
hearsay is never a fact.

## The one change

`Loop137dEars` subclasses loop137c's ears
(`scripts/fable_loop137d_agent.py`, new files only, no loop137c file
edited) and checks `frame_kind(turn)` FIRST -- before any panel read,
before the unchanged loop137c pipeline (hypo guard + base) runs. A
turn whose first words (after optional case-insensitive fillers
ok/so/and plus punctuation, repeatable) are a closed-list frame marker
-- (a) say-group: say, say that (longest-first); (b) hearsay-group:
supposedly, apparently, allegedly, reportedly, rumor has it, rumour
has it, I heard, I heard that, they say, they say that, people say
(longest-first), all fixed in `scripts/fable_fix137d_frame.py` before
any panel read -- never reaches any teach path. Say-group turns return
one clarify carrying the sentence echoed without the marker plus
" (I'm treating that as pretend, so I won't save it.)"; hearsay turns
return one clarify carrying exactly "That sounds like hearsay, so I
won't save it as a fact. If it's true, just tell me plainly." Both are
rendered verbatim by the normal `_act`/mouth path with zero writes and
zero self-routing (neither reply holds "didn't understand"). Later
questions in the same session therefore answer only from real saved
facts -- there is nothing else to read, because the framed turn stored
nothing. Everything else falls through to `super().hear()`
byte-identical.

## Deliberate scope edges

- "say that" moves from the 137c pretend reply to the say echo reply
  by design (never writes either way); no regression input starts with
  it (pre-seal scans clean), so the only observable change is the new
  probe. Bare "Say." (empty remainder) replies with just the
  parenthetical, still 0 writes.
- A marker glued to a possessive 's is a name, not a framing: "Say's
  boss is Kim." / "They Say's mother is Beth." fall through exactly as
  on 137c (apostrophe is never a trailing boundary, same rule as
  137c). Marker words later in the sentence ("Kim's song is Say My
  Name", "Kim's book is Apparently") never match: only turn-initial
  position counts.
- Hearsay turns that loop137c already declined with 0 writes ("I heard
  ...", "Apparently ...") move to the exact hearsay sentence by design
  (verdicts unchanged; predicted reply-only moves in cases150/rt136).
- On loop137c "Supposedly ..." SAVED junk (`[Supposedly Kim,boss,Lee]`);
  on 137d it is hearsay: exact reply, 0 writes. "Okay" is not a filler
  (only ok/so/and).

## What it means / does not mean

It means sentence-initial "Say (that) X" and hearsay-led turns never
write and always say their exact sealed replies, while every other
turn is bit-identical to loop137c. It does not mean framed content is
understood (no counterfactual reasoning; the content is simply
refused), nor that mid-sentence marker words are affected (titles and
values containing them teach exactly as before).
