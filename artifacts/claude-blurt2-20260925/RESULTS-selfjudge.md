# Idea self-judge (DEV, CPU, $0) — result 2026-09-25 ~03:10 UTC

Rule registered before the run (PASSMARKS-blurt2.md): if the 1B's own top pick is good on >= 6/10 requests, 333g uses
the self-judge; otherwise the judge must be trained or replaced.

Result (scripts/claude_blurt_selfjudge.py, 300 blurt-1 idea blurts, blind Opus labels):
{"blurts": 300, "good": 44, "auc_self_judge": 0.691, "items": 10, "pick1_self_judge": 2, "pick1_chance_expected": 1.47, "oracle_any_good": 9}

Verdict: the self-judge is NOT used. Its top pick was good on 2/10 requests; picking at random would give about 1.5;
a good idea existed on 9/10. It ranks a little better than chance overall (AUC 0.691) but not enough to pick.

Next (one change): a judge trained on labels. Label source = the approved open-weights teacher (OpenRouter GLM 5.3
Flash), not Claude (provider terms). First check the teacher agrees with the blind judges on these same 300 blurts
(scripts/claude_ideajudge_teacher.py, DEV only). Rule fixed now: the teacher is a usable label source if it agrees on
"good" for >= 85% of blurts AND Cohen's kappa >= 0.5. Otherwise try the stronger teacher once (z-ai/glm-5.3), then
ask Ben.

## Teacher agreement, GLM 5.3 Flash (Mac, $0.016; the first try failed on an API setting, fixed in 8a0650545)
It labelled all 40 DEV requests in the blurt file (1,200 blurts); 300 of them have blind Opus labels.
On those 300: agree on "good" 254/300 (84.7%), kappa 0.567; teacher says good 88, Opus 44, both 43 (it finds 43 of the
44 good ones but also passes 45 the blind judges rejected). "invented" agrees 288/300 (teacher 11, Opus 17).
Verdict under the rule fixed above: NOT a usable label source (84.7% is under 85%; kappa passes). It is too lenient.
Next, as registered: the stronger teacher z-ai/glm-5.3 once (handoff/queue/ideajudge-teacher3.md), then ask Ben.

## Teacher agreement, GLM 5.3 (Mac, $0.20)
On the same 300: agree on "good" 256/300 (85.3%), kappa 0.568; teacher good 82, Opus 44, both 41. "invented" 290/300.
Verdict: passes the rule (>= 85% and kappa >= 0.5), only just. Both teachers are about twice as generous as the blind
judges; the full model is barely different from Flash.

## Next (one change): a trained judge head, registered before running (written ~04:20 UTC)
scripts/claude_ideajudge_head.py: GLM 5.3 labels on the 30 DEV requests WITHOUT Opus labels (900 blurts) train a
logistic head on the 1B's hidden state at the end of the judging prompt (layer and regularisation chosen by grouped
cross-validation on those 30 only). Tested once on the 10 Opus-labelled requests (teacher labels for them unused).
- PASS (333g uses the trained head): its top pick is good on >= 6/10 requests.
- Proved wrong: top pick good on <= 2/10 (no better than the 1B's own judgement).
- Reported: top-3 contains a good one (x/10), AUC vs Opus labels.
Caution stated now: 10 requests is a small test; a pass is a DEV signal, and 333g is judged on the blind 333 panel.
