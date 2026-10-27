# 159 — Hop through known names (Muse)

## Step 1 — the code responsible (written before sealing; no behaviour changed yet)

The exp-152 red team (class N9, its only WRONG) found: after "Biscuit's
color is brown." and "Ana's pet is Biscuit.", "Who is Ana's pet's color?"
replies "Ana's pet is Biscuit, which is not someone I can look up." Three
code sites combine to produce this:

1. `scripts/fable_agent_loop.py:91` (`PERSON_RELATIONS`): "pet" and "owner"
   are not person relations, so the ears file them with `=` (literal), not
   `->` (entity). "Biscuit" is therefore stored as the literal text
   "Biscuit", not as a pointer to the Biscuit entity (confirmed in
   `scripts/fable_listening_m1.py:119-120`: `=` stores
   `{"literal": value_text}`).
2. `scripts/fable_notebook_contract.py:404-407` (`Notebook.ask` hop loop):
   when the walk stands on a non-entity mid-value it returns BROKEN_CHAIN
   immediately, without checking whether that text names a known subject.
3. `scripts/fable_fix77_core.py:275-277` (the loop150 reasoner
   `QualifierAwareReasoner77.answer`, same check repeated at :282-283):
   `if kind != "entity": return BROKEN_CHAIN` — a mid-chain literal
   ("L" view tag, :300-301) always breaks, even when the literal is the
   display name of an entity heading live taught facts.

152's turn 26 ("Who is Biscuit's owner's pet?" → "Biscuit's owner is Ana,
which is not someone I can look up.", judged OK by mistake) is the same
shape one hop later: the mid-value "Ana" heads the live taught fact
"Ana's pet is Biscuit." yet the walk stops.

## Step 2 — the one change

`scripts/fable_fix159_hop.py`: `Hop159Reasoner77` subclasses
`QualifierAwareReasoner77`; `answer()` is the parent's hop loop verbatim
except the two `kind != "entity"` branches, which first try
`bridge159(nb, lit_text)`: continue from the matching entity iff the
literal exactly equals — after the loop's own name normalisation
(`C._norm`, lowercase + collapse whitespace) — the display name of
exactly one entity heading at least one live taught fact
(`source == "taught"` and `nb.active`). Zero matches, alias-only matches,
and ambiguous (two entities, one name) matches keep the old BROKEN_CHAIN
reply byte-identical. `scripts/fable_loop159_agent.py` builds loop150 and
swaps in this reasoner (ears, mouth, sleeper, thinker, notebook, mailbox
untouched); config `artifacts/fable-hop159-20260922/loop159-config.json`.

Why this cannot invent a wrong answer: a continued walk only follows live
taught rows, so every reachable answer is a taught value; anything
uncertain (no/ambiguous match, missing next fact, unknown relation) keeps
an abstain status (BROKEN_CHAIN / MISSING_FACT). Case-only differences
("Rope" vs subject "rope") DO continue — the loop itself normalises case
away at lookup, so they are exact matches, not loose ones; the trap group
tests strictly-loose pairs (sub/super-strings, plurals, extra words).

## Step 3 — marks (all sealed in PASSMARKS.md + SEAL.sha256.txt before any run)

- H1: new 48-dialogue probe (`cases159.json`, `scripts/fable_fix159_probe.py`):
  26 two/three-hop chains through non-person relations (pets C01-C06,
  objects C07-C11, places C12-C16, organisations C17-C21, works C22-C26)
  → correct answer; 11 mid-value-nobody dialogues (N01-N11) → old reply
  unchanged; 11 loose-match traps (T01-T11) → old reply, 0 wrong answers.
- G1: bench121 new + old-fresh + Fable-Edit per-item identical to the
  sealed loop150 rows except predicted items; 0 new wrong.
- G2: `scripts/fable_marks123_all.py` suites per-case identical to the
  sealed loop150 run (`marks150`) except predicted cases.
- G3: exp-152 phone sessions re-run with the loop159 target (imports
  `scripts/fable_session152_run.py` shapes, reads sealed
  `sessions152.json`): every reply byte-identical to the T-T run except
  predicted turns; 0 new WRONG; 0 new writes except predicted.
- G4: every registered run < 25 min Mac CPU; daemon takes idle_seconds.

## Step 4 — predictions (ledger P159.x, appended before any registered run)

P159.1 (H1): 48/48 pass — 26/26 chains correct, 11/11 nobody old-reply,
11/11 traps old-reply, 0 wrong answers, 0 question-turn writes.
P159.2 (G1): 0 per-item moves on all 600 bench rows (item-by-item scan of
the sealed loop150 rows finds 0 BROKEN_CHAIN replies; only that branch
changed), 0 new wrong. P159.3 (G2): every marks123 suite per-case
identical to marks150 (scan finds 0 BROKEN_CHAIN replies in marks150).
P159.4 (G3): exactly 4 reply moves, all in S4-pets-identity — turns 7+27
→ "Ana's pet's color is brown.", turn 20 → "Ana's pet's owner is Ana.",
turn 26 → "Biscuit's owner's pet is Biscuit." (WRONG 2→OK 2, OK→OK text
change ×2); all other 176 replies byte-identical; 0 new WRONG; 0 new
writes. P159.5 (G4): each registered run < 1500 s.

Pre-seal evidence (dev only; the new loop never runs before the seal):
base calibration of all 48 dialogues through loop150 (all teaches Saved,
all questions BROKEN_CHAIN — proves every dialogue is well-formed and the
base is blind to all of them); scan counts above; unit check of
`bridge159` matching semantics against a hand-built notebook is NOT run
pre-seal (it would execute new-loop code paths — instead the rule is
verified by the registered H1 itself; a FAIL is recorded as FAIL).
