# Exp 226: "Who told you that?" (source questions about the last reply)

**Verdict: registered FAIL (P3).** Every other mark passed. The only failure is one reply-only move in rt143 case H5, and it did not come back in any rerun (details below).

## What was built
`scripts/fable_loop226_agent.py` is loop138i plus one outer layer, `Source226Mixin`. After each normal turn it records which notebook facts the reply used, taken from what the pipeline did:
- for a teach: the write record plus the new taught facts;
- for an answer: the reasoner's own `trail`, checked against the record;
- for a reverse question or a yes/no question: that stage's own function, re-run and checked against the reply.

A question from a closed list of 19 templates ("Who told you that?", "How do you know?", "Says who?" …) is caught before the ears run, so it can never write. It is answered from the recorded facts' stored source. Design: `design/v3/30-modes/226-source-opus.md`.

## Marks (sealed: SEAL.sha256.txt, all 6 files verified OK after the runs)
| mark | result |
|---|---|
| P1 source turns exact | 72/72 (saved 18, one-fact 11, 2-hop 8, 3-hop 3, backwards 5, multi 2, yes/no 3, me-name 4 incl. saved, no-fact 12, restart-after-answer 4, twice 2) |
| P2 non-source turns identical to 138i | 133/133 |
| P3 suitediff vs 138i | rt136 0, sessions152 0, bench 0, **rt143 1 move** (H5, reply-only, WRONG-ANSWER→OK, 0 new wrong / junk) → FAIL |
| P4 sleepsmoke206 | same as 138i: installed, 5/5 right, 0 wrong, broken probe abstains, 50/50 taught, 0 overwrites |
| P5 writes | 72/72 source turns added 0 notebook events; 205/205 turns stored triples equal 138i |

## The P3 move (read in full)
H5 ("What is the official language of the country that Cora Lind, who is married to Bram Kite, is a citizen of?"): the sealed 138i reply is the wrong confident chain answer (stage loop138b-rewrite). The registered 226 run replied "Was that a question?" (stage bench73). H5 is not a source template. H5 alone gave the base reply on both agents under 6 hash seeds each. The rt143 suite gave 0 moves in 1 pilot and 8 open reruns of 226, and in 8 open reruns of 138i. So it is intermittent and its cause is not established. It is recorded as FAIL, not re-run into a pass.

## Deviations
- Web-sourced and sleep-derived answers cannot be produced through dialogue on the base here. That provenance wording is written but untested.
- Self-router replies get the honest "I can't say where that came from" reply. They are not traced.

## Reproduce
`scripts/fable_source226_run.py` (run base, run new, then `--judge`); the suitediff and sleepsmoke206 commands are in PASSMARKS.md. Outputs are in `runs/`.

**What it means:** on these 72 fresh source questions the assistant now answers truthfully where its last reply came from, and nothing else in the sessions changed.
**What it does not mean:** it can trace every kind of reply (self-router, web and sleep answers are not traced), or that the one rt143 flake is understood.
