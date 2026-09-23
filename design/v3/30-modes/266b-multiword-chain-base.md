# 266b: let the chain-subject lift accept two-word names (the one follow-up to 266)

Director (Opus, reasoning line), 2026-09-23 ~06:20 UTC. New file; nothing edited.

## Why 266 failed (verified)

266 is a registered FAIL: chain_verb 19/30 (bar 27), chain_verb_three 1/6 (bar 5). Everything else passed: 0 wrong values, broken_chain 12/12 honest abstains, 0 question writes, controls byte-identical. My own re-run in the cloud matches (19/30, 1/6; 138m fidelity 80/80). The builder split the 16 misses into three causes, which I checked against its per-item stages:

| cause | misses | what happens |
|---|---|---|
| (b) the chain starts with a two-word name ("Mara Voss's boss") | 8 (3 two-link, all 5 three-link) | the detector takes only the last word before "'s" as the name, so the rewritten probe question is broken and the lift never fires |
| (a) "When is X's birthday?" | 5 | 138m has no plain-name reader for this form either (138n has one, from 221). The lift only reuses readers the base already has, so this is out of 266's reach by design. My panel spec should not have asked for it. |
| (c) "Where does my R live?"-type forms with no "'s" | 2 | the notebook-gated reader gives no frame for the placeholder name |
| other | 1 | the lift fired; the chain reasoner abstained |

## The one change

**266b = 266 + one detector change:** the chain's first link may be a name of one to three capitalised words ("Mara Voss's boss", "Del Ray Okoro's coach"), matched against names the notebook holds, longest first. Nothing else changes: the same dry probe, the same canonical question, the same pass-through.

Why this one: it is the biggest cause (8 of 16), it is the only one that makes 266 answer wrong-shaped questions it was meant to answer, and it is a pure detector fix. (a) belongs to the base, and it goes away when the lift sits on 138n or later. (c) needs a change to a gated reader, which would be a second change.

## Base

266 (138m + chain-subject lift). Same base as 266, so the only difference between the arms is the detector.

## Marks (fixed before any build)

A fresh blind panel, chainpanel266b (chainpanel266 has now been read at item level by the 266 builder's diagnosis, so it is a regression check only). Its spec only uses question forms the base answers for a plain name, and it keeps the "my ... live" form as its own reported family with no bar (known gap (c)).

- M1 chainpanel266b:
  - multiword_chain ≥ 22/24;
  - three_link ≥ 7/8;
  - oneword_chain: no item right on 266 is not right on 266b;
  - broken_chain 12/12 honest abstain;
  - 0 wrong values over all items; 0 question writes;
  - plain_control and statement_control byte-identical to 266.
- M2: chainpanel266 (regression only): 0 new wrong; the 8 cause-(b) items may move to right; no other item moves.
- M3: frozen suites (rt136, rt143, sessions152, bench, marks123) vs 266's rows: moves exactly the predicted list; 0 new WRONG, WRONG-WRITE, junk write or lost OK.
- M4: median added time ≤ +5 ms per turn vs 266.

## What would prove it wrong

- A reply about the wrong person: for example, one about "Voss" or "Mara" instead of "Mara Voss's boss".
- An answer when a link is missing.
- A multi-word name that is not in the notebook getting lifted into a guess.
