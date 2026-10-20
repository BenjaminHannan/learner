# Fix round 2 for CODE-REVIEW-080c9bdba.md (coordinator GO, Oct 20; $0 CPU; no runs beyond the identity checks)

## Step 1 first: old-vs-new bit identity, flag off (62cf9ac36 vs this branch)
Final checkpoint sha256 after 3 updates, same flags in both trees. Run twice: on the fix-round-1 code before any round-2 edit, and on the
final round-2 code (same results both times):
| config | flags | old (62cf9ac36) | new |
|---|---|---|---|
| G1 exact | --guard kfsoft --kl-replay-rows 32 --kl-weight 30, harm on the 6,800 DEV at every step (as the round-G G1 runs) | 3e5c13359bd13e00 | 3e5c13359bd13e00 |
| replay KL | --guard replay --replay-loss kl --kl-replay-rows 32 --kl-weight 10 | 07f65e5bc7e1bddd | 07f65e5bc7e1bddd |
| A1F | --guard replay --replay-loss kl --replay-freeze --kl-replay-rows 32 --kl-weight 10 | e0d004bb487ecc04 | e0d004bb487ecc04 |
| replay CE | --guard replay --replay-loss ce --kl-replay-rows 32 --kl-weight 10 | 8de74c6a4c3152ee | 8de74c6a4c3152ee |
(G3 config from round 1: b1b93cbf11436d7a both.) All identical, so the code that produced G1's numbers is the code E0 would run on.

## Findings
| # | finding | resolution |
|---|---|---|
| 3 | identity check covered only kfsoft | step 1 above: G1-exact, replay KL, A1F and replay CE all identical |
| 2 | label sha recorded, not compared | the labels' train.jsonl must have DIARY_TRAIN_SHA256 (the pin the diary pool already uses) unless --diary-any; tested both ways |
| 1 | after a zero-KL measurement the uniform p still used choice | replay_priority_weights is the draw's weight rule; when every weight is 0 (KL 0 / NaN / negative / families under 8 rows) p goes back to None, so the draw is the control's randint; tested: a zero-KL and an all-NaN run draw exactly the control's sequence |
| 4 | E0 rule differed from analyze.py | final_checkpoint_of follows analyze.py's rule with its wording, including the "nights after nights_run ignored" note; night discovery is domain/score.py's; a test checks every note template appears verbatim in analyze.py |
| 5 | e0.json written only at the end | resolve_runs checks every run (summary, nights, final, parent on disk) before any model loads; e0.json is rewritten after each run; tested |
| 6 | log percentages disagreed with the draw | the "@u top families" line prints the draw's own weights (replay_priority_weights) and their S |
| 7 | label conflicts silent | prompts listed under more than one family are counted and printed (first row's family kept); tested |
| 8 | duplicated helpers in e0_score.py | main uses domain.analyze.sha256_file and domain.score.night_checkpoints and asserts SMALL_SHA == learn_probe.DEV_IN_DIST_SHA256. Still local and open: BIG_SHA (the repo pins no 6,800-DEV sha) and the small sha() used by check_devs, kept so the refusal tests run without the repo's torch stack |
