# Exp 230c RESULTS — the name check fails closed

**Verdict: FAIL (registered).** Two sealed sub-marks missed. The fail-closed change itself did its job:
0 false "Yes" and 0 false "No" on the panel.
- **M1c 11/12.** c230-007 "Is my name Zephtarin Olquaz?" (stored: Zephtarin) gets the generic
  "I do not know that …" decline on 230b and on 230c. It never reaches the user-name route, so
  230c has nothing to act on. Diagnosis: a routing miss before the name path (the added surname
  sends the turn elsewhere). Fixing it would mean widening routing, which this experiment was
  told not to do. It is not a false yes; it is a missing "No".
- **M1f counted 2 by the sealed scorer.** The sealed scorer counts writes on each item's final
  turn, whatever it is. The two writes are controls c230-052 "My name is Kestrevin." and c230-053
  "My dog is Brakkoni.", which are teach STATEMENTS, not questions. Each writes 1 fact exactly as
  230b does, and both replies are byte-identical to base230b. Writes on turns ending in "?" = 0.
  The sealed number is still 2, so M1f is reported as missed, not re-scored by hand.

Panel: schema check passed on load (no SCHEMA-MISMATCH). Panel seal checked from the repo root
(2/2 OK; hashes equal the director's). Run once. Code seal re-checked after all runs: 6/6 OK. No
edits after the seal. 228 guard installed.

One change (scripts/claude_loop230c_agent.py, wraps 230b read-only): on a "Yes. Your name is …"
line, Yes/No is only given when the asked name was extracted and compared (230b's comparison is
unchanged). If the turn holds a word outside a closed list of common question words and no name
was extracted, the reply is the plain "Your name is <stored>.". The pattern list and routing are
unchanged. Reply-only.

## Marks table

| mark | bar | result |
|---|---|---|
| M1a "Yes" on NO / NOT_YES / NOT_TOLD (30 items) | 0 | 0 — pass |
| M1b "No" on YES / NOT_NO (16 items) | 0 | 0 — pass |
| M1c NO items exactly "No. Your name is <stored>." | 12/12 | **11/12 — FAIL** (c230-007, routing miss, same on 230b) |
| M1d YES items with base_yes true still start "Yes" | 6/6 | 6/6 — pass (c230-018 and c230-020 have base_yes false; both are the unchanged decline; reported) |
| M1e UNCHANGED byte-identical to base230b | 8/8 | 8/8 — pass |
| M1f writes on the final turn (sealed scorer) | 0 | **2 — missed as sealed** (052, 053 are teach statements; 0 on "?" turns; same as 230b) |
| M1 extra: every turn follows expected() and notebooks identical to 230b; base230b = live 230b | — | 54/54; 0 mismatches |
| M2 dev (22 cases, exact wanted replies) | 22/22 | 22/22; moves exactly e01, e04, e10, e22 as predicted; relation e20/e21 unchanged; 0 writes — pass |
| M3 sessions152 / bench / marks123 vs 230b rows; rt136 / rt143 vs 138i and vs 230b rows | 0 moves | 0 on all five, 0 vs 230b rt rows, GATE clean — pass |
| M4 sleep smoke vs smoke230b | identical | identical (1 sleep, installed, 20 ep, 5/5, wrong 0, Q99 abstain, 50/50, ow 0) — pass |
| M5 median added time (dev questions) | ≤ +5 ms | −0.037 ms — pass |

## Every move (panel: 3, all of the predicted kind "Yes. Your name is …" -> "Your name is …")
- c230-021 odd_mismatch "Is it Pravolenk, my name?": false yes removed.
- c230-027 odd_mismatch "Is Gavrinth what I'm called?": false yes removed.
- c230-033 odd_match "Is it Veskarion, my name?": a true "Yes" becomes a plain "Your name is
  Veskarion." This costs one correct "Yes"; it is allowed by NOT_NO.
Dev moves: e01, e04, e10, e22 (predicted). Frozen suites: none.

## Every miss
- c230-007 (NO): decline instead of "No. Your name is Zephtarin." (M1c).
- M1f sealed count 2 (c230-052, c230-053: statement turns; see above).
- Reported, not scored: YES c230-018 "is my name Jostravin Peldoque?" and c230-020 "Is my name
  Tessivar?" still get the decline, as on 230b. Most odd_mismatch/odd_match shapes ("I'm X, aren't
  I?", "Am I X?", "So my name is X?", "Was it X?") get a decline or "can't do 'not'". They are not
  wrong, but they are not answers either.
- c230-029 "Did I say my name was Ybrenthol?" (NOT_YES) correctly gets "No. Your name is Ybrenthal.".

## Deviations
- The panel directory existed before my seal (the writer finished early). I did not open it until
  after the seal. The first access was the scorer's schema check inside the registered run.
- rt136/rt143 go through suitediff against 138i and are also compared directly with 230b's saved
  rt rows, as in 230b.
- The M1f definition in my scorer ("final turn") was stricter than the brief's "question writes".
  I leave it as sealed and report it; no hand re-scoring.

## What it means
The assistant no longer says "Yes" to a name check it could not actually check. "Is it Pravolenk,
my name?" (real name Pravolent) now gets "Your name is Pravolent." instead of a false "Yes". On
this panel it never said "Yes" to a wrong name and never said "No" to a right one. Normal
questions and every other test suite are unchanged.

## What it doesn't mean
It does not answer every name check. A wrong full name such as "Is my name Zephtarin Olquaz?" still
gets "I do not know that", because that question never reaches the name answer. Many other
phrasings also just get a refusal. Getting a real "No" for those needs a routing change, which
this experiment was not allowed to make.
