# 157 — Leading-filler strip for teaches and questions (Muse, 2026-09-22)

## Problem

The exp-152 red team (class N4, doc 152) found that filler-prefixed
teaches are refused and poison the next turns: "btw marta's brother is
kai", "also wren's city is miami", and "oh and june's teacher is patel"
all get "I didn't understand that", and the following asks ("Who is
Marta's brother?", "Who is Wren's city?") go honestly-but-stuck
MISSING_FACT — 3 refused teaches cause 8 stuck turns in session S2. The
same session log shows exp 150 also refuses "Oh and ..." (capitalised).

## Code responsible (read, not edited)

- `scripts/fable_agent_loop.py:96` — `_STATEMENT` is `^`-anchored, so a
  leading filler becomes part of the subject span ("btw marta").
- `scripts/fable_agent_loop.py:141` — `if " " in name` refuses the
  polluted subject as a multi-word name ("btw marta" fails one-word
  check); the turn falls through to the generic clarify at `:148`.
- `scripts/fable_agent_loop.py:94` — `_QUESTION` is `^`-anchored the
  same way, so filler+question ("so who is ...?") fails identically.
- `scripts/fable_fix150_subjectguard.py` (150 guard) strips fillers only
  from the subject span AFTER the parse, so it can never recover these
  turns: FakeEars already returned clarify before the guard runs.
- The bench73 template path (`hear_teach_template`, fullmatch on the
  whole sentence) likewise requires the sentence to begin with the
  subject, so filler-prefixed teaches miss there too.

## The one change

`scripts/fable_fix157_filler.py` (`Filler157Mixin`, stackable, loop150
imported read-only) + `scripts/fable_loop157_agent.py`
(`Loop157Ears(Filler157Mixin, Loop150Ears)`, loop class unchanged, daemon
with `idle_seconds`): at ears `hear()`, run the unchanged loop150 hear
first; if it already parses, return it. Else strip exactly ONE leading
discourse filler from the sealed closed list (btw, by the way, also, oh,
oh and, and, so, ok so, okay so, hey, anyway, fyi, well; longest-match)
and accept the remainder ONLY when the unchanged loop150 chain parses it
as a complete teach/correct or question (ask). Otherwise the original
result is returned byte-identical. No `_act` change: actions carry no raw
text, and both hear calls run the full loop150 chain (129 strip, 139b
value screen, 150 subject screen).

## Title rule (in PASSMARKS)

Strip only when the filler as typed is all-lowercase ("btw marta..."
strips) or is followed by a comma ("Hey, Marta..." strips). A
capitalised filler without a comma is never stripped, so "Hey Jude's
writer is Paul McCartney", "Also Sprach Zarathustra's composer is
Richard Strauss", and "So Far Away's singer is Carole King" keep their
first word (their remainders would parse as multi-word-subject teaches
on the bench73 path, so the re-parse gate alone would not protect them).
Correction markers (actually, no, wait, sorry, I meant) are not fillers
and are never stripped.

## Why this shape

Phone users type fillers before the real sentence; the bare remainder is
exactly what the loop already handles. Gating on a full re-parse (rather
than blind stripping) means filler+garbage ("btw xyzzy") and bare
corrections fall back to the identical loop150 reply, and the one-strip
limit means stacked fillers ("hey so ...") change at most one layer per
turn. Conservative by construction: the only new accepts are turns whose
remainder the old loop already parses.

## Marks

B1: new sealed probe `cases157.json` (60: 32 filler+teach/question vs
bare twins across 12 fillers; 12 filler-initial titles, 0 wrong writes;
16 filler+garbage/correction-marker, identical to loop150). B2: on the
152 sessions the 3 N4 teaches + 5 stuck asks become OK, all else
identical. G1: bench121 new/old + Fable-Edit per-item identical to
loop150 rows except predicted. G2: marks123 suites per-case identical
except predicted. G3: 152 phone sessions every reply identical to the
T-T run except predicted, 0 new WRONG, 0 new writes except predicted.
G4: every run < 25 min Mac CPU; daemon takes `idle_seconds`.

## Risks

A capitalised filler without comma that a user MEANT as a filler ("Oh
and June's teacher is Patel") stays refused — accepted cost of title
safety, stated openly. A filler word that is genuinely part of a
one-word name would strip, but no person name in the closed list exists
in our single-token-name world.
