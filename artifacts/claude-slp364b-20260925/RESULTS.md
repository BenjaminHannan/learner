# slp-364b results: REGISTERED FAIL (P364b.1 and P364b.5)

Run 2026-09-25, CPU, $0, sealed code and sealed blind bench (both seal files check OK), 80 nights, 0 errors.

| Mark | Bar | Result | |
|---|---|---|---|
| P364b.1 faulty nights rejected by v2 | ≥ 18/20 | 17/20 | FAIL |
| P364b.2 honest nights rejected by v2 | ≤ 1/20 | 0/20 | pass |
| P364b.3 v2 minus v1 catches | ≥ +3 | 17 − 8 = +9 | pass |
| P364b.4 main notebook unchanged and sandbox restored (digest) | 40/40 | 40/40 | pass |
| P364b.5 honest nights: user replies identical under v2 and v1 | 20/20 | 0/20 | FAIL |

Proved-wrong clause (< 15/20 caught or > 2/20 honest rejected): not triggered. The sleeper's own flag caught 4/20.
Per category (v2, v1): post-sleep-people 3/3 (0), file-live-mismatch 2/2 (0), silent-noop 2/3 (0),
made-up-answer 2/2 (1), notebook-write 2/2 (2), minority-wrong 2/2 (2), unlearned-word-answered 1/1 (0),
earlier-word-corrupted 1/1 (1), replays-old-turn 1/1 (1), forgetting 1/2 (1), corrections-ignored 0/1 (0).

## The serious finding: P364b.5, 0/20 (the new-people sandbox breaks the loop)
After a v2 night, teaching a NEW person goes wrong: "Brosheth's spouse is Griteth." is saved as
"Griteth's spouse is Griteth." (142 of 434 user replies on honest nights differ from v1, all of this kind).
Likely cause (inferred from the code, not yet confirmed by a test): the sandbox puts the notebook objects back by swapping in deep copies of their contents,
but other parts of the loop still hold the OLD containers (the ones the sandbox's teaching changed), so after the
night they disagree about who is who. The byte check (P364b.4) passes because the file is restored; the live
objects are not. v2 must not be installed anywhere as it stands. Nothing uses it today.

## The three missed faults (bench opened after the run)
- slp364b-09 corrections ignored after the sleep: v2 never tests a correction after the night.
- slp364b-27 installed word made 100x less confident (answers unchanged in v2's probes): not caught.
- slp364b-31 the word file keeps only tonight's word (an earlier word is lost after a restart): the restart check
  asked only tonight's words, not words known before the night.

## Next (364c, one change set, needs a new blind bench since this one is now opened)
Run the new-people check in a forked copy of the process (the real loop's memory is never touched; files are put
back as now), add one correction to it, and include earlier words in the restart check.

## Addendum (07:35 UTC, from slp-369)
The likely cause above is now better supported: building slp-369, a plain deep copy of the outer notebook's state
reproduced the same symptom, because it also copies the inner notebook the outer one points to. Keeping the inner
object fixed removed it (slp-369 PASSMARKS disclosure). Not re-tested on 364b itself.
