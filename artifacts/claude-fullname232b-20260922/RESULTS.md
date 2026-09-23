# 232b RESULTS — same 232 code, corrected wrong-write rule, fresh blind panel

## Result
**Registered verdict: FAIL.** There are three separate reasons, listed here in order:

1. **The sealed pipeline could not read the new panel's layout (registered run).** The 232b panel pairs its items by position, using `family` = multi / one / trap. It has no `pair` or `name_words` fields. The scorer I sealed finds pairs and traps from those two fields, inherited from 232. With them missing, it saw 0 paired items, treated all 84 items as traps, and counted 83 correct saves as "trap writes". The registered numbers are therefore not a measure of the agent. They still decide the registered verdict.
2. **A real agent gap, shown by an unregistered adapter view.** The particle **"ben"** is not in 232's particle list. The list has de, da, van, von, la, bin, ibn and others, but not ben. All 3 "ben" names on the panel fail exactly as they did on 138i: the setup turn isn't understood and nothing is saved. That puts multi-word right at 33/36, below the M1c bar of ≥ 34.
3. **The sealed trap rule conflicts with two panel items (adapter view).** Two traps state a true fact and then ask about a different name or relation. 232 saved the true fact and then correctly declined to answer. Under the sealed rule ("any write on a trap item is a trap write") that counts as 2 trap writes. The panel's README says such a write is correct.

The code is byte-identical to 232. All 5 code files matched 232's seal before and after the runs. My own 232b seal also verified OK after the runs.

## Marks
| Mark | Bar | Registered (sealed pipeline) 138i / 232 | Adapter view, unregistered, 138i / 232 | Pass (registered) |
|---|---|---|---|---|
| M1a wrong writes (not in stated_facts) | 0 | 0 / 0 | 0 / 0 | yes |
| M1b trap writes | 0 | 48 / 83 (correct saves, misread as traps) | 0 / 2 (n232b-077, 084: stated facts) | **no** |
| M1c multi right ≥ one-word right − 2 | ≥ one − 2 | 0 vs 0 (no pairs found) | 33 vs 36 (bar 34) | yes on paper; adapter **no** |
| M1d multi right ≥ 138i multi + 20 | ≥ +20 | 0 vs 0 | 33 vs 0 | **no**; adapter yes |
| M1e right on 138i but not 232 | 0 | 0 | 0 | yes |
| M1f one-word replies byte-identical | 0 diffs | 0 (checked on 0 items) | 0 of 36 | yes; adapter yes |
| M2 dev / parity | ≥ 52/54; ≥ 207/210 | re-used from 232 (hash match): 54/54; 207/210 | — | yes |
| M3 suites | GATE clean, only K5 | re-used from 232: clean, 1 move (rt143 K5) | — | yes |
| M4 sleep smoke | pass | re-used from 232: pass | — | yes |
| M5 median ms delta (A+B pooled) | ≤ +5 | 5.68 / 2.05 → −3.63 | same | yes |
| Reruns identical A vs B | — | 84/84 and 84/84 | same | yes |

Adapter-view totals: right_all is 40/84 on 138i and 73/84 on 232. pass_items is 40 on 138i and 71 on 232. The 138i arm agrees with the panel writer's base138i.jsonl summary: one-word 36/36, multi-word 0/36, 0 trap facts.

## Every miss (232, adapter view)
- **n232b-006** "Sela ben Arom lives in Quellport." Not understood, nothing saved, question unanswered (same as 138i).
- **n232b-015** "Ezra ben Tamsin speaks Kessari." Same failure.
- **n232b-026** "Quenna ben Hadar lives in Vetherby." Same failure.
- Diagnosis: "ben" is missing from `PARTICLES232`, so the subject rule rejects the name and the turn falls through to 138i. Other particles and O' worked (for example n232b-005 "Kell O'Brannoch").
- Traps: 0 answers given. The 2 trap "writes" are (Tavin Morrow, city, Quellport) on n232b-077 and (Bram de la Fosse, city, Ashvale) on n232b-084. Both were stated word for word in setup. The questions (about "Tavin Marsh", and about Bram's birthplace) were correctly not answered.
- The 5 question-less NO_WRITE traps have nothing to answer, so they are "not right" by construction on both agents. They saved nothing on either.

## Every move (232 vs 138i)
- Multi-word: 33 of 36 go from wrong to right (saved and answered). 3 stay wrong (the "ben" names).
- One-word: 0 reply diffs.
- Trap question replies change on n232b-073, 077, 079 and 084, from 138i's clarify reply (or "You never told me why…" on 084) to "I don't know anyone called X." / "I don't know Bram de la Fosse's place of birth."
- Trap setup replies change on n232b-077 and 084: "Saved: …" (the stated fact is stored).
- No unpredicted flips toward an abstain or "Was that a question?" appeared, and the A/B reruns were identical. So no 5x single-item runs were needed. The 228 guard was installed on the 232 arm.

## Deviations
1. **Adapter (post-seal, input-only, unregistered).** `artifacts/claude-fullname232b-20260922/adapted/adapt_cases.py` writes a copy of the panel with `pair` = P01…P36 (by position within multi / one) and `name_words` = 2 / 1 / None. I checked that each position-pair has the same gold and verb. The sealed scorer then runs unchanged on that copy. No sealed file was changed or re-sealed. The adapter numbers are shown only as diagnosis; they do not replace the registered verdict.
2. **Missed fix before sealing.** My 232b PASSMARKS assumed the 232 panel's layout. I sealed without seeing the new layout, as the protocol requires, and I did not make the trap/pair detection robust to a different layout. That is my error.

## What it means
- On a second blind panel, the same code saved and answered 33 of 36 multi-word-name questions. Plain 138i got 0 of 36. One-word names behaved exactly as before.
- The corrected wrong-write rule works: 0 wrong writes for both agents. Every fact 232 saved was one the user actually said.
- A real, narrow gap was found: names with the particle "ben" are not understood yet.

## What it doesn't mean
- It is not a PASS: the registered run failed, and even the adapter view fails M1b and M1c.
- It does not mean 232 saves things it shouldn't. The 2 "trap writes" are true facts the user stated. The sealed trap rule just counts every save on a trap item.
- It does not show that adding "ben" would pass. That would be a code change, and it needs its own sealed run on a fresh panel.
