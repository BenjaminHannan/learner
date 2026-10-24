# Untouched areas: where premonition can improve and no thread is working (2026-10-24)

Labels: **shown** = checked in code, result files or thread status today; **suggested** = reasoning; **untested** = nobody has measured it here.
The village model, the small card experiments, and the borrowed-Qwen assistant are kept separate.

## Already covered (shown, thread status pages and PRs at ~02:45Z)
Wording generalization (PR #101), thinking board / loops (PR #100), bridge between halves (PR #98), ten weaknesses incl. HALT target and G1 guard (PR #99),
multi-step creative puzzles, Qwen backbone stage 1 + Creative-1/2 + Sleep-1 (facts taught into weights) + Mac speed test, leapfrog (creative past frontier, cascade to the big model),
tricks per size (Python tool, Wikipedia lookup, vote, think). The tricks thread's research sweep *reads about* knowing-when-unsure, function calling and long memory, but has no test of them.

## Ranked gaps (end goal: a fast local MacBook assistant that punches above its weight)

| # | Gap | Why it matters (suggested) | Cheap first test, pass mark, and what proves it wrong |
|---|---|---|---|
| 1 | **Remembering the user across weeks** (notebook write / update / read) | Premonition's founding idea, and the thing a personal assistant needs most. Sleep-1 puts 120 facts into weights; nobody tests "what did Ben tell me in May, and has it changed". | **Notebook-1, started** (`notebook1/PREREG.md`): LongMemEval-S, 60 questions, full history vs plain search vs dated notebook vs oracle, Claude Haiku stand-in. Pass: notebook >= search + 8. Wrong if notebook <= search. Then Notebook-2 with Qwen 4B as writer/reader on the PC. |
| 2 | **No scoreboard for real work** | Every thread scores its own toy (village, puzzles, GSM). Nothing says whether a change makes the assistant better at jobs. Without it, v2 can't be judged. | tau2-bench retail (or airline), ~40 tasks, Qwen3.5-4B and 35B-A3B as the agent, Claude Haiku as the simulated customer. Pass: our 35B number lands within 5 points of its published score (harness is trustworthy). Wrong if it is off by > 10 (harness broken). |
| 3 | **Knowing when to look up, ask, or say "I don't know"** | Shown (Tricks-1): with the same Wikipedia tool, the 35B searched only 53 of 400 times and guessed the rest; the 4B searched every time and won 37.5 vs 27.5. A model that guesses confidently is a bad assistant. | Re-run PopQA 400 with a "search when unsure" prompt, and with a confidence-gated rule (search when the answer's token probability < t, t picked on 100 dev items). Pass: >= 35B-with-tool accuracy at <= 50% of the searches. Wrong if gating by confidence is no better than searching at random at the same rate. |
| 4 | **Speed with several agents on the Mac** | Shown: 35B-A3B gives 45 tok/s alone, 30 each at 2, 17 at 4, 10 at 8; Ben's bar is >= 30 each with several. Tricks thread ranked speculative decoding but no one tests it. | mlx-lm speculative decoding (Qwen3.5-0.8B drafting for 35B-A3B, or the built-in MTP head) at 1/2/4 agents, same bench.py. Pass: >= 1.4x at 1 agent and >= 30 tok/s each at 3 agents. Wrong if < 1.15x at 1 agent. Needs Mac disk space. |
| 5 | **A checker for open-ended answers** | Shown: 4B pass@8 on MATH is 95% but vote picks 87.7%; a good checker would pick up to ~7 more points. Creative's checker only works when there are examples to fit. | 4B scores its own 8 MATH answers (self-verify prompt, or a small reward model) and picks the top one. Pass: >= vote + 3 points. Wrong if <= vote. Reuses saved rows; needs a GPU hour. |
| 6 | Long jobs overflow the context (board as working notes) | Agents doing real work hit context limits; premonition's board is a structured working state, so far only inside v1's network. | After #2 exists: agent writes a short "state of the task" note every N steps and drops old turns. Pass: same task success at <= 1/3 of the context. |
| 7 | Safety for real actions on his Mac | An assistant that edits files or sends email must confirm before irreversible steps and resist instructions hidden in web pages. | AgentDojo small subset: attack success rate and task success for 4B/35B, with and without a "confirm irreversible" rule. |
| 8 | Several agents sharing one board (v2 bridge) | Ben wants several agents at once; the bridge thread fixes v1's internal bridge, not agents sharing findings. | Two 4B agents split a task, with vs without a shared notes file. Waits on #2. |

Ownership update (02:40Z, coordinator): #3 and #5 are handed to the tricks thread (designs sent); #4 (MTP guess-ahead + batching server) is the backbone thread's next step. This thread runs #1 and #2.

Not gaps: routing to the boss (leapfrog thread), sealed test (ten weaknesses), loops at test time (state lab, shown +8.2 dev).

## Compute
Vast is out until Sunday; Ben's PC and Mac are queued with backbone, leapfrog and seed-1 runs. #1 runs now on the Claude API (cap $10). #2, #3, #5 need a GPU (PC slot or Modal); #4 needs the Mac.
