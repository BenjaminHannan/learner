# Exp 224c PASSMARKS (sealed before registered runs)

The change (agent `scripts/claude_loop224c_agent.py`, built on `scripts/fable_loop224_agent.py`, which is not edited):

- Whenever loop224 would serve Q1 ("I don't know that yet — you haven't told me."), a read-only notebook check runs first.
- The check gets snapshot views only (MappingProxyType / frozenset). It gets no notebook object and calls no notebook method.
- Q1 is kept only if the check confirms nothing is stored for what was asked. Otherwise the reply becomes Q2 ("I didn't understand that question — could you say it another way?").
- Check rules and guards: see the agent docstring and `design/v3/30-modes/224c-q1honest-opus.md`.
- Required by the 2026-09-22 rules: the exp-228 `_src_of` guard is installed, the same way as in `scripts/claude_loop228_agent.py`.
- Config: `artifacts/fable-agent138i-20260922/loop138i-config.json`, unchanged.

Why a forcing harness is needed: on 138i an ask always produces an answer record, so the Q1 branch is only reached by the flake.

- The 228 forced harness (`scripts/claude_determinism228_forced.py`) makes flakes happen, but in the pilot those turns carried no ask. loop224 served them Q2, not Q1 (pilot: 58 Q2, 0 Q1).
- With the 228 guard installed, the planted stale entry does nothing at all.
- So the Q1 branch is exercised by the case driver's `forced` mode (`scripts/claude_224c_cases.py`). On the probe turn only, it makes an ears "ask" come back as a "didn't understand" clarify. That is the shape of the 224b flake: an ask was captured, the notebook path reported a miss, and the glue was reached.
- This forcing is driver-only.

## Marks (all must hold for PASS)

**M1: 224's B1 cases** (`artifacts/fable-decline224-20260922/224b/cases224b.json`, natural mode).
- Bar: every probe reply is byte-identical to 224's registered `b1-224.json` (Q2 30/30, S1 30/30, Q1 controls 20/20), with 0 writes.
- Pilot: 80/80 identical, 0 writes.

**M2: taught-fact traps** (`cases224c.json`, set M2). 40 dialogs, fictional names; the asked fact is stored, and `stored_check` must be True for every one. Sub-groups:
- A: correct parse, 1–3 hops (11)
- B: misparsed subject such as "the job of X's mother" (6)
- C: partial names such as "Mira" for "Mira Vell" (5)
- D: synonym relation words new to the notebook (7)
- E: inverse relations (3)
- F: odd wordings the ears cannot parse (8)

Each dialog is run in natural and in forced mode on loop224c. Bars:
- Q1 appears 0 times (natural + forced).
- 0 wrong values: the reply states no stored value other than the gold (values that appear in the question are excluded).
- The 228 forced harness on loop224c (202 bench items) shows 0 Q1 replies.

For contrast (not a bar), loop224 in forced mode served Q1 on 32/40 in the pilot. Pilot for loop224c: 0 Q1, 0 wrong values; harness 0 Q1.

**M3: truly untaught** (set M3, 24 dialogs):
- 12 with a known subject whose asked relation was never taught for it, but is used for another person in the same notebook;
- 12 with an unknown subject.

Bars:
- loop224 (forced) must reach Q1 on at least 20 of them.
- Of those, loop224c (forced) keeps Q1 on at least 90%.
- 0 wrong values, natural + forced.

Pilot: 24/24 reached, 24/24 kept, 0 wrong.

**M4: frozen suites.** `scripts/fable_suitediff218.py --only rt136,rt143,sessions152,bench,marks123 --base-dir artifacts/claude-decline224c-20260922/base224-rows`.
- That folder holds byte copies of 224's registered rows (`224b/suitediff`). The rt136/rt143 files are renamed so 218's file finder sees them. Source and copy sha256 files are in this folder and match (0/15 mismatches).
- Bar: 0 new WRONG, 0 new WRONG-WRITE, 0 new junk write, GATE clean, and no unpredicted move.
- Predicted moves:
  - bench132-4hop-031 abstain → correct (224's registered row was the flake, and the 228 guard is now installed);
  - any row whose 224 reply was exactly Q1 and whose new reply is exactly Q2.
- Pilot: exactly one move, 031 abstain → correct. GATE clean.

**M5: sleep smoke.** `scripts/fable_sleepsmoke206.py` on loop224c, checked by `scripts/fable_decline224_b3.py` against the sealed 138i smoke.
- Bar: B3 PASS (installed, 1 sleep, 20 episodes, probes 5/5, 0 wrong, broken = abstain, taught 50/50, 0 overwrites).
- Pilot: PASS.

**Hygiene.** Every run is under 25 minutes, the seal verifies after the runs, and no sealed file is edited after the seal.

## Informational sets (reported, not in the verdict)

- **M2x (3): a known limit, disclosed before the seal.** A synonym where both words are in use in the notebook: "manager" is used for another person while "boss" is stored for the subject. A word-level check cannot tell these apart, so Q1 is expected to be served, falsely. Pilot: 3/3 Q1.
- **M3x (6): the cost of the new-relation guard.** Known subject, relation word never used anywhere in the notebook. By design these get Q2, not Q1. Pilot: 0/6 Q1.

## Predictions (also in the ledger)

- P224c.1 M1: 80/80 byte-identical to 224, 0 writes.
- P224c.2 M2: 0 Q1 over 40 dialogs x 2 modes, 0 wrong values, harness 0 Q1.
- P224c.3 M3: at least 20 reached, kept at least 90% (expected 24/24), 0 wrong values.
- P224c.4 M4: only bench132-4hop-031 abstain → correct, GATE clean.
- P224c.5 M5: B3 PASS.
- P224c.6 M2x: 3/3 Q1 (known limit); M3x: 0/6 Q1.
