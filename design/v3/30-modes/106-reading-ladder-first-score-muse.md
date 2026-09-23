# 106 — Reading-ladder first score: the ears we have on real text (Muse)

Inference-only measurement on the sealed exp-94 panel (400 Simple English
Wikipedia sentences, 312 gold triples, 245 NO_FACT). No training, no notebook
writes, Mac CPU. Rung 2 stays a registered FAIL; nothing here re-tests it.

## 1. Why this step exists

Synthetic panels measure obedience to a grammar the ears were raised on. The
reading ladder asks the harder question: what happens on sentences nobody
wrote for the model? Exp 106 is rung 0 of that ladder — run every existing ear
exactly as sealed (same checkpoints, same decoders, same certified/sealed
thresholds) and count what comes out.

## 2. Design: gates, normaliser, verdict mapping

- Rung-1 (tape/bigru × 4301–4303) runs behind the exp-76 certified tau-hat
  (0.088756 / 0.30286). Rung-2 (4701–4703) runs behind each seed's own sealed
  tau_exec_single (0.9484 / 0.8766 / 0.9548). Reusing sealed thresholds is the
  point: the ladder measures the deployed configuration, not a retuned one.
- Write = EXECUTE verdict with a write act. Correctness = normalised
  (relation, subject, object) ∈ the sentence's gold set. Normaliser:
  casefold + strip + collapse whitespace; direction ignored; missing object →
  "". One strict rule for both rungs, because the two decoders use different
  span systems (toy token spans vs WordPiece spans) and the comparison must
  not favour either.
- Neither decoder emits CLARIFY, so that row is 0 by construction; REPHRASE is
  the shared abstention verdict; NO_FACT is reported from rung-2's raw frame
  acts. Rung-1 sentences past 8 distinct opaque toy-vocab words cannot encode
  and count as REPHRASE (unencodable) — 87/400 for every rung-1 seed.

## 3. What the numbers say (see RESULTS for integers)

Three findings. First, silence dominates: 5 of 9 configs never wrote, and
rung-2's ~70% STATE proposals all died at the 0.88–0.95 gate — the WebRED
choke from exp 47 reproduces on real text. Second, rung-1's rare writes are
all wrong (5/5), and they passed the gate at confidence, not at the margin —
the certified gate bounds the synthetic distribution, not real English.
Third, the failures split into two kinds: two degenerate empty-relation
writes (`('', 'typewriter', '')`, `('', 'germany', '')`, both on NO_FACT
sentences) and one relation-namespace near-miss (`city` vs gold `located in
the administrative territorial entity`, subject+object exact).

## 4. Limits and next step (unclaimed)

The strict string normaliser punishes the near-miss in finding 3: a
relation-map-aware comparison (toy `city` ≡ WebRED located-in via the sealed
closed_map) would score it correct, but that rule was not sealed here and is
not applied. A follow-up exp could seal a mapped comparison up front; this
one reports the unmapped truth. Vacuous R1 passes (0/0) are absence of
writing, not evidence of restraint. One labeller's gold (exp 94, D2) bounds
everything above.

## 5. Reproduce

One command (39 s on Mac CPU, OMP=1): see RESULTS §5. Seal:
`shasum -a 256 artifacts/fable-read106-20260921/PASSMARKS.md` must equal
`SEAL.sha256.txt` (`fa162b…c21e4d`).
