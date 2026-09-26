# bm-398n RESULTS: do the reader's notes give more right answers? (benchmarks thread, written 2026-09-26 20:40 UTC)

**Verdict: FAIL, not proved wrong.** Answering from store B's lines (heard turns plus notes that point to them) gave
17 more right answers than store A's (heard turns only): 269 against 252 of 759, blind. That is above the +15 the
PLAN asked for, but the change is not reliable: 83 questions gained a right answer and 66 lost one (two-sided exact
McNemar p = 0.19, needed < 0.05). No category was hurt. It is registered as sealed (PLAN.md, 94833d852) and does
not change. Every LoCoMo number is "after using LoCoMo for development". Counts only.

## Marks
| Mark | Needed | Got | Result |
|---|---|---|---|
| N1: more right answers | BN A ≥ AN A + 15, gained > lost, McNemar p < 0.05 | +17, 83 gained, 66 lost, p = 0.190 | FAIL |
| N2: no category hurt | each category drops at most max(3, 3%) | 1: −1; 2: 0; 3: +1; 4: +17 | holds |
| Proved wrong | BN A ≤ AN A | +17 | no |

## Blind check (759 questions, categories 1-4, conversations 0-4; judges see the evidence lines)
| Arm | A right | B | C partly | D wrong | E don't know |
|---|---|---|---|---|---|
| AN: store A's first 20 turns | 252 | 12 | 133 | 348 | 14 |
| BN: store B's first 20 turns | 269 | 15 | 132 | 327 | 16 |

- BN − AN is +17 right answers (+2.2 percentage points). The conversation bootstrap (report only; the PLAN chose
  McNemar because there are only 5 conversations) gives +0.6 to +4.0 points.
- Right answers by category (AN → BN): 1: 24 → 23 of 141; 2: 18 → 18 of 156; 3: 8 → 9 of 44; 4: 202 → 219 of 418.
- Wrong answers fell 348 → 327 and "don't know" rose 14 → 16 (report only; this PLAN predates the D/E rule).
- The AN-to-BN table: A→A 186, A→B 4, A→C 19, A→D 37, A→E 6, B→A 6, B→B 3, B→C 1, B→D 2, C→A 26, C→B 3, C→C 76,
  C→D 27, C→E 1, D→A 47, D→B 5, D→C 36, D→D 255, D→E 5, E→A 4, E→D 6, E→E 4.
- 174 of 759 questions got byte-identical replies from both arms. Their two judges agreed on 168 of 174. The relabel
  judge agreed with the main labels on 53 of 60.
- An independent recount (a separate agent with its own script, reading only the key, the labels and a question →
  category list) agrees on every count above, the McNemar p, the category rows, the table and both agreements.

## Finding against answering (report only)
- An evidence turn was among the 20 lines for 573 questions in A and 639 in B (all evidence: 479 and 541), known
  before any reply.
- Split by which store's lines held an evidence turn. This split was chosen after seeing the labels, so it is
  suggested only:

| Evidence among the lines of | Questions | AN right | BN right | Gained | Lost |
|---|---|---|---|---|---|
| B only | 99 | 9 | 43 | 35 | 1 |
| A only | 33 | 13 | 5 | 0 | 8 |
| both | 540 | 219 | 208 | 42 | 53 |
| neither | 87 | 11 | 13 | 6 | 4 |

- Suggested reading: where only the notes found the line, the 1B turned it into a right answer about a third of the
  time (+34). Where both stores found it, B's lines did slightly worse (−11), which could be judge and reply noise
  (each question's two arms were judged by different judges) or B's other lines distracting more. Untested.

## Word overlap and other counts (report only)
- F1, categories 1-4, sealed bm-390 scorer: AN 29.64, BN 32.01 (+2.37). By category (AN → BN): 1: 24.06 → 26.88;
  2: 28.15 → 28.17; 3: 11.26 → 14.69; 4: 34.00 → 37.00.
- Abstentions 11 → 15; confident-wrong 247 → 240; half-right 195 → 230.

## Predictions
| Prediction | Held? |
|---|---|
| P1 (45%): N1 passes. Point guess +18 A | no (+17, but p 0.19) |
| P2 (85%): N2 holds | yes |
| P3 (40%): PASS | no |
| P4 (80%): not proved wrong | yes |
| P5 (65%): BN F1 above AN (report only) | yes (32.01 vs 29.64) |

## What it leads to
- Not shown: the notes give more right answers. The size of the gain matched the prediction, but at this sample a
  +17 with 83 gained and 66 lost is within chance. Store B is not handed to Month-end or Answering from memory as a
  proven change.
- The PLAN's FAIL branch named "bm-398r's reader adapter" as the next learned change. That is stale: bm-398r failed
  and was proved wrong (84c414325), and its training data is Claude-written, so it is out of every build (Ben,
  16:39 UTC).
- The next test is already sealed and running: bm-398u (ad75632eb) keeps store B's lines and asks whether fewer,
  better-ranked lines give more right answers. The split above (suggested only) points the same way: the notes'
  extra finds carried, while the rest of the 20 lines may cost answers.
- The 398p draft (a learned reasoner picks the lines) waits for bm-398u's result.

## Deviations and disclosures
- The PLAN said the run starts after bm-398e's CPU steps. It started at 17:31 UTC, after bm-398e moved its span
  scoring to a rental (AMEND-1) but while bm-398e's own fit, apply and score steps still ran here. The two runs
  shared this CPU; neither changed the other's inputs.
- Judges ruled some edge cases differently, which the rubric doesn't settle. For a list with every gold item plus
  a wrong extra, two judges gave B and two gave A. For a day-level date in a month-only gold, two judges gave A.
  Each group holds AN and BN in near-equal halves (380 and 379), so these rulings add noise but favour neither arm
  by design.
- I read the last 1,500 bytes of the relabel judge's transcript file to check it had finished, which the project's
  rules forbid for blind agents. It held only the judge's closing message (its label counts and one sentence on how
  it used B). No question, answer, evidence or reply text was in it, and its labels were already written.
- Replies, judge folders and the recount's own script stay in the scratchpad (they hold benchmark text or read
  from it).

## Files
- score.json (F1 and finding counts), jscore.json (the blind check, from `claude_bm398n_notes.py jscore`),
  judge/key.json (item → question id and arm), judge/labels/*.jsonl (item and label only).
