# 232 RESULTS — multi-word names in verb sentences

## Result
**Registered verdict: FAIL (on M1a only).** The sealed scorer counted 10 "wrong writes" for 232. It counted the same 10 for plain 138i. Every one of them is a fact the user stated word for word in a second setup sentence, for example "Faddon Pike's dog is Biscuit." → (Faddon Pike, dog, Biscuit). The panel's `expect_writes` lists only the verb fact. My sealed scorer counts every other stored fact as wrong, so those correct extra facts were flagged. This is a scorer-definition mismatch, but the scorer was sealed, so the verdict stands as FAIL. I did not change or re-seal anything.

Every other mark passed:
- On the panel, 232 answers **36/36** multi-word items right (138i: **0/36**).
- The one-word twins are 36/36 on both agents, with byte-identical replies.
- There are 0 trap writes and 0 lost items.
- Dev is 54/54 and parity is 207/210 (exactly the predicted misses).
- The suite GATE is clean (1 predicted move), the sleep smoke passes, and latency is −3.6 ms.

## Marks (registered runs; seal verified OK after all runs)
| Mark | Bar | 138i | 232 | Pass |
|---|---|---|---|---|
| M1a wrong writes (panel A) | 0 | 10 | 10 | **FAIL** (see note) |
| M1b trap writes | 0 | 0 | 0 | yes |
| M1c multi right ≥ one-word right − 2 | ≥ 34 | — | 36 vs 36 | yes |
| M1d multi right ≥ 138i multi + 20 | ≥ 20 | 0 | 36 | yes |
| M1e right on 138i but not 232 | 0 | — | 0 | yes |
| M1f one-word replies byte-identical | 0 diffs of 36 | — | 0 | yes |
| M2 dev pass | ≥ 52/54 | 37/54 | 54/54 | yes |
| M2p parity | ≥ 207/210, predicted misses only | — | 207/210 | yes |
| M3 suites: new WRONG / WRONG-WRITE / junk | 0/0/0, only K5 move | — | 0/0/0, 1 move (rt143 K5 reply-only) | yes |
| M4 sleep smoke | pass | — | sleeps 1, installed 1, probes 5/5, wrong 0, taught 50/50, ow 0 | yes |
| M5 median ms delta (panel A+B pooled) | ≤ +5 | 5.68 | 2.06 | yes (−3.62) |
| Reruns identical (A vs B) | — | 84/84 | 84/84 | yes |

Panel totals (A runs): right_all is 43/84 on 138i and 79/84 on 232. pass_items is 37 on 138i and 69 on 232. The 69 is lowered by the same 10 flagged items plus the 5 question-less traps. Missing expected writes: 45 on 138i, 0 on 232.

### M1a note (diagnosis)
The 10 flagged items are n232-007, 013, 014, 025, 035, 036, 043, 044, 053 and 054. Each has a second setup sentence of the form "X's <sister/dog/boss/brother/teacher/friend> is Y." Both agents stored exactly that triple, which is correct. The panel lists only the verb fact under `expect_writes`. My scorer's rule ("active taught triples that match no expect_writes entry") therefore counts them.

No other written triple on 232 differs from something the user stated. There are no 232 writes on the 12 traps, and no multi-word write that the one-word twin didn't also make.

This is a mistake in my scorer's definition, made before the seal. It is not an agent write error. It still fails the registered mark.

## Every panel miss
- **232, answer items: none.** All 36 multi-word and 36 one-word items are right.
- The 5 question-less traps (n232-074, 077, 079, 082, 084) have no question turn, so "right" is False by construction on both agents. They are write checks only: 0 writes on both.
- 138i misses all 36 multi-word items. Its multi-word setup turns get "I didn't understand…" and the verb fact is never written.

## Every move
- One-word items: 0 reply diffs on any turn.
- Multi-word items: 36 go from wrong (138i) to right (232), and the verb facts are now written.
- Trap question replies (6 items: n232-073, 075, 076, 078, 080, 081) change from 138i's clarify reply to "I don't know anyone called <Name>." This matches the one-word reply shape and was predicted in PASSMARKS. On n232-080, 138i replied "You never told me why…". Trap setup replies: 0 diffs. Trap writes: 0.
- n232-083 ("the old baker") is unchanged: the lower-case subject is not claimed.
- Suites: rt143 K5 changes, reply-only: the clarify reply becomes "I don't know Bram Kite's place of birth." (verdict OK→OK, store identical). rt136, sessions152 and bench (800 items): 0 moves.
- Dev: 17 items go from wrong to right (all the multi-word verb items), 0 lost.
- Parity misses (predicted): t27 with "van der" and "da" (a typed particle possessive teach, out of scope); t31 with "Vask-Ley" (base 138i "I cannot predict." on a declined ";" turn).

## Deviations
1. **228 guard.** The rules changed mid-task. 232 installs the guard: `install_srcguard228()` runs at import and in the builder, and `SrcGuardMixin228` is first in the daemon bases. The base 138i runs without it, as the brief asks. There were no unpredicted flips toward an abstain or "Was that a question?" and the A/B reruns were identical, so no 5x single-item re-runs were needed.
2. **Launch mistake.** The first panel launch command failed before running anything: zsh did not split the argument variable, and the driver exited with "arguments are required". No rows were produced. The same sealed commands were then run under bash. There were no code changes and no re-runs of a completed run.
3. **Pilots.** The pilots used an earlier scorer. The final scorer changes, both made before the seal, were: a tighter "other value" rule, and a list of rerun-diff ids. The scorer that ran is the sealed one.

## What it means
- People with two-, three- or four-word names now work in plain verb sentences: "Juno de Carvel speaks Veltish." then "What language does Juno de Carvel speak?" The assistant saves and answers them the same way it already did for one-word names.
- This held on a blind panel it had never seen: 36 of 36 multi-word items, up from 0 of 36.
- Nothing changed for one-word names; the replies were byte-identical.
- Hedged, hearsay, negated and question-shaped sentences with long names still save nothing.

## What it doesn't mean
- It is not a registered PASS. The scorer I sealed counts correct extra facts as "wrong writes", so M1a fails on paper, for 138i as much as for 232.
- It doesn't fix multi-word names in other sentence types. Those gaps come from the older possessive path and still exist:
  - yes/no possessive questions ("Is Orrin Vask's city X?")
  - "the city of X's boss" chains
  - typed possessive teaches with lower-case particles ("Juno de Carvel's city is X.")
- It only covers the five verb forms: lives in, works at, works for, was born in, speaks.
- The panel is small (84 items) and uses fictional names. Real names with unusual shapes (particles not on the list, five or more words, all-caps) are not tested.
