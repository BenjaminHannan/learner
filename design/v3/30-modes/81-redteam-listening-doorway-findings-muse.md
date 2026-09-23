# 81 — Red-team listening-doorway findings (2026-09-22, read-only probe)

Red-team pass over the LISTENING doorway before a human talks to it. Under
test: `scripts/fable_listening_m1.py` driven through `scripts/fable_agent_loop.py`
(FakeEars template parser) over `scripts/fable_notebook_contract.py`. Method: 73
adversarial ENGLISH turns in 17 sequences, one fresh AgentLoop per sequence
(runner `scripts/fable_redteam81_probe.py`, full log
`artifacts/fable-redteam81-20260921/fable_redteam81_results.json`). Nothing was
fixed; this doc ranks what (little) needs attention.

## Integer summary

turns 73 (+1 harness setup) | OK 74 | BUG 0 (critical 0, high 0, medium 0, low 0) | UNCLEAR 0 | crashes 0

## Findings: none at doorway/contract level

Every rule under test held: a turn is written, answered, clarified, or refused
— never silently dropped (0 crashes, every turn replied), never written wrong
by the doorway (every write matched the action the parser produced);
corrections supersede incl. the confirm-yes path (B-02, B-05, L-04, P-03);
contradictions trigger CONFLICT clarify, never a silent second value (A-03,
P-02, L-03, H-03, J-02); ambiguous names ask (A-07); questions never write
(all genuine interrogatives taught_delta=0); nothing personal inferred ("my"/
"Tom" entities verified absent, O-02, O-04, Q-01); 3 hops answer, true 4-hop
refuses (M-04/M-05); self-reference terminates (L-02). So there are no BUG
reproducers to file. The two lossy parses below are FakeEars scaffolding
limits — documented for the ears agent, not doorway bugs.

## FakeEars limitation 1 (sharpest): "?" is ignored, then kept in the value

`"Mira's city is Lisbon?"` is TEACHEd, and the stored literal is `Lisbon?`
with the question mark (the `_STATEMENT` regex strips `.` but not `?`), so the
next answer echoes it back (`Mira's city is Lisbon?.`). A user asking a genuine
yes/no question gets a silent write of a corrupted value. Illustration (6
lines, repo root, read-only):

    import sys, tempfile; sys.path.insert(0, 'scripts')
    import fable_agent_loop as A
    loop = A.AgentLoop(tempfile.mkdtemp())
    print(loop.turn("Mira's city is Lisbon?"))  # ['Saved: ... Lisbon?.'] -- wrote
    print(loop.turn("Who is Mira's city?"))     # ['Mira's city is Lisbon?.']

Direction: strip trailing `?` in FakeEars, or route `X?` declaratives to
clarify ("did you mean to tell me, or are you asking?"). Real ears must
distinguish declaratives from interrogatives before the doorway acts.

## FakeEars limitation 2: conjunctions pack into one literal, fact lost

`"Mira's city is Lisbon and Mira's pet is a cat."` saves city=`"Lisbon and
Mira's pet is a cat"`; the pet fact is silently lost (later `Who is Mira's
pet?` → MISSING_FACT, E-03). The doorway wrote its action faithfully — the
splitter is ears' job. Direction: multi-clause turns should clarify or split
in the parser, never pack.

## Further FakeEars limits (all safe clarifies, 0 writes — noted only)

No pronouns (B-04, F-03), no forget verb (C-02), no imperatives (D-03), no
yes/no answering (D-04, N-02), no JSON (K-01), structured lines rejected as
non-English (K-02), uppercase-`'S` possessive unparsed (`_APOS` is lowercase-s
only, H-02), typo/accent/fullwidth names become separate people (G-02, H-05/06;
teach-creates is by design), and person/alias/forget/quote acts are unreachable
in English at all. None of these is a doorway bug; each is a missing ears
capability that currently fails safe.

## Explicit non-findings (held under attack)

CONFLICT gating, supersede chains, alias-free AMBIGUOUS-never-merge, 8-case
contradiction battery, UNKNOWN_ENTITY/MISSING_FACT/BROKEN-free refusals,
case/whitespace normalisation via `_norm`, status words as values, 6000-char
turns, empty/whitespace/name-only turns, quote/hypothetical no-writes,
no-inference-about-the-user, restart-free fresh loops, 0 crashes.

## What it means / does not mean

Means: the M1 doorway core is trustworthy as probed — fix nothing before a
human talks to it; hand limitations 1–2 to the ears agent. Does not mean the
system is safe end to end: real English ears, mouth wording, and sleep mining
were out of scope and unprobed.

Predictions: P81.1 TRUE (73 turns, 100% OK) · P81.2 FALSE (0 BUGs) ·
P81.3 FALSE on the letter (D-01 wrote 1 FACT; all genuine interrogatives 0) ·
P81.4 TRUE (0 crashes).
