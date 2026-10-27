# 115 — Sleep scale ladder: 104's live sleep until it breaks (Muse, 2026-09-22)

## Problem

Exp 104 fired a real install inside the running loop96 daemon, end to end:
one relation (`maternal_grandmother` = mother+mother), one sleep, 20
episodes, all marks PASS. Nothing is known about scaling: several relations
at once, installs across sleeps (forgetting?), longer chains, long sessions,
or a crash mid-ladder. Exp 115 climbs a 5-rung ladder and stops at the
first rung that fails, reporting it as the breaking point with a reproducer.

## Design (additive only; no existing file touched)

`scripts/fable_sleep115_agent.py` generalises the three exp-104 pieces from
one word to the three word slots the sealed R44 architecture provides
(`maternal_grandmother` mother+mother, `boss_of_spouse` spouse+boss,
`doctor_of_mothers_friend` mother+best_friend+doctor):

- **Sleep115Ears** wraps the loop's ears chain. FakeEars leaves spouse /
  best_friend / doctor teaches as literals (absent from PERSON_RELATIONS),
  which would starve the episode feed of entity-valued hops; the wrapper
  forces `is_person=True` for the five chain hops and passes everything
  else through (attribute delegation keeps daemon logging intact).
- **Sleep115Reasoner** wraps QualifierAwareReasoner77 with a three-word
  episode feed (the wire57 queue rule per word: walk the chain, queue
  `(start, word idx, answer)`), plus per-word sleep-derived marks: the
  record source flips to `sleep-derived` and that word's report row heads
  the trail. Pre-install answers stay MISSING_FACT (words are never
  declared relations, so `known()` is false until bridged).
- **Sleep115Sleeper** subclasses wire57's `SparseVillageSleeper` (exp-46
  recipe, unchanged gate — it already loops over words). After an install
  it audits each word's hardened `[3][9]` logits against that word's true
  chain (non-keep argmaxes in row order: [1,1], [3,4], [1,5,7]), bridges
  each into the live `words` table (additive — earlier installs untouched),
  appends one `sleep_report` row per word, and merges all words into one
  atomic JSON file (`sleep115-words.json`, tmp + fsync + os.replace).
  Boot restores every valid word; a `sleep115-SLEEPING` marker brackets the
  recipe for the kill arm. The latency mark covers recipe + bridge.
- **Sleep115Daemon** = `Loop96Daemon` + retrofit + one log row per SLEEP
  tick (multi-sleep sessions fully recorded).

`scripts/fable_sleep115_drive.py` is the mailbox-only ladder driver: L1
(150 teaches + 60 asks + 5 fillers, threshold 215, one 3-word sleep);
L2 (phase 1 threshold 75 installs A, same-dir restart, phase 2 threshold
145 installs B+C, then retention probes); L3 (3-hop word alone, threshold
100); L4 (400 turns, threshold 75: w0/w1/w2 in sleeps 1-3, then
`boss_of_father` and `teacher_of_spouse` — chains with NO word slot — in
sleeps 4-5, then 25 probes); L5 (L4 + kill-9 in the 3rd sleep, dormant).

## Evidence (sealed wave; breaking point L4)

L1 PASS 3/3: one sleep installed all three words (20 episodes each, OOF
1.00, agreement 1.00, routings exact), 15/15 NEW-people probes per seed
(all sleep-derived), taught 150/150, sleeps 29-31 s. L2 PASS 3/3: A in
sleep 1, B+C in sleep 2, A still 5/5 after sleep 2 (no forgetting), taught
150/150. L3 PASS 3/3: the 3-hop install took 4-6 s, 5/5 probes, taught
75/75. L4 FAIL (seeds 1-2; seed 3 incomplete at 141/400 turns when the wave
clock ran out): sleeps 1-3 installed w0/w1/w2 (5/5 each, taught 225/225),
sleeps 4-5 queued zero episodes and installed nothing, and all 10 extra
probes honestly abstained with 0 wrong. Zero wrong installs and zero taught
overwrites everywhere, all seeds. Wave report: wave-report.json.

## Limits

Only three compositions are installable (R44 `N_WORDS=3` is architecture,
not a setting); the brief's uncle/cousin examples need brother/child
skills that do not exist, so L1 uses the sealed slots. Single-word sleep
latency varied 5-415 s for identical fits — the other agents share this
Mac, so wall-clock is contention-dominated; the 120 s mark is meaningful
only for the instant no-op sleeps. Sleep still fires on a turn counter,
never need; ears/mouth remain template stand-ins. L5 never ran (stop rule);
the L4 reproducer (`--only l4 --seed 1`) replays the structural break.

## What it means / does not mean

Means: installs compose (three at once, across sleeps, no forgetting, no
damage) right up to the architecture's edge, where the system abstains
instead of inventing a fourth slot. Does not mean sleep is scheduled by
need, latency-bounded under load, or extensible to new compositions
without retraining the base: the ceiling is three words by construction.
