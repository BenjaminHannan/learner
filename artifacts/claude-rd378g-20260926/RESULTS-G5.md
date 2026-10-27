# rd-378g G5 results (written 2026-09-27 22:39:44 UTC): G5 PASS, so rd-378g is a PASS (G1-G5)

G5 asks whether the new writer's notes (G, trained only on ungraded GLM and Luna notes) are no less true than the
rd-378 writer's (R, Claude-trained). A PASS means "no less true than the rd-378 writer". It does NOT mean trustworthy:
the blind judges called about half of R's notes unsupported, here and before, so matching R is a low bar.
RESULTS.md (G1-G4) is unchanged. This file adds G5 and the overall verdict.

## The mark (shown; sealed rule, ADDENDUM-K)
Key = both judges say ok, or both say unsupported; everything else is excluded. Share = key unsupported / (key ok + key
unsupported), per writer. Source: g5/score.json from `scripts/claude_rd378g_g5.py score`.

| Writer | Notes judged | Key ok | Key unsupported | Excluded | Unsupported share |
|---|---|---|---|---|---|
| G (new, no Claude, no grader) | 368 | 158 | 153 | 57 | **49.2%** |
| R (rd-378 writer, Claude-trained) | 467 | 196 | 203 | 68 | **50.9%** |

| Line | Rule | Result | |
|---|---|---|---|
| G5 bar | G's share <= R's share + 5 points (<= 55.9%) | G 49.2% vs R 50.9%, G - R = -1.7 points | **PASS** |
| Proved wrong | G's share >= R's share + 15 points (>= 65.9%) | -1.7 points | not fired |

The 57% fallback was not needed: R's weights reached the rental and R wrote its own G5 notes (RESULTS.md).
Prediction written before any G note existed (ADDENDUM-K): R about 50%, G about 50%, G5 PASS. It came true.

## Overall rd-378g verdict (shown): PASS
| Mark | Result | Source |
|---|---|---|
| G1 notes still help | +11.40 points over A (bar +5) | RESULTS.md |
| G2 as good a search aid as R | -1.04 points against R (bar -2) | RESULTS.md |
| G3 no category left behind | every category above A | RESULTS.md |
| G4 notes parse | 5 of 3,122 turns unparsed (0.16%, bar 2%) | RESULTS.md |
| G5 no less true than the rd-378 writer | G 49.2% vs R 50.9% unsupported (bar R + 5) | this file |

PASS = G1-G5. G is a Claude-free note writer that helps search about as much as R, and whose notes are no less true
than the rd-378 writer's. The blind judges found about half of each writer's notes unsupported, so this PASS does not
show that either writer's notes are trustworthy.

## What happens next (fixed in advance by ADDENDUM-K and rd-378k PASSMARKS-B)
- G is offered to Month-end for 0.2d's notes slot only as a search aid, disclosed as "trained on ungraded GLM and Luna
  notes; G's unsupported share 49.2% vs R's 50.9% on fresh dialogs". No G note goes to Month-end as trustworthy. Notes
  stay search pointers to the raw lines (store v4 answers from raw lines only).
- rd-378k may now use A = G (PASSMARKS-B), but it still waits for a grader that passes (ADDENDUM-K).

## Report-only rows ADDENDUM-K lists (shown; g5/report_only.json from scripts/claude_rd378g_g5_report.py)
| Row | G | R |
|---|---|---|
| Excluded notes | 57 of 368 | 68 of 467 |
| - judges gave different verdicts | 27 | 26 |
| - judges agreed on bad_cite, bad_when or bad_form | 30 | 42 |
| Unsupported share, chat dialogs (14) | 45.9% (45 of 98) | 42.6% (52 of 122) |
| Unsupported share, overheard dialogs (29) | 50.7% (108 of 213) | 54.5% (151 of 277) |
| Notes per turn | 0.730 (368 on 504 turns) | 0.927 (467 on 504 turns) |
| Turns with at least one note | 304 of 504 | 356 of 504 |
| Unparsed turns | 0 of 504 | 0 of 504 |

## Extra report-only rows (not in ADDENDUM-K's list; they change nothing)
| Row | G | R |
|---|---|---|
| Judge A: ok / unsupported / bad_cite / bad_when / bad_form | 173 / 156 / 15 / 11 / 13 | 212 / 205 / 15 / 20 / 15 |
| Judge B: ok / unsupported / bad_cite / bad_when / bad_form | 167 / 161 / 20 / 12 / 8 | 201 / 208 / 25 / 20 / 13 |
| Same verdict from both judges | 341 of 368 (92.7%) | 441 of 467 (94.4%) |
| Turns where judge A / judge B found something memorable with no note ("missed" > 0) | 89 / 67 | 60 / 46 |

- Suggested: the result does not hang on one judge. Each judge alone called a smaller share of G's notes unsupported
  than of R's (judge A 42.4% vs 43.9%, judge B 43.8% vs 44.5%, of all notes).
- Suggested: the pass is not luck of the dialog draw. Resampling the 43 dialogs 10,000 times (both writers' notes on a
  dialog kept together, seed 37805) puts G - R between -7.6 and +4.0 points (95% range), all under the +5 bar; G - R
  was above +5 in 1.1% of draws and never reached +15 (g5/bootstrap_report_only.txt). Not a registered test.
- Suggested: G writes fewer notes than R (0.73 vs 0.93 per turn) and leaves more memorable things without a note, by
  both judges. G5 measures truth per note written, not coverage. G2 already showed G's notes help search about as much
  as R's.
- Untested: why G's notes are no worse despite no grader. One guess is that Luna, a strong writer, wrote most of G's
  training notes (ADDENDUM-K's prediction). Nothing here tests it.

## How it ran (shown)
1. `python -B scripts/claude_rd378g_g5.py selftest`: "rd378g g5 selftest 1/1 ok". The script, ADDENDUM-K and the judge
   brief match SEAL-ADD-K.sha256.txt. Both notes files match the run's SEAL-run.sha256.txt (W/g5_G.jsonl, W/g5_R.jsonl).
2. `make --dialogs artifacts/claude-rd378g-20260926/g5/dialogs.jsonl --rem 2 --g vast/g5/notes_G.jsonl
   --r vast/g5/notes_R.jsonl --seed 37805 --out <scratch folder outside the repo>` at 22:15:29 UTC: 43 dialogs
   (14 chat, 29 overheard), 86 items, G 368 notes and R 467 notes on 504 turns each, none unparsed or missing
   (g5/make.json).
3. Two fresh blind judges (new Claude subagents that had seen none of this work), started 22:15:46 UTC. Each had its own
   empty folder holding only items.jsonl and an unchanged copy of the rd-378 judge brief (JUDGE_NOTES.md, sha256
   c56a78e5...). They were told to open nothing outside that folder, never saw map.json or which writer wrote which note,
   and were told that code may print and check but never decide a verdict. Judge A (judge_A.jsonl) finished after about
   15 minutes and judge B (judge_B.jsonl) after about 23. Both files have 1,008 lines, one per non-assistant turn, with
   no duplicates, no missing turns and every verdict count matching its note count (checked in code). Judge A's two helper
   scripts only printed a dialog and appended the verdicts it typed. Judge B used none, and changed one of its own
   verdicts by hand after settling how to label a joke taken as fact.
4. `score --map g5/map.json --a g5/judge_A.jsonl --b g5/judge_B.jsonl` at 22:38:55 UTC: g5/score.json.
5. map.json and items.jsonl entered the repo only after both judges had finished.
6. Blind recount (g5/recount.txt): a separate new subagent, given only map.json and the two judge files and not told the
   score, wrote its own count from scratch. It got G 158 ok, 153 unsupported, 57 excluded (49.2%) and R 196 ok, 203
   unsupported, 68 excluded (50.9%): the same as score.json. Its integrity checks were all clean (1,008 pairs, 0 broken).

## Disclosed
- The judges used the brief's five verdict words (ok, unsupported, bad_cite, bad_when, bad_form), as rd-371b's judges
  did. The key counts only notes both judges called ok or both called unsupported; the rest are excluded and reported
  above. This is the sealed rule, not a change.
- The judges are Claude agents. That is allowed for a test (they measure, never train). Their verdicts train, tune and
  filter nothing.
- Untested: whether the judges kept to their folders. They were told to, and nothing they reported suggests otherwise.
  Their default working directory was the repo, and the tool may have shown them the repo's CLAUDE.md, which names no
  writer and nothing about G5. map.json sat in a separate scratch folder, outside the repo, while they judged.
- G5 compares the same pair as G2: two things differ (the writers and the grade filter), so it is not a one-change test.

## Files (all new; g5/ held only dialogs.jsonl before)
g5/items.jsonl (the 86 judge items), g5/map.json (opaque id to writer), g5/judge_A.jsonl, g5/judge_B.jsonl,
g5/make.json, g5/score.json, g5/report_only.json, g5/bootstrap_report_only.txt, g5/recount.txt, g5/SHA256.txt.
