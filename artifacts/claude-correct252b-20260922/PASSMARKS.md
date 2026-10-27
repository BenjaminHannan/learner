# Exp 252b — value-screen fix on 252 — PASSMARKS (sealed before any registered run)

**Base:** 252 (`scripts/claude_loop252_agent.py` + `artifacts/claude-correct252-20260922/loop252-config.json`, sealed in exp 252).

**Mine:** `scripts/claude_loop252b_agent.py` + `artifacts/claude-correct252b-20260922/loop252b-config.json`. The stack is the same as 252: SrcGuardMixin228 first, then Correct252DaemonMixin, RestartIndex220Mixin and Loop138jDaemon.

## The one change (coordinator ruling: option B, value screen only)

The change is in `scripts/claude_fix252b_screen.py`. It rebinds `claude_fix252_correct.value_ok252` in the loaded module; no file is edited. `value_ok252` is the only screen in 252 that checks words against the stopword list, and every 252 write path calls it: `_fix252`, the bare-value path, the explicit named path and `_two252`. The new screen does two things:
1. It runs 252's screen unchanged.
2. It also splits the value on non-letter characters and rejects it if any piece is a 252 stopword ("that's" → "that"). It likewise rejects any piece that is one of the apostrophe-less spellings below.

**Words added** (apostrophe-less spellings of the contractions the screen covers; `dont` was already a 252 stopword):
`thats hes shes theres heres whats whos wheres whens isnt wasnt arent werent doesnt didnt dont theyre youre theyll youll itll thatll therell wholl hed theyd youd itd thatd whod theyve youve weve whove`

**Words excluded** (they are ordinary English words or plausible names or places, so they are never added):
`its hell shell well ill wed id shed were lets whys hows ive im cant wont`

A pilot unit check found these values still pass: Aldgate, Crane Hollow, O'Brien, Jean-Luc, Well, Shell, Ive, Wendish.

## Marks (each registered run is done once; outputs go to `artifacts/claude-correct252b-20260922/run/`)

| Mark | What | Bar |
|---|---|---|
| M1 | 252 panel re-run once on 252b; `claude_corr252b_score.py m1` against `artifacts/claude-correct252-20260922/run/panel-252.jsonl` | Every row identical except `ms_per_turn` (wall time, which can never match). The exception is c252-022: its store after the turn and after the followup must equal the store after setup, and the followup must not say "that's outdated". Any other difference is a FAIL. |
| M2 | Held-out safety dev `dev252b.jsonl`, 56 items, my own wordings (38 denials and corrections ending in a trailing clause, 6 questions with a trailing clause, 12 controls); `claude_corr252b_score.py dev` against the 252 rows made in the same registered session | 0 junk writes, 0 wrong removals, 0 question writes, controls identical to 252's (all fields except `ms_per_turn`) |
| M3 | `fable_suitediff218.py --only rt136,rt143,sessions152,bench --base-dir artifacts/claude-correct252-20260922/run/base138k-rows` (the sealed 138k rows) | Move lists equal to 252's `run/sd-252` (rt136 C071/C072/C073/C075, sessions152 S3-teachers-correction#6, all reply-only); 0 new WRONG, WRONG-WRITE, junk or lost OK |
| M4 | `fable_sleepsmoke206.py --idle-seconds 5.0` | Every field equal to 252's `run/smoke-252.json` except agent, config, label and seconds |
| M6 | `claude_merge138k_probe.py` on 138k `v-dialogs.json` + `v-supp.json`; `claude_corr252_m6check.py m6` against 252's `run/m6-252-*.json` | 0 ghost answers, 0 failed duplicate checks, 0 reply or store moves |

## Predictions

- **M1:** c252-022 is the only difference, and it now writes nothing. In the pilot the reply was "I don't have Tobin anymore, that's outdated as Quenby's manager, so I didn't change anything." and the followup was "Quenby's manager is Tobin." PASS.
- **M2:** all of 252's junk writes are gone except b252-035 ("That's wrong, that's old news." after "Where does Kasia work?" stores employer = "old news"). That write comes from the "that's Z" correction pattern, not the screen. So M2 FAILS on that one item. There are 0 wrong removals, 0 question writes, and the controls are identical.
- **M3, M4 and M6:** identical to 252 (all PASS).
- **Registered verdict:** FAIL, on M2 because of b252-035. That fix is exp 258's job.

## Reference column (no mark): 138k on dev252b, run once before the seal

The 138k rows are in `run/dev252b-138k-ref.jsonl` (sealed).
- 138k has 1 junk write: b252-051 "Correction: Amos's teacher is Calloway." stores the subject "Correction: Amos", which 252 already fixes. It has 0 wrong removals and 0 question writes.
- In the pilot, 252 had 6 junk writes on dev252b (b252-001, 006, 008, 013, 018 and 035). **All 6 were introduced by 252**; 138k writes none of them. The 252b pilot removes 5 and leaves b252-035.
