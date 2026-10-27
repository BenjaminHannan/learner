# 138c — self serves only when grounded, else the base reply (Muse, 2026-09-22)

## Problem

After the seal, loop138's decline text was rewritten (deviation D2) to
contain every checker's phrase, so "hi", "who are you?", "What is the
capital of Chile?" and "Do you know Tom?" all get the same mashed decline:
"HONEST_DECLINE + I didn't understand that, I don't know — could you say
it another way?" And bench121-4hop-165 shows the router hijacking a content
question after a notebook miss: the notebook clarified, route127 fired D7,
and the D7 canonical answer ("I have no opinions…") was served as if it
were content -- scored wrong while the base loop abstained.

## The one change

In `scripts/fable_loop138c_agent.py`, `Loop138cAgentLoop.turn` keeps
loop138's notebook-first path, logging, sleep retrofit and daemon exactly,
but changes only the notebook-missed branch: the self answer is served
ONLY on (router non-DECLINE AND grounded answer). Grounded means: not the
Self99 FALLBACK text and carrying none of the Self99 DECLINE_MARKERS. A
decline-marker sentence claims no fact, so it is not content -- this is
what catches 165, whose hijack text is a decline body rather than
FALLBACK (the brief's parenthetical names only FALLBACK; the marker clause
is stated openly in PASSMARKS as the operative part). Everything else --
router DECLINE, FALLBACK answers, decline-marker answers -- serves the
base loop's own reply verbatim (`L134.Loop134AgentLoop.turn` on the same
state, i.e. exactly what loop138 computed as `said` and discarded).

## What moves, and what cannot

- 165 (D7 hijack): ungrounded, so the base clarify returns -- abstain again.
- Director's probe: all four router-DECLINE, so base clarifies return
  verbatim; the mashed decline is never served anywhere anymore.
- Panel declines: base clarifies return; they need the sealed accept rule
  to count as correct declines (a judge change, stated in PASSMARKS).
- Cannot move: 174 (the frozen 113c gate's partial-frame misjudgement is in
  the notebook path, which wins before the self rule is consulted) and
  rt110 S1 (a redteam-shaped count probe the router answers C1 with
  genuinely grounded state content -- the rule serves grounded content by
  design, so S1 stays served). Both are predicted FAILs with diagnoses.

## Judges

B1 bench121 per-item identity vs loop134 (165 back, 0 new wrong); B2
marks123 suite equality vs loop134 (S1 back); B3 blind panel through the
turn path (<= 6 wrong, with the decline accept rule); B4 director's probe
(4/4 base-verbatim, zero mashed markers); B5 every run < 25 min Mac CPU.
New files only: `scripts/fable_loop138c_*.py`,
`artifacts/fable-self138c-20260922/`, this doc.
