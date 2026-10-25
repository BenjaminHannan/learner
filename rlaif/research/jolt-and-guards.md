# JOLT+ vs our RLAIF-1 code, and judge-reward guards (2026-10-24)

Labels: SHOWN = stated in the cited source (I read it) or checked in our code. SUGGESTED = my inference. UNTESTED = nobody has run it on our setup.
Method note: no subagents were available to me, so I read pages directly. Only the paper's HTML up to char 100000 of 123180 was read
(Appendices C-F, incl. beta ablations and full pseudocode, were NOT seen). Check those before trusting any "paper does not say" below.
Paper: https://arxiv.org/abs/2610.10447 (HTML: https://arxiv.org/html/2610.10447). Code: none listed on the arXiv page (SHOWN, abs page, 2026-10-24).

## Part 1. Paper vs our implementation

### What matches (SHOWN)
- Advantage = reward minus the mean of the G siblings, no std division; one centred group per role (paper Eq. 19: A(tau)=R(tau)-(1/G)sum_j R(tau_j)). Ours: `advantages()` in train.py. Match.
- Teacher term: A * log pi(a|s,c) - beta_T * KL(pi(.|s,c) || sg pi(.|s)), reverse KL, reference = snapshot at rollout params (Eq. 18). Ours: teacher loop in train.py with `seq_terms(..., other=student view)`. Match. No separate reference model, no clipping, no importance ratio in the paper; ours has none either. One update per batch, so on-policy.
- Student distillation KL(pi(.|s) || sg pi(.|s,c)) (Eq. 7); JOLT+ adds the student outcome advantage. Direction matches ours.
- Global token average per loss across the whole batch ("divided by the total number of valid completion tokens"). Ours: separate Ns and Nt token counts. Match.
- Rollout temperature 1.0, B=8, G=4 for GSM8K/MATH (Table 3). Ours 8 x 4. Match. (AppWorld row: B=2, G=4, 300 steps.)

### Mismatches, ranked by expected impact

1. beta_S = 1.0 in ours; paper uses 0.1 in all settings (Table 3). The paper says "Unit teacher and student coefficients are unstable in this setting" and "coupling coefficients below one" work best (Appendix A.1, SHOWN). Our 1.0 is the exact value the authors report as unstable. Our SPEC even says "paper does not publish values", which is now wrong.
   Fix: `--beta-s` default 1.0 -> 0.1 (train.py line with `--beta-s`). Also update SPEC.md.
2. beta_T = 0.05 in ours; paper uses 0.001 for MATH, LCBv6, AppWorld, TMax; 0.03 only for GSM8K (Table 3; full-objective Table 8 also 1e-3). 50x too strong would tie the teacher to the student and kill the "teacher can use the hint" signal.
   Fix: `--beta-t` default 0.05 -> 0.001.
3. Privileged context c. Paper AppWorld: a task-local "skill" system message with success analysis, mistake analysis and a golden workflow, summarised from earlier attempts (by a strong model), retrieved by UCB score; empty bank = no hint. Other tasks: GSM8K verified answer; LCB a successful sibling response, else execution feedback; TMax the private verifier files (SHOWN, via my extract of the paper's task descriptions; exact skill prompt not seen).
   Ours: literal reference tool-call list + reference reply + Sonnet critique of the worst student attempt. The paper's central worry is a teacher that "solve[s] tasks through shortcuts unavailable to the student" (abstract). A copy-this-call-list hint is the extreme shortcut. Smallest change in `hint_block` / the `cs` construction: when a sibling attempt has check_frac==1, give its tool-call trace instead of the reference; keep the critique; fall back to the reference only if no sibling passed. SUGGESTED, UNTESTED. Monitor `teacher_success - success` in log.jsonl: if the gap is huge and student success does not follow, the teacher is not meeting the student.
4. Student KL estimator. Paper pseudocode and token weights use the sampled-token log-ratio (A_S+ = A + beta_S*Delta_t, Delta = log pi(a|s,c) - log pi(a|s) at the sampled token, Eqs. 20 and the "JOLT+ only" line). Ours uses the exact full-vocab KL and a separate pg term. Same direction and same expectation to first order; ours is lower variance and costs more memory (already chunked). Leave as is. SUGGESTED equivalent, UNTESTED.
5. Learning rate / steps. Paper: full fine-tune, lr 1e-6 to 2e-6 (1e-7 AppWorld), 150-300 steps. Ours: LoRA r=32, lr 1e-5, 30 steps. LoRA usually needs a larger lr, so 1e-5 is plausible, but 30 steps is 5-10x shorter than any paper run; a "tie" at 30 steps says little. Paper also reports OPSD alone deteriorates later in training and JOLT+ reaches GRPO's training reward in about 1.8x fewer updates (SHOWN). Add `--steps` 100+ if budget allows. No code change needed.
6. Distillation temperature: the extract mentions temperature 1.1 for the student reverse-KL objective but the text was garbled ("1.11.1"). Ignore; UNTESTED.
7. Grad clipping at 1.0 in ours; paper silent. Keep.

Paper AppWorld numbers for orientation (SHOWN, Table 1, dev pass rate): GRPO 62.20, OPSD 29.49, pi-Distill 59.85, JOLT 51.92, JOLT+ 72.09. Student there is Qwen3-4B-Instruct, not our 1.7B; do not expect the same gap.
MATH teacher ablation (SHOWN, Table 8, step 75): OPSD 62.95, OPSD+student reward 66.52, JOLT KL-only 65.39, outcome-only 67.87, JOLT full 72.10, JOLT+ 73.80.

### Top 3 code changes
1. `--beta-s 0.1` (SHOWN as paper value; unit coefficients reported unstable).
2. `--beta-t 0.001` (SHOWN as paper value for AppWorld).
3. Teacher hint from a passing sibling trace, reference only as fallback (SUGGESTED, UNTESTED). Run as a separate arm; one change at a time, per CLAUDE.md.
Pass marks stay as in SPEC.md; changes 1+2 are a bug fix to hyperparameters, change 3 is an experiment.

## Part 2. Reward-hacking guards for an LLM-judge reward

Evidence base (all read only at abstract/summary level unless noted):
- Mahmoud et al., Reward Hacking in Rubric-Based RL, https://arxiv.org/html/2605.12474v1 (read). SHOWN: a weak training verifier (GPT-4o-mini) gave about 7x more incorrect credits than a strong one (GPT-OSS-120B); stronger verification cut but did not remove hacking; rubric-free judges still preferred the base model on 78.4% of prompts while rubric judges preferred the RL checkpoint on 85.8%; a verifier-free "self-internalization gap" peaked within 100 steps of true-quality peak and stopping there lost <=0.13% vs 0.45-1.81% for stopping at the end. NOT tested there: ensembles as reward, length control, KL ablation, rubric changes.
- Gradient regularisation slows judge hacking (search snippet only, not read): https://arxiv.org/pdf/2602.18037
- Evaluator ensembles under hacking, covariance analysis (snippet only): https://arxiv.org/pdf/2608.08002
- Hack-Verifiable Terminal Bench (title only; PDF would not parse): https://arxiv.org/pdf/2608.22103
- Verifier false positives in RLVR (snippet only): https://arxiv.org/pdf/2607.11022
- Practitioner note: criteria that are surface-satisfiable get exploited (snippet only): https://www.paperinstruments.com/blog/rubric-judge

### Candidate guards, as they apply to us
- Hidden end-state checks / check-only held-out eval: we already have both. Checks are machine-verified, so the policy cannot argue with them. SHOWN in our SPEC (alarm: Sonnet +15 while held-out success <+3).
- Judge strength / second judge: SHOWN stronger verifier helps (above). We already spot-grade 5% with Opus.
- Judge ensemble as reward: UNTESTED in the sources I read; costs 2x grader dollars.
- Rubric randomisation / paraphrase: no source read; SUGGESTED only.
- Length penalty: max_new=384 and max_total=2048 already cap length; the Qwen model cannot pad much. Low priority. SUGGESTED.
- KL anchor to base model: ours has no reference-model KL (the JOLT KLs are teacher-vs-student, not anchors). Paper has none either. With LoRA, lr 1e-5 and 30 steps, drift is small. SUGGESTED low priority; no evidence in what I read.
- Early stopping on a hack-free signal: SHOWN (Mahmoud, above).

### Top 3 for reward = 0.6 checks + 0.4 Sonnet
1. Make the soft score unable to pay without the checks (SUGGESTED, UNTESTED). Change `reward()` so the Sonnet term is scaled by check fraction, e.g. r = f * (0.6 + 0.4*s/10). Then a polished reply with the wrong end state earns 0 from the judge, so the cheapest hack (flattering or confident text) no longer pays. Costs one line; also removes the "claims success without doing it" payoff. Run it identically in both arms.
2. Held-out check-only monitor each `--save-every` plus a stop rule (SHOWN technique, Mahmoud; rule is ours). Evaluate each saved adapter on the 100 held-out tasks with `--eval-only` (no `--eval-grade`, so $0), stop at the peak of held-out success; extend the alarm in SPEC to also fire on rising Sonnet-minus-check-frac gap in log.jsonl (`sonnet/10 - check_frac`). Already half in SPEC.
3. Cross-model audit of the judge on the high-reward tail (SUGGESTED, partly SHOWN that stronger verifiers cut incorrect credits). Instead of a uniform 5% Opus slice, send the top-reward 5% of rollouts per step (plus the uniform slice) to Opus and log Sonnet-minus-Opus. Rising disagreement on the top tail is the signature of gaming. Log-only first; use as reward (min of the two) only if it fires. Extra cost small.

## Open items
- Appendix C-F of the paper (beta ablations, full pseudocode, optimizer, LoRA vs full FT, AppWorld skill prompt) not read; fetch with offset=100000 on the HTML or read the PDF before finalising "no clipping / no ratio".
- Hack-Verifiable Terminal Bench content not read.

## Lead check (2026-10-24)

- Verified against arXiv 2610.10447 HTML, Table 3: beta_T = 0.001 (0.03 on GSM8K), beta_S = 0.1 on all settings; "Unit teacher and student coefficients are unstable in this setting" (Appendix A.1). Flags exist; the running RLAIF-1 keeps its preregistered 0.05 / 1.0 so its result stays interpretable.
- Guard 1 is implemented as `--reward-gate` (off by default).
