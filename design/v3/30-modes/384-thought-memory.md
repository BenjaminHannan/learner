# 384: a memory for the model's own thoughts (thought-memory thread, 2026-09-25 ~19:55 UTC)

Ben, 19:28 UTC (project chat): "what if we gave the model a memory for its thoughts that it could recall?"

Reading picked: "thoughts" = the model's own worked attempts (reasoning steps, creative guesses, what a checker
confirmed and what failed), stored in their own store with their own label, and recalled by meaning when a similar
problem or conversation comes up. Not facts, and never the notebook.

Status: research note plus one proposed first test. Nothing built, sealed or run.

## What the research says (labels: shown = measured in the cited work; suggested = interpretation; untested = ours)
Checked against the arXiv abstracts on 2026-09-25 (and the full text for Dynamic Cheatsheet).
| work | what the memory holds | result |
|---|---|---|
| Reflexion, arXiv 2303.11366 | the agent's own written reflections after a failed try, kept for the next try | shown: HumanEval pass@1 91% vs 80% for plain GPT-4 |
| Voyager, 2305.16291 | a growing library of checked code skills, found by meaning | shown: 3.3x more unique Minecraft items; reuses the library in a new world |
| ExpeL, 2308.10144 | past attempts plus lessons drawn from them | shown: gets better as it collects more experience, no weight updates |
| Buffer of Thoughts, 2406.04271 | reusable "thought templates" drawn from past solving | shown: +11% on Game of 24; Llama3-8B + BoT can rival Llama3-70B |
| Dynamic Cheatsheet, 2504.07952 | short strategies and snippets the model keeps across questions | shown: GPT-4o Game of 24 10% -> 99%, but only because it stored a brute-force Python solver; Claude 3.5 Sonnet AIME more than doubled |
| ReasoningBank, 2509.25140 | strategies drawn from BOTH successes and failures | shown: beats memories of raw transcripts or of successes only (web and coding agents) |
| Experience-following, 2505.16067 | study of what goes wrong | shown: agents copy the output of the most similar memory, so a wrong memory spreads its error; only good-quality entries should be kept |

Two warnings that matter for us:
1. Small models gain least (shown, Dynamic Cheatsheet Table 3): GPT-4o-mini gained little or got slightly worse,
   because it (a) rarely produced correct solutions worth storing and (b) fetched the wrong memories or misused them.
   Our 1B is smaller than any model in these papers, so a gain for it is untested and may not come.
2. Dynamic Cheatsheet's biggest 24-game jump came from storing a whole-puzzle solver. Ben's tool rule (17:47 UTC) forbids
   that: memories may help with steps, never solve the whole puzzle.

Brain side (suggested, textbook psychology and neuroscience, not checked today): people do remember their own thoughts,
and they sometimes mistake an imagined thing for a real one ("reality monitoring", Johnson and Raye 1981). The
hippocampus stores episodes fast and sleep replays them into the slow cortex (complementary learning systems,
McClelland, McNaughton and O'Reilly 1995). Our "better than the brain" part: every thought keeps a hard label, so the
model can never mistake its own guess for something Ben taught.

## Design (untested)
- A separate store, `<state_dir>/thoughts384/thoughts.jsonl`, append-only. One row per attempt:
  problem text, what was tried (the steps or expression), outcome (worked and checked / failed, with where /
  not solved within budget / proved impossible), checked_by (exact checker, user, or unchecked), when, source "own-thought".
- Recall by meaning with the MiniLM retriever the stack already uses (the same recall() shape as 382, a separate store).
  Recalled rows are shown to the model labelled "my earlier attempt", with the outcome.
- Writes: the creative tool, the reasoner and chat turns write here. Only checked rows may be shown as "this worked"
  (the experience-following warning). Unchecked rows are kept but shown only as "I tried this, not checked".
- Never: in the notebook, in the 382 store, used to answer "what did Ben tell me", or holding a whole-problem solver.
  Test puzzles never enter it (code checks exact duplicates).
- Sleep reads it (read-only) to choose what to practise. Checked "worked" rows are today's wins.jsonl; "not solved yet"
  rows are Creative's open-problems shelf; checked sub-results are Creative's pieces library. One store, three uses.

## First test, tm-384 (proposed, $0, CPU, not sealed)
Where: Creative's 24-puzzle harness (scripts/claude_blurt2.py guesser, exact checker), since it is the cheapest
checkable place today. One change, at test time only (no training): what the model sees before its 30 guesses.
- NONE: blurt-3's plain prompt, 30 guesses per fresh puzzle.
- RECALL: the same, plus the 3 past attempts most similar in meaning, from a memory built only on practice puzzles
  (checked hits and checked dead ends, each with its outcome).
- PLACEBO: the same, plus 3 random past attempts from the same memory, same format and length.
Measure (GPT-6 Pro's headline, 19:13 UTC): fresh puzzles solved within 30 guesses; 80 fresh puzzles, 2 seeds.
Proposed marks, to be fixed before any run: PASS if RECALL solves at least 6 more puzzles than NONE and more than
PLACEBO, in both seeds, with 0 test puzzles found in the memory. Proved wrong: RECALL no better than PLACEBO in both
seeds (then any gain came from the longer prompt, not from recall). Prediction (suggested by warning 1): a small gain
or none for the 1B. If it fails, the next single change is to give recall to the new small reasoner (358) instead.
Later, one at a time: dead ends on vs off; recall inside a chat; a second kind of problem.

## Overlaps (Ben 19:22 UTC: threads overlap and work together)
- Creative: the pieces library and open-problems shelf become kinds of row here; the test uses its harness.
- Fix sleep: wins.jsonl becomes the checked "worked" rows; sleep picks practice from "not solved yet" rows.
- Month-end / Benchmarks / Reading: same recall() code as the 382 store, but a separate file with a separate label.
- Sleep research: the new small reasoner (358) is the long-term user; it could call recall between thinking rounds.

## Plain summary for Ben
Giving the model a memory of its own past tries is one of the better-supported ideas: big models that look up what
worked and what failed before solve more new problems. The catch is that small models used it badly in the one
study that tested them, and ours is smaller still, so we test it before building on it. The test is cheap: the same
puzzle guesser with and without its own recalled past tries, against a fake memory, on fresh puzzles.
