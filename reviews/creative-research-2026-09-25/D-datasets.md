# D. Checkable training problems for a 1B learner (verified 2026-09-25)

Scope: sources where an exact or strong checker decides "right/wrong", ordered toward real assistant work.
All licences below were read from the HF API tags / dataset card or the repo LICENSE file on 2026-09-25
(GitHub API was blocked; raw.githubusercontent.com LICENSE files were read instead). "Verified" = I saw it; "unverified" = claim from paper/memory, not re-checked.

Legend: **Checker** exact = string/set/value match or rule verifier; tests = run code against I/O or asserts; partial = LLM judge or self-written tests.
**Gen.** = who wrote the reference solutions. **Flags** = licence problems, held-out overlap, Claude-written text.

Global caveats
- Competitive-programming statements (Codeforces, AtCoder, LeetCode, etc.) are copyrighted by the sites; the HF licence covers the dataset packaging. This is the normal grey zone every open code model uses; note it, do not panic.
- Anything under CC-BY-**NC** (non-commercial) is fine only while the project stays non-commercial research. Marked NC below.
- For our loop we only need **prompts + a checker**. We do not need anyone's solutions. So a dataset whose *solutions* came from GPT/R1 is still usable if we drop the solution column. That matters most for "Claude-written" rows: drop them entirely (prompt text too, if the prompt was Claude-written).

---

## 1. Procedural generators (unlimited, code-checked)

### 1a. Reasoning Gym — `github.com/open-thought/reasoning-gym` (pip `reasoning-gym`)
- Licence: **Apache-2.0** (LICENSE: "Apache License Version 2.0, January 2004"). Verified.
- Size: unlimited; 104 task generators listed in GALLERY.md (arithmetic, base_conversion, calendar_arithmetic, time_intervals, countdown, puzzle24, sudoku, mini_sudoku, word_ladder, cryptarithm, knights_knaves, zebra_puzzles, codeio, bf, maze, shortest_path, number_sorting, letter_counting, spell_backward...).
- Checker: exact, per-task `score_answer()`; multi-solution tasks (Countdown, 24, Rubik) are checked by evaluating the answer, not string-matching.
- Ladder: **yes**. Each task has config knobs (e.g. `min_value/max_value`, number count, grid size, `difficulty`) and a built-in `coaching` curriculum module (`BaseCurriculum`, `CurriculumExperiment`).
- Gen.: code (no model). 
- **Flag: task `gsm_symbolic` is built from GSM8K templates** (gallery sample: "12 students playing basketball ... #### 70" with GSM8K-style `answer_cot`). EXCLUDE it. Also skip `arc_agi`/`rearc` if ARC is ever used as a held-out test.
- Sample (puzzle24): `Make 24 using 4, 3, 9, 8. You can only use each number once...` → any expression that evaluates to 24.
- Fit for 1B: **best starting point**. Start at tiny settings (chain_sum with 2 terms, 3-number countdown, 4x4 mini_sudoku) so hit rate is 30-70%, then turn knobs.

### 1b. Enigmata — code `github.com/BytedTsinghua-SIA/Enigmata`, data `BytedTsinghua-SIA/Enigmata-Data`
- Licence: code **Apache-2.0** (repo LICENSE, verified); pre-built data **CC-BY-NC-4.0** (HF tag, verified). Run the generators yourself to stay on the Apache side.
- Size: 36 tasks in 7 categories; generators unlimited. Checker: rule-based verifier per task (exact).
- Ladder: yes, "precisely controllable difficulty parameters" per generator (README).
- Gen.: code. Flag: data folder includes `arc_agi`, `big_bench_symbolic` (BIG-Bench-derived). Not on our held-out list, but note.
- Sample: not fetched (HF viewer returned 500). Tasks include binario, campsite, car_painting, sudoku-type grids.
- Fit: good second generator family; many tasks tuned for 7B-32B, so start at the easiest level.

### 1c. SynLogic — `MiniMaxAI/SynLogic`, code `github.com/MiniMax-AI/SynLogic`
- Licence: **MIT** (HF tag + repo LICENSE "MIT License Copyright (c) 2025 MiniMax"). Verified.
- Size: `easy` 15,837 train (27 tasks, "target 7B"), `hard` 32,840 train (35 tasks, "target 32B"); plus validation. Generators in repo.
- Checker: per-task verifier (exact). Ladder: easy/hard configs + per-task difficulty knobs.
- Gen.: code. **Flag: mixed Chinese and English** (a `web_of_lies` row was all Chinese) — filter to English. Tasks mirror BBH/BBEH styles (web_of_lies, boolean_expressions) and ARC; not on our held-out list.
- Fit: the "easy" split is already hard for 1B; use it as the rung after Reasoning Gym.

### 1d. Countdown / Game of 24 files
- `nlile/24-game`: **Apache-2.0** tag (verified), 1,362 puzzles, fields `numbers`, `solutions`, `solvable`, **`solved_rate`** (human solve rate, e.g. 0.988) and `mean_time` → a ready-made human difficulty ladder. Sample: `[1,1,1,8] → (1+1+1)×8`. Checker: evaluate expression = 24 and uses each number once. Source is a puzzle site scrape; treat licence claim as uploader's.
- `Jiayi-Pan/Countdown-Tasks-3to4`: **no licence stated** → drop; use Reasoning Gym `countdown` instead (same task, Apache).

### 1e. KOR-Bench — `github.com/KOR-Bench/KOR-Bench`
- Code Apache-2.0 (verified). It is an **evaluation benchmark** (the repo says "evaluation code for the paper"). Treat as held-out; do not train. Dropped from training list.

### 1f. Wordle
- No verified permissively-licensed Wordle training set found (`willcb/V3-wordle`, `predibase/wordle-sft` have no licence tag). Wordle is multi-turn; a 50-line game engine with a public word list is the easy route. Not needed early.

---

## 2. Human-made puzzles with answers

### 2a. Lichess puzzles — `Lichess/chess-puzzles`
- Licence: **CC0-1.0** (HF tag, verified). Size: **6,100,952** puzzles, updated monthly (card: last update 2026-09-07).
- Fields: FEN, Moves (UCI), **Rating** (Glicko, ~400 to ~3000), RatingDeviation, Popularity, NbPlays, Themes (e.g. `mateIn1`, `endgame`), OpeningTags.
- Checker: exact on the move sequence; better: python-chess, accept any move that mates for `mateIn1` (some puzzles have alternate mates).
- Ladder: **yes, the Rating field**, plus themes (mateIn1 < mateIn2 < long).
- Gen.: games by humans, solutions by Stockfish. No contamination.
- Sample: `FEN 8/8/4k1p1/2KpP2p/5PP1/8/8/8 w - - 0 53, Moves g4h5 g6h5 f4f5 ..., Rating 1569, Themes [crushing, endgame, long, pawnEndgame]` (first move in `Moves` is the opponent's setup move).
- Fit: a text-only 1B reading FEN is weak; expect near-0 except `mateIn1` with rating < 1000. Nice side-rung, not core.

### 2b. Sudoku
- `sapientinc/sudoku-extreme`: 3,831,994 train / 423k test, field `rating` (tdoku backtracks) — good ladder, **but no licence on the card** (sources: Kaggle, tdoku benchmarks, enjoysudoku forum). `sapientinc/sudoku-extreme-1k` is tagged **ODC-BY** (1k rows). Sample: `5...27..9..41......` → `58342716997413652...`, rating 18.
- `nakashi104/sudoku-1million`: **CC0-1.0**, derived from Kaggle "1 million Sudoku games" (stated CC0). Easy puzzles only.
- `Ritvik19/Sudoku-Dataset`: tagged Apache-2.0 but card says each Kaggle source "may have its own licensing terms" → treat as unverified.
- Checker: exact grid match (unique solution) or rule check.
- Recommendation: **generate** Sudoku with Reasoning Gym (`mini_sudoku` 4x4, then `sudoku` with fewer blanks) — licence-clean, ladder by number of blanks. Full 9x9 is near 0 for a 1B without a scratchpad.

### 2c. Crosswords (plain clues)
- No English plain-crossword clue set with a clear training licence was verified. `albertxu/CrosswordQA` is `license:unknown` and mostly NYT-style (NYT content is copyrighted). `azugarini/crossword-clues-QA` is Apache-2.0 but **Italian**, 1,171 rows. Dropped.

### 2d. Cryptic crosswords — George Ho's "Cryptic Crossword Clues" (`jeggers/crosswords` mirror; source cryptics.georgeho.org)
- Licence: **ODbL** (database) + "Database Contents License" for contents (card, verified). **Flag:** the clues themselves are from The Times, Guardian etc. scraped via blogs; the curator can license the database, but the clue text copyright is the publishers'. Grey; I would not use it.
- Size: 660,613 rows. Sample: `Soft cases used by opera violinists (7) → RAVIOLI` (Times 27915). Checker: exact answer + letter count.
- Fit: near 0 for a 1B anyway.

### 2e. NYT Connections
- `tm21cy/NYT-Connections` (358 puzzles, tagged CC-BY-4.0) and `eric27n/NYT-Connections` (tagged Apache-2.0; "All game information was collected from the NYTimes archive").
- **Flag: NYT owns the puzzles; an uploader's licence tag does not change that. Do not train.** If wanted, build Connections-style puzzles from WordNet / own category lists (checker: exact set partition, ladder = how related the red-herring groups are).

---

## 3. Coding with tests

| Name / HF id | Licence (verified) | Size | Checker & harness | Ladder | Gen. of solutions | Flags |
|---|---|---|---|---|---|---|
| MBPP `google-research-datasets/mbpp` | CC-BY-4.0 | full: 374 train / 500 test / 90 val / 10 prompt; `sanitized` smaller | tests: 3 `assert` lines per task, run in-process (no sandbox shipped) | no (all easy) | human | MBPP **test** is a common benchmark: train split only |
| APPS `codeparrot/apps` (repo `hendrycks/apps`) | MIT (HF tag + repo) | 10,000 (5k train/5k test) | tests: stdin/stdout or `fn_name` I/O JSON; HF loader is a script (`trust_remote_code`) | yes: introductory / interview / competition | human | APPS test used as a benchmark |
| TACO `BAAI/TACO` | Apache-2.0 | 25,443 train / 1,000 test | tests: `input_output` JSON (stdin or fn_name); avg ~200 tests/problem in test split | yes: EASY, MEDIUM, MEDIUM_HARD, HARD, VERY_HARD + skill tags | human | train includes APPS/CodeContests problems |
| CodeContests `deepmind/code_contests` | CC-BY-4.0 (HF; repo Apache-2.0) | 13,328 train per paper (HF viewer indexes 3,762) / 117 valid / 165 test | tests: public + private + generated stdin/stdout; incorrect solutions included | yes: `difficulty`, `cf_rating` | human (many langs) | keep test split out |
| CodeContests+ `ByteDance-Seed/Code-Contests-Plus` | CC-BY-4.0 (card + LICENSE) | 11,690 problems; configs 1x-5x = 25-98 tests avg | tests: generator + validator programs per problem; run in SandboxFusion (Apache-2.0) | via CodeContests ratings | human; test generators by an LLM agent (model not stated on card) | built on CodeContests |
| LeetCodeDataset `newfacade/LeetCodeDataset` | Apache-2.0 tag | v0.3.1: 2,641 train / 228 test | tests: `check(candidate)` asserts, `entry_point` like `Solution().twoSum` | yes: Easy/Medium/Hard + date | canonical from GitHub; `response` column LLM-written (model not stated on card) | LeetCode text copyright; drop `response` |
| KodCode-V1 `KodCode/KodCode-V1` | **CC-BY-NC-4.0** | 484,097 train + 3,335 `use_with_caution` | tests: pytest files (or stdio) written by **GPT-4o**; has `benchmark_similarity` vs HumanEval/MBPP | yes: `gpt_difficulty` from GPT-4o pass rate over 10 tries | **GPT-4o-0513** (solutions + tests + questions) | NC; drop `use_with_caution` (benchmark-near) |
| rStar-Coder `microsoft/rStar-Coder` | CC-BY-4.0 | 418K problems, 580K solutions; configs seed_/synthetic_ × sft/rl/testcase | tests: I/O lists; inputs from GPT-4o-written generators, outputs by majority vote of **QwQ-32B** | test "scale" varies; no explicit label | **QwQ-32B** (Qwen), inputs GPT-4o | "seed" = human problems; synthetic = GPT-4o problems |
| OpenCodeReasoning `nvidia/OpenCodeReasoning` | CC-BY-4.0 | 567,850 (split_0) + 167,405 (split_1) | none shipped; questions from TACO/APPS/CodeContests/Codeforces | `difficulty` field | **DeepSeek-R1** | says CodeContests & open-r1 test excluded; other sources' test splits may be in |
| PrimeIntellect `verifiable-coding-problems` | **none stated** | 144,169 | stdin/stdout `verification_info` | metadata difficulty | mixed | no licence → **drop**; use the original APPS/TACO |
| SYNTHETIC-1 `PrimeIntellect/SYNTHETIC-1` | Apache-2.0 | 1,994,262 traces | mixed: tests, symbolic math, **LLM judge** | no | **DeepSeek-R1** | raw traces; not needed |
| self-oss-instruct `bigcode/self-oss-instruct-sc2-exec-filter-50k` | ODC-BY | ~50k | partial: the model's own tests, executed | no | **StarCoder2-15B** (open) | self-tests are weak checkers |

Samples:
- MBPP 601: "Write a function to find the longest chain which can be formed from the given set of pairs." Tests: `assert max_chain_length([Pair(5, 24), ...], 4) == 3`.
- TACO/APPS: Codeforces-style story + stdin/stdout pairs, e.g. APPS 1259/D "Polycarp has n different binary words..." `input '4\n4\n0001...'`.
- LeetCode: `two-sum`, starter `class Solution: def twoSum(...)`, test `assert candidate(nums=[3,3], target=6) == [0,1]`.
- KodCode (Leetcode subset): "determine if s can be transformed into t by at most one edit" + pytest file; `gpt_pass_trial_num: 3` → `gpt_difficulty: hard`.

Sandbox: none of these ship a sandbox except CodeContests+ (SandboxFusion) and LeetCodeDataset ("sandboxed execution environment" in repo). All tests are **visible** in the data; hide them from the prompt yourself and run in a subprocess with time/memory limits (no network).

### 3b. Real-repo tasks (for later, not for a 1B now)
- **SWE-Gym** `SWE-Gym/SWE-Gym`: MIT; 2,438 instances from 11 Python repos (real GitHub issues/PRs, SWE-bench style). Checker: repo's FAIL_TO_PASS/PASS_TO_PASS tests in Docker. Clean of Claude text (instances are real issues); the paper's agent trajectories are a separate thing.
- **R2E-Gym** `R2E-Gym/R2E-Gym-Lite`: HF card has **no licence tag** (repo Apache-2.0); 4,578 train envs. Paper: SFT trajectories collected with **Claude Sonnet 3.5-v2** → never use their trajectory sets. Problem statements are partly LLM back-translated (model not confirmed) → **flag**.
- **SWE-smith** `SWE-bench/SWE-smith`: MIT; card says 50,137 instances from 128 repos (viewer shows 59,136 rows). Bugs are partly LM-generated ("LM Modify/Rewrite") and **issue text is LM-generated**; the paper's expert model is **Claude 3.7 Sonnet** (trajectories). Which LM wrote bugs/issues is not confirmed → **flag: may contain Claude-written text; exclude unless provenance per row is shown**.
- Fit for 1B: hit rate ≈ 0. These need long context, tool use, and file editing. Revisit only after function-level coding works.

---

## 4. Assistant tasks with checkable answers (non-maths, non-code)

### 4a. Function calling — xLAM / APIGen `Salesforce/xlam-function-calling-60k`
- Licence: **CC-BY-4.0** (HF tag); **gated** (accept terms on HF). Ungated full mirror `minpeter/xlam-function-calling-60k-parsed` (CC-BY-4.0, 60,000 rows) verified.
- Checker: **exact** match of function name + JSON arguments (normalise key order/types); supports parallel calls.
- Ladder: partial: number of calls per query (1 vs parallel), number of candidate tools.
- Gen.: **DeepSeek-V2-Chat, DeepSeek-Coder-33B, Mixtral-8x22B, Mixtral-8x7B** (APIGen paper), filtered by format + execution + semantic checks.
- Flag: built to score well on **BFCL (a test set)**; BFCL itself (`gorilla-llm/Berkeley-Function-Calling-Leaderboard`, Apache-2.0) must stay held out.
- Sample: user "Fetch details for product 456789 with locale 'es_ES'." → `product_id({"is_id": 456789, "locale": "es_ES"})`.
- Fit: **good early assistant rung**: short, exact, and a 1B can get single-call cases right often.
- Others: `Salesforce/APIGen-MT-5k` is **CC-BY-NC-4.0** (multi-turn, harder). `Team-ACE/ToolACE` Apache-2.0 but LLM-generated dialogs (model not verified; checker weaker) → skip for now.

### 4b. Calendar / meeting scheduling — NATURAL PLAN `github.com/google-deepmind/natural-plan`
- Licence: code Apache-2.0, "All other materials ... CC-BY 4.0" (README, verified).
- It is a **benchmark** (Trip Planning, Meeting Planning, Calendar Scheduling; eval scripts only; no train split). **Flag: treat as a held-out test.**
- For training, use generators: Reasoning Gym `calendar_arithmetic`, `time_intervals` (exact), and a small in-house meeting-slot generator (random busy blocks → exact free slot; ladder = people × days × constraints).

### 4c. Instruction following with code-checked constraints
- `allenai/RLVR-IFeval`: **ODC-BY**, 14,973 rows. Prompts sampled from the Tulu 2 SFT mix + one IFEval constraint; `ground_truth` JSON names the verifier (e.g. `verify_keyword_frequency, N=17, word="nonsensorial"`). Checker: exact Python function.
  - **Flag 1: the constraints are exactly IFEval's constraint types (IFEval is a held-out test).** Training on them makes IFEval a measure of practice, not transfer. Use only if IFEval is dropped as a test, or keep one constraint family out.
  - **Flag 2 (checked here): 140 prompts contain GSM8K *train* questions verbatim** (0 GSM8K test). Filter them if "never train on GSM8K" covers the train split.
- `allenai/IF_multi_constraints_upto5`: **ODC-BY**, 95,373 rows, up to 5 constraints from IFEval (25 types) + IFBench-Train (29 new types). Same IFEval flag; you could keep only the 29 IFBench-train types. **Checked here: 2,133 prompts contain GSM8K *train* questions verbatim (0 GSM8K test)** — filter them out.
- Ladder: yes, number of constraints (1 → 5).
- Gen.: prompts from human/LLM chat mixes; responses not needed (model writes its own; checker is code).
- Fit: good; format constraints (word count, JSON, no commas) are checkable and a 1B can hit them.

### 4d. SQL — Spider `xlangai/spider`
- Licence: **CC-BY-SA-4.0** (HF tag). 7,000 train / 1,034 validation. The SQLite databases are not in the HF repo (download from the Spider site).
- Checker: **execution match** (run gold and predicted SQL on the DB, compare result sets); exact-string match is too strict.
- Ladder: yes, Spider hardness levels (easy/medium/hard/extra) computable from SQL structure.
- Gen.: human (Yale students). Sample: "How many acting statuses are there?" → `SELECT count(DISTINCT temporary_acting) FROM management`.
- Share-alike: fine for training; a released *dataset* derived from it must stay CC-BY-SA.
- Alt: `b-mc2/sql-create-context` CC-BY-4.0 (WikiSQL + Spider questions with CREATE TABLE context).

### 4e. Unit conversion, regex, JSON extraction
- No verified, licence-clean, checker-backed training set found that beats a generator. `paraloq/json_data_extraction` (Apache-2.0, <1K) was written by **Gemini-Pro** and is labelled a benchmark. Recommend in-house generators:
  - unit conversion: `pint` library → exact numeric answer with tolerance; ladder = single unit → compound units → multi-step.
  - regex: generate target string sets, check the model's regex with `re.fullmatch` on held-out positive/negative strings.
  - JSON extraction: fill a random record into a templated email/log, ask for JSON, check exact field match.
  Reasoning Gym also has `number_format`, `base_conversion`, `string_manipulation`.

---

## Recommended ladder (easiest → most real-world)

1. **Reasoning Gym, small settings** (Apache-2.0; exclude `gsm_symbolic`). Unlimited, exact, knob-driven difficulty, so the hit rate can be tuned to ~30-60% from day one.
2. **Reasoning Gym "assistant-flavoured" tasks + own generators**: calendar_arithmetic, time_intervals, number_format, unit conversion (pint), JSON extraction templates. Same exact checkers, closer to real requests.
3. **Instruction-following constraints** (`allenai/IF_multi_constraints_upto5`, ODC-BY; keep IFBench-train constraint types, drop GSM8K rows). Ladder by constraint count; checks form, not facts.
4. **Function calling** (xLAM 60k, CC-BY-4.0, open-model generated). Exact name+argument match; single call → parallel calls. Keep BFCL held out.
5. **Beginner code with tests**: MBPP train (CC-BY-4.0, human) + APPS introductory + TACO EASY (MIT / Apache-2.0, human). Run tests in a subprocess sandbox; hide tests from the prompt.
6. **Harder code with graded tests**: TACO MEDIUM → CodeContests(+) by `cf_rating` (CC-BY-4.0), LeetCodeDataset Easy/Medium (drop `response`). rStar-Coder seed problems for volume (drop the QwQ solutions if not wanted).
7. **SQL by execution** (Spider train, CC-BY-SA-4.0): real-world "query this data" work with an execution checker.
8. (Later) **SWE-Gym** (MIT, real issues, Docker tests). Hit rate ≈ 0 for a 1B; keep as the far rung. Avoid SWE-smith / R2E-Gym text until Claude provenance is ruled out.

Side rungs (optional): SynLogic easy (MIT, English rows only), Enigmata generators (Apache code), Lichess mateIn1 by rating (CC0), 24-game by `solved_rate` (Apache tag).

## Licence / contamination problems found
- **Do not train**: NYT Connections sets (NYT copyright despite CC/Apache tags); NATURAL PLAN, KOR-Bench, BFCL, HumanEval, IFEval (benchmarks); cryptic-clue text (publisher copyright; grey).
- **Non-commercial only**: Enigmata-Data (CC-BY-NC; generators are Apache), KodCode-V1 (CC-BY-NC, GPT-4o written), APIGen-MT-5k (CC-BY-NC).
- **No licence stated → dropped**: PrimeIntellect verifiable-coding-problems, Jiayi-Pan Countdown, sapientinc/sudoku-extreme (use the ODC-BY 1k version or generate), R2E-Gym-Lite card.
- **Held-out contamination**: Reasoning Gym `gsm_symbolic` (GSM8K templates); RLVR-IFeval has 140 and IF_multi_constraints_upto5 has 2,133 verbatim GSM8K-train questions (0 test; first-80-char match) and both use IFEval constraints; xLAM was tuned toward BFCL.
- **Claude-written text risk**: SWE-smith (LM-generated bugs/issues; Claude 3.7 Sonnet used for trajectories), R2E-Gym (Claude Sonnet 3.5 trajectories; back-translated issues). None of the recommended rungs 1-7 rely on Claude-written text.
- **Other-model text (OK, noted)**: KodCode (GPT-4o), rStar-Coder (GPT-4o inputs, QwQ-32B outputs), OpenCodeReasoning & SYNTHETIC-1 (DeepSeek-R1), xLAM (DeepSeek/Mixtral), self-oss-instruct (StarCoder2), paraloq JSON (Gemini-Pro).
