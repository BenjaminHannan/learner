# 102 — Integrated-agent patches for redteam98 (Muse, 2026-09-22)

Exp 98 showed the joined-up loop breaks at its ears seam: template ears
believe hearsay-shaped sentences, forget is unreachable, "Actually, "+template
is dropped, year junk is stored verbatim, and one bad byte kills the daemon.
Exp 96 had closed two earlier gaps with `GuardedEars`. This experiment adds
exactly five pre-filter fixes in one new file,
`scripts/fable_loop102_agent.py`; no existing file is touched.

## Design: one wrapper, one subclass, one daemon override

`Loop102Ears` wraps `Loop96Ears(chain)` and inspects the raw turn before
delegating, in fixed order. F1 scans for attribution markers (", X said",
"according to", "read online"/"I read that", "I heard", "apparently",
"reportedly", leading "quote", "the web says") and answers the plain clarify
"Do you know that yourself, or did you hear it somewhere? ...". A
bench-template match whose subject starts lowercase *and* carries attribution
vocabulary is refused the same way, so junk entities are never minted. Both
narrowings are evidence-driven: a pre-build scan of 1,148 sealed turns showed
bare "online" would hit people called Online, and 22 legitimate Fable-Edit
subjects ("baseball ...", "jazz ...") start lowercase. F3 strips "Actually, /
No, / Correction: / Sorry, I meant ..." then bench-matches with a capitalised
first letter, emitting a `correct` action through the same structured path as
B1-B4; non-template remainders fall through untouched (FakeEars keeps its
possessive correction, bare yes/no still answer pending confirms). F2 parses
"forget N R", "Forget X's R.", "Forget that X's R is V.", "Please forget ..."
into a `forget2` action; `Loop102AgentLoop._act` serves it with the M1
doorway's existing `Listening._forget` (same store, multi-word names work,
ambiguity/unknown stay the doorway's job). Exact resolve misses fall back to
unique whole-word-prefix match ("Roberto" -> "Roberto Merhi"); a name that is
the verb ("forget Forget city", sealed G1) clarifies instead of guessing.
F4 strips trailing "in/since/until <yyyy>", "from <yyyy> to <yyyy>", "as of
<yyyy>" and delegates the bare sentence; questions are never stripped (D8).
The stripped bare value is taught *without* qualifier metadata: attaching it
would make the sealed unqualified D2/D7 asks abstain under the doc-56 gate,
so the phrase is dropped (documented deviation). `Loop102Daemon` rebuilds the
agent with this ears chain and overrides `process_file` only to catch
`(OSError, ValueError)` on the UTF-8 read: the poison file gets "I couldn't
read that message -- please send it as plain text.", moves to done/, is
logged, and the daemon keeps running (F5).

## Evidence (sealed P1-P4, all PASS)

P1 replays the 16 reproducers (E7 typo-fixed copy in `repro/`) through both
daemons: Loop96 gives H5 OK + 15 BUG (as the director found), Loop102 gives
16/16 OK. P2 re-runs all 64 sealed cases through loop102 with the unchanged
judge: 0 OK->BUG, 16 BUG->OK, 0 remaining BUG; only intermediate replies
changed on A1/H3/C6/C8 (all OK->OK). P3 re-runs L1-L6 with the agent swapped
in: L1 2/2 clarify, L2 74 cases 0 wrong writes (6 listed changes, one new:
C_forget-02 now reaches the doorway, 0 writes), L3 3/3, L4 thinker rulings
hold, L5-Z1 60/60, L5-Z2 200/200 (150+50, bench73 on all 575 teaches), L6
3x200/200 0 wrong 0 dupes. P4 runs 30 pre-sealed innocents (Said/Online/Quote
names, "Tom Said" values, mid-sentence "actually", year values): 0 false
refusals (gate <= 2). D1: P4 run 1 failed on a harness checker bug (fixed,
re-ran, recorded).

## Limits

Qualifier phrases are discarded, not understood; the verb/noun "Forget" clash
is resolved by fiat (clarify) to protect sealed G1; leading-"quote" also
rewords two already-safe replies (A1/H3, OK->OK); the guard retires when real
ears lands.

## What it means / does not mean

Means: the running loop now survives every attack the red teams proved, still
with zero edits to any existing module. Does not mean the parts understand
English: this is still template parsing plus two safety wrappers, and
mouth53 plus neural ears remain the documented replacements.
