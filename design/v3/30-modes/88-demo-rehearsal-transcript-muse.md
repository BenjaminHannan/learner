# 88 — Demo rehearsal transcript (one-command family demo)

Date: 22 Sep 2026. Prefix `fable_demo88_`. Artifact: `artifacts/fable-demo88-20260921/`.
Script: `scripts/fable_demo88_rehearse.py` (NEW; imports 55b/55/modes54 code, edits nothing).

## Why

Ben wants a single command that replays the family demo so a non-technical
viewer (uncle, dad) can follow it: teach, ask, correct, ask again, then the
notebook-vs-transformer comparison — with no code on screen.

## Design

- Act 1 (family scene, fresh notebook, same ModeScheduler+Listening doorway):
  8 frozen turns. Teach that Mira's mother is Ana, Ana lives in Porto, Mira
  lives in Lisbon; ask where Mira's mother lives (two hops, "Porto"); ask
  where Mira lives ("Lisbon"); correct to Paris; ask again ("Paris"); ask
  about Tom (never taught) and hear an honest "I don't know anyone called
  Tom." Names avoid the 40 Q10 people and 5 Q11 newcomers, so nothing collides.
- Acts 2+3 reuse the 55b comparison byte-for-byte: `run_notebook_55b` for the
  notebook side (120 teachings, 20 two-hop asks, 5 new teachings, 5 new asks,
  20 old re-asks) and `run_baseline_qa` for the transformer (250 QA updates,
  then a fixed 60 s fine-tune per seed, seeds 5401/5402/5403). `--skip-baseline`
  honours fast mode: notebook only, transcript says the comparison was skipped.
- `transcript.md` is plain words throughout: Ben's structured lines are rendered
  from hand-written English (Act 1) and the frozen `en` questions (Acts 2+3);
  Agent lines are the actual replies (already plain templates); statuses become
  "I saved it in my notebook" / "I answered from my notes" / "I did not know,
  so I said so." Timings are plain sentences. The scoreboard is built by
  reloading the run JSON from disk and asserted equal (V3). A frozen
  forbidden-token list (entity IDs, status codes, arrows, braces, `qid`,
  filenames, backticks) is audited and asserted clean (V4). The 116-word
  why-it-wins note is asserted ≤ 150 words, and its three example facts are
  asserted against the frozen 55 lines (this caught a real "Pia vs Keir" slip
  in development). V2 asserts 0 notebook wrong answers across Act 1 asks, the
  20 old-after, and the 5 new.

## Registered runs (per seed/case, never averaged)

| run | mode | notebook old-after /20 | notebook new /5 | notebook wrong | transformer old-after /20 per seed | transformer new /5 per seed | wall-clock |
|---|---|---|---|---|---|---|---|
| 1 | full | 20 | 5 | 0 | 0, 0, 0 | 0, 0, 0 | 471.5 s |
| 2 | fast | 20 | 5 | 0 | skipped | skipped | 0.0 s |
| 3 | fast | 20 | 5 | 0 | skipped | skipped | 0.0 s |

Run1 baseline detail: Q10 before 19/20/20, Q11 before 0/0/0, fine-tune
27,328 / 28,062 / 27,275 steps in 60.0 s each, Q11 after 0/0/0, Q10 after
0/0/0. Wrong writes 0 in all runs. Marks V1–V4 PASS in all three runs.

## What it means

One command now produces a transcript a non-technical viewer can read start
to finish, with the scoreboard exactly matching the run data: the notebook
answers everything and admits what it doesn't know; the crammed transformer
loses the old answers without gaining the new ones, on these runs.

## What it does not mean

No new claim about fine-tuning beyond 55b's registered verdict; no broad
English (structured doorway plus hand-written renderings); the transcript is
a rehearsal script, not a live interactive demo.

## Deviations / questions for Ben

No deviations from PASSMARKS. Question (conservative default taken): the full
transcript shows one sample two-hop exchange plus counts for the other 19 old
questions rather than all 20 exchanges, to stay readable; the JSON holds every
reply. If Ben wants all 20 printed, that's a one-line change.
