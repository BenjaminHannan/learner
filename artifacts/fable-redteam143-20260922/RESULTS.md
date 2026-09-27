# Exp 143 RESULTS — question-side red team vs loop132 (1.8 s, Mac CPU)

Registered run: 124 cases (122 fresh + A1/B1 confirms), one fresh Loop132Daemon
dir per case, teaches then question through the mailbox. Sealed expectations;
every case reported. Mechanical: OK 92, WRONG-ANSWER 22, MISSED 10,
HARNESS-ERROR 0. After hand re-read of all 32 non-OK expectations (doc-124
discipline): 1 expectation error (H5, below), leaving 21 genuine WRONG-ANSWER
(19 fresh + 2 confirms) and 10 genuine MISSED.

## Marks

| mark | bar | result |
|---|---|---|
| M1 harness errors == 0 | 0 | PASS (all teaches `Saved:`, every case judged) |
| M2 WRONG-ANSWER, grouped + fixed below | report | 21 genuine (19 fresh in 5 classes + A1/B1 confirms) |
| M3 MISSED (coverage) | report | 10 genuine in 2 classes |
| M4 A1/B1 reproduce doc-124 findings 1/2 | reproduce | PASS (both WRONG-ANSWER as in 124) |

P143.1 (ledger): predicted 4 WRONG-ANSWER classes; found 5 fresh classes.
FALSE. Brier 0.36.

## M2 — WRONG-ANSWER classes (ranked by normal-user likelihood)

1. **Negation blindness** (5: N1–N5). "not/never" ignored; full chain
   answered. Cause: `compose_n_hop` coverage gate,
   `scripts/fable_bench92_english_arm.py:237-239`, never inspects negation.
   Fix: clarify when a negation token (`not`, `never`, `n't`, `no`)
   appears in a "?" turn (one screen in `fable_loop113b_agent.py:68-103`).
2. **Qualifier blindness** (2 fresh T1/T5 + B1 confirm). Years / "as of ..."
   ignored. Same gate; date residues are not relations. Fix: clarify when a
   year/date/"as of" residue is present (same router).
3. **Short-chain prefix answers** (9 fresh U1–U5/K8/S4/T4/L4 + A1 confirm).
   Taught chain shorter than asked (or extra relation mentioned, e.g.
   "employs" never taught in T4/L4); walked prefix answered confidently.
   Same gate: it checks walked ⊆ mentioned only. Fix: bidirectional gate —
   require mentioned-relations == walked-relations, else None
   (`fable_bench92_english_arm.py:237-239`).
4. **Answer-type mismatch via shared cue stems** (2: K6/K10). "Who
   developed HarborOS?" answered "Veldoria" ("developed" cues origin);
   "What country was Sunmosaic created in?" answered a person ("created"
   cues creator). Fix: clarify when the wh-word's answer class
   (who→person, what-country/where→place) mismatches the terminal hop.
5. **Substring entity mention** (1: O3). "capital of Norlandia" matched
   taught "Norland" and answered Aldport. Fix: word-boundary entity
   matching in `_entity_mentions92`
   (`fable_bench92_english_arm.py:145-173`).

One rule change fixes classes 3 + 4 + half of M3 below: stop the walk at
the first hop whose relation is unmentioned, and ask only if every
mentioned relation was walked (mention↔walk alignment).

## M3 — MISSED classes

- **Sub-walk suffix blindness** (5: P1/P2/Q1/Q2/D2). 1-hop question fails
  whenever the taught chain continues past the asked hop (walk runs to the
  sink, full-coverage demand fails). E.g. "Who is Joren Hale married to?"
  clarifies although Petra Voss is taught — because Petra's chain
  continues. Fixed by the same alignment rule above. Correction machinery
  itself verified working (Joren→Petra supersede present in triples).
- **Cue/format gaps** (5: H3 "lives" not a citizenship cue; J5/J10 no
  question mark; J8/J9 one-letter typos). Each needs its table/route
  widening; no wrong answers involved.

## Held (sampling of the 92 OK)

1–4-hop canonical/possessive/of-chains/relative/passive all answer
(C/D/E/F/G/H/I); polite/what's/lowercase/space/case variants answer (J);
never-taught/unknown-relation/unknown-entity abstain (K/L/O); yes-no
fact-statements and 2-mention abstains as sealed (M); look-alike 2-hops
exact (P3/P4); all three correction prefixes install (Q5/Q6/Q1-world);
branch/loop/two-mention abstain (S1/S2/S3/S5/T2/T3); rewriter F5/H4 fire
correctly on islands (`loop132-rewrite` stage).

## Expectation error (1)

H5 (mechanical WRONG-ANSWER): the rewriter resolved the 2-mention relative
clause via the Bram seed and returned Meridian — the human-correct value.
My sealed "abstain" was wrong. Reclassified OK; the rewrite path's seed
choice on multi-mention questions is flagged as fragile in the design doc.

## Deviations / limits

None from plan. Single deterministic run per case; in-process
`process_file` mailbox (same code as subprocess daemon); English only;
no sleep involved (≤7 turns < threshold). Reproduce:
`export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1; uv run --offline --no-project --python 3.12 --with torch --with numpy python -B scripts/fable_redteam143_run.py`
(after seal; results in `artifacts/fable-redteam143-20260922/`).

## What it means

Loop132 answers every intact-chain phrasing tried and cleanly abstains on
untaught relations/entities — but any asked-but-untaught hop, qualifier,
or "not" is silently dropped while it confidently answers the rest.

## What it does not mean

It does not mean teaching or the loop132 rewriter is broken (rewriter
wins on F5/H4; corrections install) — all 21 wrong answers come from the
unchanged base composer gate, and no fix was applied here.
