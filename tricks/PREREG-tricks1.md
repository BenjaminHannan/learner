# Tricks-1: does a small model with tricks beat a big plain model? (pre-registered 2026-10-24)

Thread "Find tricks for more brains per size", branch `claude/project-thread-io8hpv`.
Written before any run. Inference only, no training. The routing/cascade trick belongs to the
leapfrog thread (`claude/project-thread-1gfrhe`) and is not tested here.

## Models
- Small: `Qwen/Qwen3.5-4B` (bf16), the planned worker.
- Big reference: `Qwen/Qwen3.6-35B-A3B-FP8`, the planned boss (36B total, 3B active).
Both with vLLM, chat template, `enable_thinking` set per arm.

## Sets (fixed seed 0, drawn once, saved with the results)
- **GSMH**: 300 random rows of `reasoning-machines/gsm-hard` (grade-school problems with big ugly numbers). Score: |pred - target| <= 1e-4 * max(1, |target|).
- **MATH**: up to 300 rows of `HuggingFaceH4/MATH-500` whose answer parses as a plain number or simple fraction. Same numeric score.
- **POPQA**: 400 rows of `akariasai/PopQA`, 200 with subject popularity s_pop < 1000 (rare facts) and 200 with s_pop >= 1000. Score: any listed answer appears (case-folded) in the reply, standard PopQA scoring.

## Arms
| arm | model | trick | sets |
|---|---|---|---|
| s_plain | 4B | none: think-free, step-by-step, greedy | all |
| s_think | 4B | thinking mode on, one sample, 8k token budget | GSMH, MATH |
| s_vote8 | 4B | think-free, 8 samples (T=0.7), majority vote | GSMH, MATH |
| s_py | 4B | think-free + Python tool (up to 4 calls, 10 s each) | GSMH, MATH |
| s_wiki | 4B | think-free + Wikipedia search tool (up to 3 calls, top 3 intros) | POPQA |
| b_plain | 35B-A3B | none, think-free, greedy | all |
| b_think | 35B-A3B | thinking on, one sample, 8k budget | GSMH, MATH |
| b_wiki | 35B-A3B | Wikipedia tool | POPQA |

## Pass marks (fixed now)
Each trick is judged separately. "Big plain" means b_plain.
- **P1 tool for maths**: s_py >= s_plain + 5 points on GSMH **and** s_py >= b_plain on GSMH.
  Proved wrong if s_py - s_plain < 2 points on GSMH.
- **P2 lookup for facts**: s_wiki >= b_plain + 10 points on POPQA (all 400) **and** on the rare half.
  Proved wrong if s_wiki <= b_plain on POPQA.
- **P3 thinking / voting**: best of (s_think, s_vote8) is within 3 points of b_plain on MATH.
  Proved wrong if both are > 10 points below b_plain on MATH.
- Report tokens generated per question for every arm (cost of the trick), since on the Mac every extra token is time.

## Notes
- 95% intervals by bootstrap over questions; with n=300 a 5-point gap is about the noise edge, so P1/P3 claims are "suggested" unless the interval excludes zero.
- No set is looked at before the run except to check the loaders parse.
- Spend cap: $8 on Vast.
