# H11: claim check of the H9 novelty report (read-only)

Written 2026-09-28 21:12 UTC (`date -u`), by the H11 helper. Checked: `artifacts/claude-dir-h9-novelty-20260928/REPORT.md` (commit 0ef6c539a),
`calibration.json`, `budget.json`, `scripts/claude_dir_h9_budget.py`. Nothing was edited except this file. No training, no GPU.
Verdict words: **CONFIRMED** (file:line), **WRONG** (what is true), **NOT FOUND**. "REPORT:n" means line n of H9's REPORT.md.
Web pages were treated as data. Recount code is quoted inline at the end (section 9); nothing else was committed.

## 0. Short answer (for Ben, plain words)

H9's numbers about our own runs are right: I recounted the loop's maze scores, stop counts and F_eq (and the plain net's F_eq) from the raw
JSON, and every weight count from the code, and found no wrong number. What I found is smaller and mostly about how sure the report sounds:

1. Two things are stated as fact that are really guesses from very little data ("seed noise is about 10 F_eq" comes from one
   design on two seeds, and the loop's own two seeds differ by only 0.29). Details in section 6.
2. Three web pages H9 could not read are readable, and they, plus a few more papers I found, show **close earlier work for R4
   (twin noisy runs plus a halting head) and R3 (feeding the net's own answer back)**. That lowers their novelty.
3. R1 and R2 are both fine as "learned, not hand-written rules", but both are shaped like grid or path tasks. R2 is the most
   hand-designed. Details in section 7.
4. Recommendation (my opinion, untested): test R1 first, with its start/goal-named features made neutral, and R2-lite second because
   it costs no extra compute. R4 should wait for the stop-training test (H12).

| item | result |
|---|---|
| 1. per-rung counts, F_eq, rounds / cap hits | CONFIRMED: 16 of 16 counts and 12 of 12 stop rows recounted from raw JSON |
| 2. no maze stop-head loss; Learner carries only `h` | CONFIRMED (`claude_fewex_bench.py:205`, `:184-206`) |
| 3. calibration arithmetic | CONFIRMED, with 3 small wording issues (3b) |
| 4. parameter counts and percents | CONFIRMED by re-run and by my own count; 2 labelling / cost-figure inconsistencies (4b) |
| 5. web citations | 40 of 42 URLs fetched and match, with 5 claims the page does not literally say (5b); 2 not fetched; new prior art found (5c) |
| 6. "shown" but only reasoned | 7 sentences listed (section 6) |
| 7. built for mazes / hand-written rule | R3, R4: no. R1: partly maze-shaped. R2: grid-shaped and hand-picked (section 7) |

## 1. Section 2 table against the raw JSON (CONFIRMED)

Source: `artifacts/claude-fewex-20260927/eq-runs/loop-s{0,1}-pre/holdout.json` (`scores[k]["9"]`), all with n = 300. Recounted by script
(section 9). "pre" is the practised loop.

| seed | counts at k = 1, 4, 16, 64, 256, 1,024, 4,096, 16,384 | sum | F_eq | report |
|---:|---|---:|---:|---|
| 0 | 1, 0, 28, 137, 256, 271, 257, 274 | 1,224 | 51.00 | matches REPORT:67 |
| 1 | 1, 0, 3, 190, 262, 236, 284, 255 | 1,231 | 51.29 | matches REPORT:68 |

Plain (practised) F_eq: seed 0 counts 2, 8, 1, 29, 124, 217, 227, 203 (sum 811, 33.79); seed 1 counts 0, 0, 0, 12, 134, 213, 223, 224
(sum 806, 33.58). Matches REPORT:67-68 and `RESULTS-EQ.md:45,49`.

Stop table (REPORT:97-104), all 12 rung-seed cells recounted; every one matches (mean rounds to one decimal, cap hits, learned minus
fixed-16 counts):

| rung | seed 0 rounds / cap / learned-fixed | seed 1 rounds / cap / learned-fixed |
|---:|---|---|
| 16 | 48.0 / 300 / 0 | 13.4 / 23 / 0 |
| 64 | 48.0 / 300 / +1 | 43.3 / 262 / +5 |
| 256 | 48.0 / 300 / +11 | 48.0 / 300 / +5 |
| 1,024 | 48.0 / 300 / +6 | 20.6 / 71 / +9 |
| 4,096 | 48.0 / 300 / +14 | 34.8 / 196 / +1 |
| 16,384 | 31.9 / 163 / +4 | 33.1 / 177 / +2 |

Also confirmed from the same JSON: seed 0 hit the 48-round cap on 300 of 300 mazes at k = 1, 4, 16, 64, 256, 1,024 and 4,096
(REPORT:37-39); seed 1 cap hits run from 23 to 300 (REPORT:39); the learned-stop gain over fixed-16 is 0 to 14 counts at every
positive rung including k = 1 and 4 (both 0). No arm gets more than 13 of 300 at k = 1 or 4 (max is 13, fresh loop seed 0 at k = 4;
`RESULTS-EQ.md:43-50`). Line cites checked and right: `RESULTS-EQ.md:19-22, 37-50, 43-49, 72, 76-86, 120-130, 196-203`.
Also right: the source checkpoints were practised for 12,000 batches of 64 (`runs/qual-*/source.json`: `source_steps` 12000,
`source_batch` 64; note the constant in the current `claude_fewex_bench.py:27` reads 6000, so the record, not that file, is the
evidence). Marks M3 to M6 copy `RACE-PASSMARKS.md:5,11` and `RACE-ADDENDUM-1.md` correctly (95% of 200 = 190; three points = 6 of 200;
+10 = 240 counts; M4 thresholds 931 / 926 = plain sum + 120).

## 2. `claude_fewex_bench.py:205` and the harness Learner (CONFIRMED)

- Line 205: `self.update(torch.stack(ces).mean())  # no maze stop-head loss`. The loss is built only from `N.ce_and_exact(self.net.read(h)[0], s, y)[0]`
  (line 204), i.e. cell cross-entropy; the stop logit `read(h)[1]` is never used in maze adaptation.
- The Learner (`class Learner` line 169; `maze_batch` lines 184-206) carries only the state `h` (lines 192, 198-206): 3 free rounds without
  gradient (line 198), 2 rounds with gradient (line 202), `h` detached each update (lines 200, 206). Optimizer state aside, nothing else is carried.
- The stop rule (`claude_fewex_bench.py:76-78`) is right as described: from the third round on (`range(2, MAX_ROUNDS)`), `q > .5` and the last
  three predictions equal.
- Plug-in contract: an optional `Learner` is allowed (`PROTOCOL.md:31`, also `ADDENDUM-4.md:9`).

## 3. `calibration.json` arithmetic (CONFIRMED; I recomputed from the raw JSON, not from the script)

| claim | recomputed seed 0 / seed 1 | verdict |
|---|---|---|
| +10 F_eq = +240 counts summed over 8 rungs (of 300) | 10% x 2,400 = 240 | CONFIRMED |
| per-rung share of F_eq (points) | 0.04, 0.00, 1.17, 5.71, 10.67, 11.29, 10.71, 11.42 / 0.04, 0.00, 0.12, 7.92, 10.92, 9.83, 11.83, 10.62 | CONFIRMED |
| curve shifted one rung left (4x fewer examples) | 62.38 / 61.88 | CONFIRMED |
| shifted two rungs | 73.79 / 72.50 | CONFIRMED |
| perfect from k = 64 up, k <= 16 unchanged | 63.71 / 62.67 | CONFIRMED |
| perfect only from k = 256 up | 56.92 / 58.08 (+5.92 / +6.79) | CONFIRMED |
| k = 64 at 235, k >= 256 perfect | 61.00 / 59.96 | CONFIRMED |
| M6 sums 1,464 / 1,471 (F_eq 61.00 / 61.29) | 1,224 + 240 / 1,231 + 240 | CONFIRMED |

3b. Small wording issues (numbers right, sentences imprecise):
- REPORT:76-77 gives "+11.38 / +10.59" for the one-rung shift. Seed 1 is +10.58 (61.875 - 51.292); 10.59 comes from subtracting the two rounded
  printed values.
- REPORT:80-81 says a winner must "lift the 64-example rung to about 235 of 300 and every rung from 256 up to nearly perfect". That is true only in
  seed 0, and only if the upper rungs are *exactly* perfect (61.00 is exactly the target, so "nearly perfect" would miss). In seed 1 the same recipe
  gives 59.96, below 61.29; seed 1 would need about 267 of 300 at k = 64.
- The shifted scenarios pad the top rung by repeating the last count (`claude_dir_h9_budget.py`, `loop[1:] + [loop[-1]]`); REPORT:70 says "a curve that only
  moves left" but not that the extension is flat.

## 4. Parameter counts (CONFIRMED)

Re-ran `python3 -B scripts/claude_dir_h9_budget.py`: exit 0, and `git status` showed `calibration.json` and `budget.json` byte-identical afterwards.
Independent count (section 9) from the layer shapes in `scripts/claude_fewex_net.py:22-63` with `VOCAB = 125` (`claude_rsn358a_envs.py:39`):

| net | count | REPORT / budget.json |
|---|---:|---|
| loop (d 256, 2 blocks, 8 heads, ln_state, halt) | 1,645,726 | matches (also `RESULTS-EQ.md:19-20`) |
| plain (d 128, 8 blocks) | 1,619,965 | matches |

| design (REPORT name) | extra | stored | % of 1,645,726 | my count |
|---|---:|---:|---:|---|
| R1 reach: LN 512 + Wq,Wk 4,096 + offset 81+1 + s,t vectors 514 + gamma 1 + Linear(4,256) 1,280 | 6,485 | 1,652,211 | 0.3941% | CONFIRMED |
| R2 soft-D4: 15 orbits (a <= b over 0..4) x 8 heads x 2 blocks | 240 | 1,645,966 | 0.0146% | CONFIRMED |
| R3 echo gain | 1 | 1,645,727 | 0.0001% | CONFIRMED |
| R4 kappa | 1 | 1,645,727 | 0.0001% | CONFIRMED |

Bands: 1% = 1,629,269 to 1,662,183; 2% = 1,612,811 to 1,678,641. Both right.
Cost figures in REPORT:230-231 and :344 (labelled arithmetic): 10 products of 81 x 81 = 5.31M multiply-adds against 127.4M for the two blocks
(linear layers only) = 4.17%; at 11 x 11, 17.7M / 190.3M = 9.31%; at 30 x 30, 7.29 billion; R3 output head about 2.03% of block cost. All CONFIRMED.

4b. Two inconsistencies to fix (no number is wrong):
- `budget.json` numbers its designs "1 refill loop, 2 twin-stream, 3 reach channel, 4 soft-D4". The report's R1 to R4 are reach, soft-D4, refill, twin.
  A reader matching by number gets the wrong design.
- R1's cost is "about +4%" at REPORT:231 (correct: 4.17%) but "about +5%" at REPORT:237 and "~5% at 9x9" at REPORT:441.
- REPORT:6 says the script reproduces "every number in sections 2 and 5 labelled arithmetic". It reproduces the F_eq calibration and weight budgets only;
  the stop table and the multiply-add costs are not in it (I recomputed them above).

## 5. Web citations

42 URLs appear in REPORT.md. All were fetched with curl (arXiv answered 200 for me; H9 reported a proxy 403 on arXiv, which did not happen here).
Fetched pages were converted to text and searched. 40 pages returned content; details:

5a. Numbers and statements CONFIRMED on the page:
- TRM 2510.04871 (full text, arxiv.org/html): 2 layers, 7M params, y and z, n = 6 / T = 3 (line 570 of the text), BCE halting on reaching the correct
  solution, EMA 0.999, 8 dihedral transforms for Maze-Hard, Sudoku-Extreme 87.4%, Maze-Hard 85.3%, ARC-AGI-1 44.6%. Table 1: no EMA 79.9% (-7.5), 1-step gradient
  56.5% (-30.9), separate networks 82.4% (-5.0). HRM 27M and 40.3% ARC-AGI-1 (HRM paper, TRM paper line 324).
- ARC Prize HRM analysis: +13 points from 1 to 2 loops; hierarchy about 5 points ("~5pp") over a regular transformer; 300 augmentations near max;
  puzzle-id embeddings only work on ids seen in training. ("Argues against a task-register design here", REPORT:149, is the author's inference, not the page's.)
- Recursive Stem Model 2603.15641 (PDF): detached history, loss on final step, 97.5% Sudoku-Extreme, about 80% on 30x30 maze, tested to about 20,000 iterations.
- PABEE, LoopFormer, Looped-MoE, Mixture-of-Recursions, Huginn (3.5B; prelude / recurrent block / coda found in the full text), 2502.17416 (proves T loops simulate T CoT steps),
  path independence, recall networks, TTT (53.0% ARC, +7.3 points BBH), CompressARC (76K params, 20%, equivariant to permutations, colours, rotations, flips), IRED,
  MGDM/discrete diffusion 2410.14157 (91.5 vs 45.8 Countdown; 100 vs 20.7 Sudoku; absorbing-mask noise by default), Analog Bits (mechanism not in abstract,
  as H9 says), task diversity 2306.15063 (threshold between 2^14 and 2^15 tasks, linear regression), log depth 2402.09268 (full text has "Application: connectivity
  with log-depth transformers"), graph connectivity 2510.19753 (first author Qilin Ye; L layers solve diameter <= 3^L via matrix powering by repeated squaring; heuristic
  learned when training graphs exceed capacity), APPNP, residual pathway priors 2112.01388, self-consistency, RevThink, DreamCoder, HM-RNN. Titles and authors match what the report names.
- Cavanagh et al. 2011 (nn.2925): STN as a brake during decision conflict, raising the decision threshold (page now fetched; H9 had only the title).

5b. Statements the page does **not** literally say (true or plausible, but tag "F" overstates):
- REPORT:208-210 and :125 "the successor representation is the discounted sum of transition-matrix powers, and place cells encode expected discounted occupancy
  (Stachenfeld 2017; F)". The nature.com page is a paywalled preview: the abstract says only "predictive representation". "Successor representation" appears
  only in the reference list. The claim is standard in the literature but was not visible on the fetched page (memory-supported, so tag M).
- REPORT:126 "proposed to assign credit to actions" (Foster and Wilson 2006). Abstract (also paywalled): "suggestive of a role in the evaluation of event sequences in
  the manner of reinforcement learning models". A paraphrase, not the wording.
- REPORT:152 PonderNet "learned halting probability per step". The abstract says the model "learns end-to-end the number of computational steps"; the per-step halting probability is not on the page (H9 does flag "mechanism not fetched").
- REPORT:166 "Looped diffusion LMs, arXiv 2605.26106 ... on Sudoku and Countdown". That page (LoopMDM) mentions Sudoku (8 hits) and Countdown 0 times. Countdown is in the
  recursive-masked-diffusion review page (2606.18022), so the sentence mixes the two papers.
- REPORT:162 LPN "trained leave-one-out over many tasks". The phrase "leave-one-out" is not on the page; the mechanism is (text line 160: the pair being reconstructed is not used to infer the latent).

5c. Pages H9 called unread ([U]) that are readable, and **new prior art** found (abstract level; I read abstracts, not full papers):
- arXiv 2609.22197 = "Dissecting Hierarchical Reasoning Models: A Mechanistic Study" (single-state recurrent transformers comparable to HRM). No effect on R1 to R4.
- arXiv 2511.16886 = "Deep Improvement Supervision" (a target per loop, "eliminates halting mechanisms", 24% ARC-1 with 0.8M weights). Relevant to the stop-training question (H12).
- emergentmind 2605.19943 = **"Probabilistic Tiny Recursive Model"** (Sghaier, Parviz, Jolicoeur-Martineau, May 2026): injects Gaussian noise at each recursion step, runs K parallel
  trajectories from the same weights, and picks among them with the model's existing Q (stop) head. This is very close to R4's "same weights, two streams from different noisy starts, use the stop head".
  What the page does *not* say (and R4 does): disagreement between streams fed into the stop head, or learning that in training. The page notes Q-driven inference-time halting is untested there.
- Found by my own two web searches (abstracts fetched, not read further): "Speed is Confidence" 2601.19085 (K = 4 parallel latent states, halt-first selection; 97% Sudoku-Extreme);
  "Boosting Inference with Guided Reasoning" 2605.25230 (stochastic perturbations of the recursion reweighted online by the early-stopping head); GRAM 2605.19376 (multi-trajectory recursive
  reasoning); "Fixed-Point Reasoners" 2606.18206 (fixed-point convergence as the halting rule, tested on Sudoku, Maze); "Steering Recurrent Reasoners at Inference Time with Readout Feedback"
  2608.24136 (feeds the model's own intermediate readout probabilities back into the latent dynamics on Sudoku and Maze, at test time). The last is a close relative of R3's echo.
  Effect: R4's twin noisy streams and R3's readout echo both have direct precedents (mostly test-time in those papers; R3 and R4 would train them in). H9's novelty scores (R4 0.5, R3 0.3) look too high for R4;
  what is left of R4 is "disagreement as an input to a learned stop", not the twin streams. I found nothing that matches R1's exact combination in one more search, which is weak evidence only.
  These papers were not in H9's report; whether they cover the "conflict gates the stop" piece was not checked beyond abstracts.
- Also seen only as titles in the PTRM page's related list, not read: "Tiny Recursive Models on ARC-AGI-1: Inductive Biases, Identity Conditioning, and Test-Time Compute", "Test-time Recursive Thinking", "Tiny Recursive Reasoning with Mamba-2 Attention Hybrid".

5d. Not fetched:
- annualreviews.org Miller and Cohen 2001: HTTP 403 (bot wall). Not checked.
- pubmed.ncbi.nlm.nih.gov/16945502 (Frank 2006): a "Just a moment ... enable cookies" page, no article text. Not checked. (Europe PMC as a side route returned 503; I did not try to get around it.)
- PubMed 16474382 (Foster and Wilson): named in REPORT:551 without a full URL; not fetched. The nature.com page for that paper was fetched instead (abstract only).
- The two nature.com pages (nn.4650, nature04587) are paywalled previews, abstract only.
- "Baddeley-style capacity" (REPORT:129) and "silicon builds symmetry in" (REPORT:133) are memory claims, no URL; not checkable.

## 6. Sentences that say "shown" (or "verified") for something only reasoned or under-supported

REPORT:31-32 promises that "the facts are *shown* in section 2". These are not shown, or only under an assumption:

1. REPORT:32-33 "F_eq +10 is a big ask: about 4 times fewer examples at every rung." Shown: +10 = +240 counts, and one uniform left shift gives +10.6 to +11.4. Not shown: that "4x fewer
   examples" is the right reading. It assumes the curve slides left and the last rung repeats; H9's own "perfect from k = 64 up" case gives +11.4 to +12.7 with no shift at all.
2. REPORT:41-43 and :111-112 "Seed noise is about 10 F_eq." Shown: the sparse loop's gap to the loop was +3.88 in seed 0 and -6.25 in seed 1 (`artifacts/claude-sparse-20260928/RESULTS.md:9-14,43`; its F_eq
   was 54.88 and 45.04). That is one design on two seeds. The baseline arms' own seed spread is tiny: loop 51.00 vs 51.29 (0.29), plain 33.79 vs 33.58 (0.21). Two seeds cannot give a noise size, and
   this spread is a property of the sparse design, not measured seed noise. The chances in REPORT:448-449 ("even a true +10 average has roughly even odds of missing the both-seeds mark") rest on it.
3. REPORT:208-210 "Verified: the successor representation is the discounted sum of transition-matrix powers" (F). Not on the fetched page (5b). Correct as general knowledge; not verified here.
4. REPORT:217-221 (labelled suggested): "the base loop must grow that chain a hop at a time (its narrow heads see a 3-column strip, `claude_fewex_net.py:42-45`)". The cited lines make only the first 4 of 8 heads
   narrow (`narrow[: self.h // 2] = True`, line 44); the other 4 heads attend to every cell with a relative position bias (clipped at 4). So the cited code does not show a hop-at-a-time limit.
5. REPORT:374-376 "Not found in these sources: cross-stream disagreement fed to the stop head." True of the pages H9 read, but three pages were unread and PTRM, Speed is Confidence, Boosting Inference and GRAM were missed (5c).
   The novelty scores built on it (REPORT:376-377, ranking table) are stale.
6. REPORT:16-19 "none is built for mazes, and none tells the net what kind of puzzle it is looking at" and :228 "Nothing mentions walls, routes, mazes or grid size." A design judgement, not a
   measurement; see section 7 (R1's features are named start and goal; R2 is a grid symmetry).
7. REPORT:40 "R4 targets Ben's own stop rule". The rule (own thinking time) is in `handoff/director-roadmap.md:10` and the H9 brief, not on `ben-goals-2026-09-26.md` (no hit for "thinking time" there). It is the Director's wording of Ben's rule.

Fine as labelled: every "guess", "suggested" and "untested" in sections 5 to 7 is honest about being a guess; the ranking arithmetic (0.6 x 20 = 12, 0.4 x 30 = 12, 0.3 x 25 = 7.5, 0.5 x 3 = 1.5) is right.
Not checkable from the files: "about seventy search and fetch calls" (REPORT:508).

## 7. Judged against the goals page (`design/v3/30-modes/ben-goals-2026-09-26.md`) and Ben's "not built for mazes" rule

The goals page forbids new work on hand-written question parsing, hand-written reasoners, templates and rule-based routing ("No new work on hand-written rules"), and wants a *learned* reasoner
that carries skill to other kinds. "Ben rejects anything built for mazes" is in the H9 brief, not on the goals page.

| design | hand-written rule? | built for mazes? | reading |
|---|---|---|---|
| R1 reach | No rule; a hand-designed *computation* (closure by repeated squaring) with learned link map and learned markers | **Partly.** No maze word, but its four outputs are "reached from start-like cells", "reaches goal-like cells", "lies between", "reaches total" (REPORT:204-206): route-finding between two marked cells. Mazes have exactly a start and a goal; sums and grids do not. | Fails the spirit of the rule unless the start/goal-named features are made neutral (e.g. reach from learned query vectors) and the design is shown on a second kind. Needs a second held-out kind (roadmap item 3) to support "general". |
| R2 soft-D4 | A hand-picked symmetry prior (rotate/flip invariance), eps = 0.3 fixed | Grid-specific, not maze-specific; H9 flags it as "the most hand-designed of the four" (REPORT:288-289). A word question has no 2-D grid, so it does nothing for the goals page's later "ordinary word questions". | Highest hand-design; smallest fit with "everything". Cheap to run. Bundles two edits (table and mask), acknowledged at REPORT:296-298. |
| R3 refill | No | No | Clean under the rules, low novelty (precedent: RoFB, TRM's y, self-conditioning). |
| R4 twin stop | No | No | Clean under the rules, fits "decides its own thinking time", but its twin streams have direct precedent (5c) and it cannot move F_eq +10 (H9's own point, REPORT:381-383). |

## 8. My verdict (one paragraph; my opinion, untested)

I would test **R1 first, after one edit before any run**: replace the "start-like" and "goal-like" scores and the "lies between" product with neutral learned probe vectors (still one small change, still about 6.5K weights),
because as written the four outputs are a route-finder's vocabulary, which is what Ben rejects, and because R1 is the only one of the four that can plausibly raise the plateau (the loop still misses 5 to 15% of 9x9 mazes at every k >= 256: 236 to 284 of 300 right, where
sample count is no longer the obvious limit) as well as the low rungs. **R2-lite (table only, no mask change) second**: it adds no compute, its credit check (row/column swap gap) is cheap and informative, and it would tell us how much of the gap is orientation.
R3 and R4 should wait: R3 has the weakest novelty, and R4 is really a stop-head question that H12 (stop-training test) is set up to answer first. Two cautions. H9's chances (20 to 30% for R1 and R2) are unanchored guesses, and the only sealed comparison
so far (the sparse loop) came out +3.88 and -6.25 against a +10 bar, so treat a both-seeds +10 as a long shot for any design. And every design here is judged only on mazes; the goals page's main measure is carry-over to a kind never practised, which this ruler cannot show until
the two-more-kinds ruler (H1) exists.

## 9. How I checked, and what I did not do

Recount (Python, standard library; reads the raw JSON, does not import H9's script):

```python
import json
R=[1,4,16,64,256,1024,4096,16384]
for s in (0,1):
    d=json.load(open(f'artifacts/claude-fewex-20260927/eq-runs/loop-s{s}-pre/holdout.json'))
    c=[d['scores'][str(k)]['9']['right'] for k in R]          # counts of 300
    print(s, c, sum(c), round(100*sum(c)/2400,2))
    for k in R: x=d['scores'][str(k)]['9']; print(k, x['right']-x['fixed_right'], x['cap_hits'], round(x['mean_rounds'],1))
```

Parameter count (from `claude_fewex_net.py:22-63`): `lin(i,o)=i*o+o`; block = 2 LN + qkv + out + two MLP layers + `2*heads*9`; net = tok(125*d) + slot(2*d) + blocks + ln_out + head(d*125+125) (+ ln_state + halt for the loop).
Output: loop 1,645,726; plain 1,619,965; R1 +6,485; R2 +240 (15 orbits x 8 heads x 2 blocks).

Not done: no model run (no torch here); I did not open readpanel320 or any checkpoint; I read `holdout.json` score files only, as the brief asked. Full-text checking used the arXiv HTML or PDF versions where they exist; for the three
paywalled or blocked sources I say so above. I installed `pypdf` in a throwaway virtual environment outside the repo to read PDFs; nothing of it is committed. Fetched abstracts are what the arXiv abstract page says, not a review of the papers' methods.
