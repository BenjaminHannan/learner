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
