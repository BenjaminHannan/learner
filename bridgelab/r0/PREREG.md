# R0 pre-registration: is v1's bridge just a fixed bias?

Written before any condition was scored.

Question. At evaluation `Bridge` hands D the vector `p_cd(unit(ctx_c))`, where `ctx_c` is a frozen EMA of the creative registers. It is the same
vector for every question, so it can only act as a learned constant added to D's register rows. R0 asks whether D's accuracy depends on the
*content* of that constant (does ctx_c carry slow-moving information?) or only on *some* vector of about the right kind being present.

Conditions (D = /tmp/claude-0/w/D-final.pt, creative = W2.pt; same scorer as v1/run.py `final_eval`: `validation_hook`, own-retrieval accuracy):
1. real (saved ctx_c); 2. off (zero vector); 3. ctx_c x0.5, x2 (before unit()), and output vector x0.5, x1.5;
4. ctx_c replaced by (a) creative-register mean over 256 creative dev prompts, (b) over 256 creative warm prompts, (c) one random creative prompt (several draws),
(d) Gaussian vector with the same RMS (several seeds); 5. b = p_cd(unit(ctx_c)) frozen as a plain constant (expect bit-identical to 1).
Also: cosine(ctx_c, alternative) and cosine of the projected output vectors.

Subsets. Fixed seeded random subset of DEV visits (train shards 380-399) and of `validation` visits; n questions reported. All conditions use the same questions.

Decision rules (fixed now).
* "Bias only" is SUPPORTED if every plausible creative summary (4a, 4b, 4c) keeps D dev accuracy within 1.0 point of real.
* "Bias only" is WRONG (ctx_c carries content that D uses) if accuracy moves by more than 1 point for 4a-4c, i.e. accuracy depends on the summary content.
* Scaling ctx_c must leave accuracy unchanged exactly (unit() removes scale); condition 5 must be bit-identical to 1. If not, that is a bug, not a finding.
* Per-question information is impossible by construction either way: the vector is identical for every question, so no condition here can show per-question use of the creative side.
* Sampling noise: with n questions the binomial s.e. of an accuracy near 80% is about sqrt(.8*.2/n); the same questions are used in every condition, so differences between conditions are paired, but the 1-point rule is applied to the raw difference.
* 4d (Gaussian) and off are reported as context, not part of the pass rule.

Deviation note (data): the village shards are regenerated with the v1 generator (seed 0, 250 visits/shard, deterministic per index). The name detector
of the label-free cache is normally fitted on all 380 train shards; here it is fitted on the first 40 train shards (the full train set is not on this machine).
Sanity check: condition 1 and 2 should land near REPORT-V1 (82.0% / 23.6% dev, 46.1% / 20.1% validation).
