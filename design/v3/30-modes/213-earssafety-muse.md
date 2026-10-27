# 213 — EARS write safety map + gate rescore (Muse BUILD, scorer side only)

## Problem

Two coupled defects, one verified by director review of the scorer:

1. **Invented relations.** `pick_surface` (ears47_score:179-218) ends in "any
   content word in the sentence"; `canonical_relation` snake-cases it into a
   relation name; the validator accepts it because the word is copied from
   the utterance. "Aldric Venmore is a Norvish pianist." writes relation
   `norvish`; a birth date writes `birthplace`. Scorers judge the frame
   class, never the rendered item, so this is invisible in every report.
2. **Blind gate.** tau0 = most-confident wrong EXECUTE on cal, moved halfway
   to 1. It certifies nothing about wrong writes (it only saw frame-class
   wrongs) and executes almost nothing (~86/5,000 cal rows).

## Fix (Part A)

`fable_ears213_relmap.py`: an explicit allowlist, ears class -> notebook
relation, 12 entries (residence->city; birthplace/place of birth->birthplace;
date of birth->date_of_birth; date of death->date_of_death;
occupation->occupation; mother/father/sibling/friend/employer/age->same).
Admission rule: the frame's (subject, object) spans must directly state that
relation; doubt means ECHO-only. Deliberately excluded: country of
citizenship, spouse, child (no notebook relation); creator (direction
convention unclear); capital/origin shapes (not residence). `render` maps
class->relation and class->fixed-surface with no access to content words
(the fallback is deleted by construction, not patched). Verdict/decode code
is reused verbatim, so existing verdicts cannot shift (mark A2 checks it).
`judge` scores the rendered (relation, subject, value) triple against gold.

## Gate (Part B)

Per seed, on cal only: eligible rows (EXECUTE verdict at tau 0, write act,
mapped class — all label-free) get a fixed-sequence LTT over a G=15
count grid starting at the zero-error certifiable mass
M_MIN(alpha)=299/149/59, testing the exact binomial tail at delta=0.05 with
the CP-bound duality assert, both reused from abstain64/76. tau_hat = last
accepted tau, sealed to file before any test panel opens (in-process flag).
Then t_seen/t_new/reading94/reading94b at sealed taus plus the old tau,
executed/correct/wrong per seed per alpha. Reading panels: counts only.

## Evidence

A1: 48-case fictional probe (both review examples; demonym/date/capital/
citizenship traps; pronoun/RETRACT/ASK edges) — new path 48/48, 0 invented;
old fallback wrong on 30/48 descriptively. A2: exact tau + count equality vs
sealed 119g/119h reports. Smoke: random-init RelCondEars, 20 self-built
rows, ABSTAIN-ALL (legal) + synthetic LTT certifying 0.5175/0.5/0.5.

## Limits

Reading-gold vocabularies differ from notebook relations, so test-panel
wrong counts are conservative (over-count, never hide). The table covers 12
classes; everything else stays ECHO-only by design — coverage loss there is
intended. Production wiring (validator + notebook declare of the three new
relations) is future work; this exp is scorer-side measurement.

What it means: writes can no longer invent relation names, and the gate now
certifies a wrong-write rate instead of a frame-class accident.
What it does not mean: certified-safe exercised writes — the GPU numbers are
still pending; test-panel rates are measurements, not guarantees.
