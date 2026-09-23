# Exp 247 RESULTS: wider missing-apostrophe repair (cause C1 of diagnosis 243)

**Result: registered verdict FAIL, on M1b only.** Every other mark passes. The M1b failure comes from 6
wrong-value items in the `direction` family. All 6 are base228's own leaks: my agent's reply is
byte-identical to base228's reply, and base228.jsonl marks each of them base_right=false. My change touched
none of those replies. The common brief says direction leaks base228 already has are "listed, not counted"
(M1e), but M1b as registered ("wrong values on all 124 items: 0") has no such exception. My scorer
applied M1b exactly as written, so the verdict stays FAIL and I did not re-score or re-run anything. If the director
rules that base228's own direction leaks are excluded from M1b too, M1b becomes 0 new wrong-value items
and every mark passes. That ruling belongs to the director, not to me.

The family my fix targets, no_apos, went from 0/16 to 16/16 right.

## Marks (every registered run was done once; the seal was checked OK before each run: 8/8 files)
| mark | bar | result | pass |
|---|---|---|---|
| M1a no_apos right | >= 15/16 | 16/16 (base228: 0/16) | PASS |
| M1b wrong-value items, all 124 | 0 | 6 (all in direction: q243-085..090, replies byte-identical to base228, all base228 leaks) | **FAIL** |
| M1c question writes, all 124 | 0 | 0 | PASS |
| M1d control byte-identical | 12/12 | 12/12 | PASS |
| M1e other-family regressions / untaught / new direction leaks | 0 / 10/10 / 0 | 0 / 10/10 / 0 (base228 leaks listed: 085-090) | PASS |
| M1f combo (no bar) | - | 2/8 right (096, 098 new; base 0/8), 0 wrong values | reported |
| M2 dev | fix 33/33, keep 15/15, trap 10/10, outside 5/5, 0 writes | 33/33, 15/15, 10/10, 5/5, 0 writes, setup replies identical 63/63 | PASS |
| M3 suitediff vs 138i | 0 bad moves; moves = predicted (none) | GATE clean, 0 moves in rt136, rt143, sessions152 and bench | PASS |
| M4 sleep smoke | sleeps 1, installed, 5/5, wrong 0, 50/50, ow 0, < 300 s | sleeps 1, installed 1, 5/5, wrong 0, 50/50, ow 0, 84.6 s | PASS |
| M5 median added ms per panel question | <= +5 | -0.08 | PASS |

Panel family table for my arm (right/n): compose 0/16, no_apos 16/16, whats 0/12, first_person 0/12,
verb_subject 0/12, my_relation 0/16, direction 4/10, combo 2/8, control 12/12, untaught 10/10.
Across the 124 items, the fresh base228 rerun matched the base228.jsonl base_reply on 124/124, so the base is
deterministic here. Replies changed from base228 on only 18 items: 16 no_apos and 2 combo. That matches
P247.3.

## Every move
- Panel (decline -> right): q243-017 through q243-032, all 16 no_apos items. These cover one-, two- and
  three-part names, relations spouse/city/pet/employer/school/doctor/sister/boss/nationality/dentist/friend/
  "country of citizenship"/teacher, and base228 answers to those items of 15 declines plus 1 "I have no opinions." (027).
- Panel combo (decline -> right): q243-096 "whos Vrox Zizans spouse?" and q243-098 "who is garkar dombyns spouse?".
  The 6 other combo items keep base228's reply. They need the C2 ("whats") or my_relation fix.
- Dev: all 33 fix items move from decline/opinion to right. The 15 keep items are byte-identical. The 10
  traps and 5 outside items give no stored value.
- Suites: none.

## Misses (with one-line diagnosis)
- q243-085..090 (direction, counted in M1b): the verb question flips direction ("Who does Brylto employ?" ->
  "Brylto's employer is Gedund."). This is base228 behaviour (exp 251's cause) and is untouched by 247.
- Combo 095/097/099/100/101/102: another cause is still present (whats / my / married-to). This is outside C1.

## Deviations
- Agent build: build_agent138i is reused unchanged. The builder rebinds the module global
  `L138I.Loop138iEars` to Loop247Ears during the build only, then restores it in `finally`. No file was edited,
  and base228 built in the same process is unaffected (fresh base228 matched base228.jsonl 124/124).
- Before the seal I added a `main()` so the sleep smoke could spawn the daemon. Also before the seal, I added
  allowed_mentions ["Orrin"] to 3 dev items where Orrin is the asked name itself.
- Dev "outside" class (5 items): greeting/please/yes-no/verb forms. Their apostrophe twins also fail on base228,
  so they were marked "no wrong value, no write" and were not required to be right. This was declared in
  PASSMARKS before the run.
- The M1b wording conflict is described above. The verdict was left as FAIL.

## What it means
When someone types a question without the apostrophe, like "Who is Pells spouse?" or "Who is Joren Hales
boss?", Premonition now reads it the same way as "Pell's spouse" and gives the saved answer. This works for any fact it has
stored about that person, and for names of one, two or three words. The fix gave no new wrong answers,
wrote nothing during questions, and left every other kind of question byte-for-byte the same.

## What it doesn't mean
It does not fix questions that start with a greeting or "please", yes/no questions, "whats", "my sisters" or
verb questions. It does not treat synonyms as the same relation, so asking "wife" when "spouse" was stored
still gets no answer. The registered verdict is FAIL because 6 old wrong answers from the base (the "Who does X employ?"
direction bug) sit on the same panel. My change did not cause them, but the M1b bar counts them. The panel is
16 items for this family, all with made-up names. That is enough to show the pattern works, not to measure
how often real users type this.
