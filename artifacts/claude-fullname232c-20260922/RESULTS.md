# Exp 232c — 232 plus complete name particles: RESULTS

**Verdict: PASS.** The one registered run passed every mark (M1a–M1g and M2–M5), and the reruns were identical.

**Blind panel** (`artifacts/claude-namepanel232c-20260922/`, 84 items):
- 232c answered **36/36** multi-word-name questions correctly; 138i answered 0/36.
- 0 wrong writes and 0 trap writes.
- 0 lost items, and one-word replies were byte-identical to 138i.

**Setup:**
- The code, scorer, dev cases and PASSMARKS were sealed before I opened the panel. The panel seal was checked before the run: 0 non-OK lines.
- Both seals were re-checked after all runs: 0 non-OK lines each.
- The schema check passed: scorer exit 0, no SCHEMA-MISMATCH.

## Marks

| Mark | Required | Result | Pass |
|---|---|---|---|
| Schema | no SCHEMA-MISMATCH; counts multi 36 / one 36 / trap 8 / stated_extra 4 | rc 0, counts match; base138i.jsonl fields and ids match | yes |
| M1a wrong writes (not in stated_facts) | 0 | 0 | yes |
| M1b trap-family writes | 0 | 0 (138i also 0) | yes |
| M1c multi right ≥ one right − 2 | ≥ 34 | 36 vs one 36 | yes |
| M1d multi right ≥ 138i multi + 20 | ≥ 20 | 36 vs 138i 0 | yes |
| M1e right on 138i, wrong on 232c | 0 | 0 | yes |
| M1f one-word replies byte-identical | 0 diffs | 0 diffs (36 items) | yes |
| M1g stated_extra value answers | 0 | 0/4 (stated fact saved 4/4, reported only) | yes |
| Panel pass items | — | 232c 84/84; 138i 48/84 | — |
| Reruns identical (A vs B, both arms) | yes | 0 diff ids on 138i, 0 on 232c | yes |
| M2 dev (103 items) | ≥ 98, 0 wrong/trap writes, misses exactly 007 + 085 | 101/103, 0 wrong, 0 trap, misses d232c-007 + d232c-085 | yes |
| M2p particle parity | 238/280 with the sealed miss list | 238/280, the exact sealed miss list | yes |
| M3a suites vs 138i | GATE clean, moves = 232's (rt143 K5 reply-only) | rt136 0, rt143 1 (K5 reply-only), sessions152 0, bench 0; GATE clean | yes |
| M3b sessions152 + bench vs 232's rows | 0 moves | 0 and 0; GATE clean | yes |
| M4 sleep smoke | sleeps ≥ 1, installed ≥ 1, wrong 0, 50/50, ow 0 | sleeps 1, installed 1, probes 5/5, wrong 0, taught 50/50, ow 0 | yes |
| M5 latency (232c − 138i median) | ≤ +5 ms | −3.5 ms (1.94 vs 5.48 ms) | yes |

The sealed predictions were met: P232c.1 through P232c.5 all came true.

## Every move

**Panel, 36 multi items.** The answer is now right on all 36 (138i declined all of them). The names used these particles:
- de, da, di, dos, del, della, den, der, ter, le, la, du, van, von;
- ben, bin, ibn, bat, abu, al, el, ap, mac;
- and 3 apostrophe/hyphen names.

They were 31 three-token, 3 two-token and 2 four-token names.

**Panel, 8 non-pair reply moves.** All are declines; none gives a value.

| Item | Family | Question | 138i reply (start) | 232c reply |
|---|---|---|---|---|
| 073 | trap | untaught person with "van" | "I do not know that from what you taught me…" | "I don't know anyone called Marcel van Oosterhuis." |
| 074 | trap | untaught person with "bint" | same | "I don't know anyone called Rania bint Sulaiman." |
| 075 | trap | untaught person with "mac" | same | "I don't know anyone called Ciaran mac Diarmada." |
| 080 | trap | small talk, then untaught person with "dos" | same | "I don't know anyone called Beatriz dos Arvelos." |
| 081 | stated_extra | untaught relation | same | "I don't know Oskar van Heerlen's employer." (the stated city was saved) |
| 082 | stated_extra | untaught relation | same | "I don't know Matteo di Salvione's place of birth." (the stated language was saved) |
| 083 | stated_extra | near-miss surname (Marwani / Marwasi) | same | "I don't know anyone called Rashid ibn Marwasi." (Marwani's fact was saved) |
| 084 | stated_extra | different first name (Clara / Paula) | same | "I don't know anyone called Paula de la Monteira." (Clara's fact was saved) |

- Traps 076–079 have no question. They were scored on writes only, and both arms wrote 0.
- In the one-word family, 0 replies changed.
- **Cross-check (reported only):** the panel writer's base138i.jsonl base_reply values matched my own 138i A run on all 84 items (0 differences). Note that base138i was produced without the 228 guard.

**Dev** (my own set: 44 pairs covering all 34 particles, de la / van der / von der / van den, O', D', hyphen and initials; 12 traps, 7 of them conjunction traps; 3 stated_extra):
- Result: 101/103. Multi 42/44, one 44/44, 0 wrong writes, 0 trap writes.
- All 7 conjunction traps: 0 writes. This includes "Ana and Bo live in Quellport." and "Orrin and Tessaly Vask live in Dunmere."
- Misses (both predicted):
  - d232c-007 "Tobin do …": not claimed, gets 138i's reply;
  - d232c-085 "Tomas de la Vega Ruiz": 5 tokens.
- Reply-only moves on declines: 096 (hedge + ben), 097 (negation + ben), 100 (never taught). The reply changes from 138i's long decline to "I don't know anyone called Sela ben Arom." / "…Juan de la Cruz.", with 0 writes.
- Stated_extra items 101–103: the fact was saved, and the other question was declined. Example: "I don't know anyone called Sela ben Tamsin."

**Parity: 238/280.** One-word "Orrin" was compared against each particle name over 35 dialogs. The misses are exactly the sealed list:
- "Orrin do Vask": 35/35 (not claimed);
- t27, typed particle possessive (out of scope, as in 232): ben, y, mac, de la, bint, zu;
- t31, 138i's reply to a declined ";" turn: ben.

**Suites:**
- vs 138i: the only move is rt143 K5, reply-only. This is the same move 232 has.
- vs 232's sealed rows: sessions152 0 moves, bench 0 moves.

**Flake rule:** it did not trigger. There were no rerun diffs and no unpredicted flip to an abstain or "Was that a question?".

## Deviations and limits (all declared in PASSMARKS before the seal)

1. **"do" names are not handled.** The director's list includes "do", but the stack's 150b clause-in-subject guard reads "do" as a verb. That guard would turn such a teach into a split request. 232c therefore requires 150b to say "store" and does not claim "X do Y" names; they get 138i's decline. The guard was not changed. The blind panel contained no "do" names, so this limit was tested only on dev and parity.
2. **4-token cap.** The 137 possessive parser refuses subjects over 4 tokens, so 232c claims 2–4 tokens in all. The panel's longest names were 4 tokens. 5-token names (dev 085) are a known miss.
3. **M3 route.** `--base-dir` 232 skips rt136 and rt143 because of the tool's filename search. Those suites were covered by `--base 138i` with 232's move set (M3a).
4. **The 150b pre-check** inside the subject rule is part of the one change (subject acceptance), not a separate fix. An ineffective fallback mixin was removed before the seal.
5. The panel's base138i.jsonl was produced without the 228 guard. It still matched my guarded 138i run on every reply.
6. **Process:** the registered dev/parity/suite/sleep batch exited with shell code 1. That code came only from the final `grep -vc` returning a count of 0 (every seal line OK). All steps completed.
7. **Coverage gap:** the blind panel contained no conjunction traps. Conjunction handling was checked only on my own dev set.

## What it means
- Taught with a verb sentence, the assistant now learns and recalls facts about people whose names contain particles such as "van", "bint", "ibn", "de la" or "ap". Examples: "Oskar van Heerlen lives in Delft." or "Rania bint Sulaiman works for …".
- On a fresh set of questions written by someone else, it got all 36 multi-word names right. The old version got none.
- It saved nothing wrong, invented no answers, and answered one-word names exactly as before.
- When asked about a similar-looking but different person (Marwani vs Marwasi, Clara vs Paula), it said it didn't know them instead of borrowing the other person's fact.

## What it doesn't mean
- **Names with "do"** (for example "João do Rio") still don't work.
- **Names longer than 4 words** still don't work.
- **Typed possessives** ("Orrin ben Vask's city is …") with particle names still don't work.
- This is **plain-software parsing.** It is not learned understanding of names, and it only covers five verb patterns (lives in, works at/for, was born in, speaks).
- **Conjunction safety** ("Ana and Bo live in …") was shown only on my own dev cases, not on the blind panel.
- It says nothing about conversation quality in general.
