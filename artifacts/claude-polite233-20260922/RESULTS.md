# Exp 233 RESULTS — polite negative questions (Opus)

**Verdict: FAIL** (registered). M1(d) failed: polite_untaught honest abstain
was 9/12, and the bar was 12/12. All other marks and sub-marks passed.
Every one of the 8 panel misses uses a frame the brief's list does not
include ("remember", "Can you not", "be able to", "Surely you can't have
forgotten"). My agent leaves those unchanged, so they still get the
loop223 negation clarify.

The one change: `scripts/claude_loop233_agent.py` (loop223 subclass).
`Loop233AgentLoop.turn` rewrites a "?" turn that starts with can't / cannot /
couldn't / won't / wouldn't / don't you, or do you not, (+ please/just) +
tell me / know / remind me / say, into the plain question it contains
(for example "Where does Kim live?", "Who is Kim's boss?", "What is Kim's
city?"). This happens only when the rewritten question has no negation
word. The plain question then goes through the unchanged loop223 turn().
Design: design/v3/30-modes/233-polite-opus.md.

## Marks (integer counts)

| mark | bar | got | verdict |
|---|---|---|---|
| M1a wrong values (233, panel) | 0 | 0 (223 also 0) | pass |
| M1b question writes (233, panel) | 0 | 0 (223 also 0) | pass |
| M1c polite_taught right | >= 223 + 15 = 15 | 19/24 (223: 0/24) | pass |
| M1d polite_untaught honest abstain | 12/12 | **9/12** (223: 0/12) | **FAIL** |
| M1e true_negation + negated_statement identical to 223 | 24/24 | 24/24 (16 + 8), reply and stored triples | pass |
| M2 dev (63 own cases) | >= 60/63 | 62/63 | pass |
| M3 suitediff218 vs 223 rows | 0 new WRONG/WRONG-WRITE/junk, 0 moves predicted | rt136 0, rt143 0, sessions152 0, bench 0, marks123 0 moves; GATE clean on all | pass |
| M4 sleep smoke | sleeps=1 installed=1 probes=5/5 wrong=0 broken=abstain taught=50/50 ow=0 | exactly that (episodes=20, abst=0, 84.7 s) | pass |
| M5 latency, median (233 − 223) per question turn | <= +5 ms overall and on unchanged families | −0.89 ms overall; +0.09 ms on the 24 unchanged items | pass |

Panel seal checked before opening (panel.jsonl OK). My seal checked
after all runs: 8/8 OK.

## Every panel miss (8 of 60)
All 8 got the loop223 clarify ("I didn't understand that. I only know
current facts and I can't do 'not' ..."), byte-identical to 223. No
rewrite fired because the frame is not in the brief's list:
- p233-008 polite_taught "Don't you remember who Nyle's doctor is?" (remember)
- p233-013 polite_taught "Can you not tell me where Ilsa lives?" (can you not)
- p233-014 polite_taught "Do you not remember who Borro's neighbour is?" (remember)
- p233-018 polite_taught "Wouldn't you be able to tell me who Lorn's boss is?" (be able to)
- p233-023 polite_taught "Surely you can't have forgotten who Tibby's landlord is?" (surely ... forgotten)
- p233-031 polite_untaught "Don't you remember who Ambry's doctor is?" (remember)
- p233-035 polite_untaught "Can you not tell me where Ilsa lives?" (can you not)
- p233-036 polite_untaught "Do you not remember who Quill's neighbour is?" (remember; panel marks it clear=false)

The 5 taught misses did not break M1c: 19 right is still at least 15. The
3 untaught misses broke M1d. The clarify gives no value, so it is not a
wrong answer. But my sealed scorer counts only "I don't know"-style
replies as an honest abstain.

Diagnosis (one note): the frame list was sealed to the brief's list. The
blind panel's author wrote wider polite frames ("remember", "can you
not", "be able to", "surely ... forgotten"). The fix would be to widen
the frame list. That needs a new experiment, because this one is sealed.

## Panel passes (for the record)
polite_taught 19/24 right: 001–007, 009–012, 015–017, 019–022, 024.
Rewrites seen include "Where does X live?", "Who is X's R?", "What is X's
city/town/coach?". polite_untaught 9/12 honest abstain ("I don't know X's
R." or "I don't know anyone called X."). true_negation 16/16 and
negated_statement 8/8 identical to 223.

## Dev (M2)
62/63 pass: 0 wrong values, 0 question writes, and 0 differences in
setup replies. The one miss, D21 "Couldn't you say where Jessamy's boss
lives?", rewrites to "Where does Jessamy's boss live?". The base does not
read that two-hop form, so it gives its honest abstain (known before the
seal).

## Suites (M3), every move
Moves: none. rt136 0, rt143 0, sessions152 0, bench 0, marks123 0. rt136
and rt143 compare against 223's registered rows, which I copied unchanged
into base223/ because the suitediff file finder needs "redteam136/143" in
the file name. sessions152, bench and marks123 compare against
artifacts/fable-cantdo223-20260922 directly.

## Deviations
- The rule update about the 228 src-guard (SrcGuardMixin228) arrived
  after my seal. This agent does not install the guard. Per the rules,
  runs already sealed stay as they are. No unpredicted flip happened in
  any registered run, so no 5× reruns were needed.
- A registered-suite command first failed to launch (zsh did not split
  a `$R` variable, so nothing ran and nothing was written). I re-issued
  the same commands straight away. It is a driver-only shell fix, with
  no file changed.
- Pilots ran before the seal on dev, suites and smoke. Registered runs
  were done once each.

## What it means
- For the frames the brief listed, polite "Can't you tell me where X
  lives?" questions now get the stored answer (19 of 24 panel items) or
  an honest "I don't know" (9 of 12). Before, every one got the
  "can't do 'not'" clarify.
- Real negative questions and negative statements behave exactly as
  before (24/24 identical). Nothing wrong was ever said or written.
- The frozen suites and the sleep smoke did not move.

## What it doesn't mean
- It does not handle every polite form. "Don't you remember ...", "Can
  you not ...", "Wouldn't you be able to ..." and "Surely you can't have
  forgotten ..." still get the clarify. That is why this is a FAIL.
- The rewrite is a word-pattern rule, not understanding. Two-hop forms
  like "where Kim's boss lives" become questions the base still can't
  read.
- Passing the suites means nothing old broke. It does not show the new
  rule works on wordings outside these 60 + 63 items.
