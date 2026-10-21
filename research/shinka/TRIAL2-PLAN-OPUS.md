# Trial 2 plan: ideas first, then code (Claude API ceiling $100)

Written 2026-10-21 by an Opus design session. Design only: no API spend, no Shinka run, no GPU. Ben's instruction: $100 is a **ceiling, not a target**; use the tokens as well as possible to get a genuinely new and useful idea.

Inputs read: `CARD.md` (sealed trial 1 card, PR #90), `results/evo1/REPORT.md`, `results/noise/`, `NEXT.md`, `KNOWN.md`, `task/initial.py`, `task/toy.py`, funding-ledger rows (2026-10-20 00:16, 03:37, 04:22; 2026-10-21 01:55, 02:00, 02:05), `design/06-premonition-mini-spec.md`. The Sonnet draft (`claude/shinka-trial2-plan`, `TRIAL2-PLAN.md`) does **not exist on the remote** (checked with `git ls-remote`), so this plan is written from scratch and replaces it.

Labels: **shown** = measured or read in the repo; **suggested** = inferred, not tested; **untested** = not checked.

## 0. The answer in one paragraph

Trial 1 evolved *code* and checked novelty at the end; every finalist was the same known idea in new code (shown). Trial 2 makes **one change**: novelty is checked on the **idea, in words, against the literature, before any code is written**. Many diverse ideators write short idea cards; a web-searching "prosecutor" tries to prove each one already exists; only ideas that survive get implemented and scored on the same CPU toy, against the best *known* writer given the same tuning effort. Every stage has its own dollar cap and a sealed stop rule. **Expected spend ≈ $27, hard stop $45** for the whole trial (suggested estimates, section 5). The other $55 stays unspent unless Ben reopens it.

## 1. What trial 1 teaches (facts the plan rests on)

| fact | label | source |
|---|---|---|
| Trial 1 failed its card: 0 winners; best 6a-1 0.715/0.740 vs multi-head 0.743/0.740 on fresh seeds | shown | REPORT.md |
| All 6 finalists share one idea (deflation pursuit = matching pursuit on attention), present from generation 1 | shown | REPORT.md |
| Code-similarity rejection fired 0 times in 15 proposals | shown | REPORT.md |
| Opus mutation ≈ $0.087/call; Opus judge ≈ $0.21/finalist (≤2 searches); Haiku ≈ $0.0015/call; Sonnet ≈ $0.017/call | shown | NEXT.md, ledger |
| Prices now: Opus 5.5 $4/$20 per M tokens in/out, Sonnet 5.5 $2/$10, Haiku 5.5 $0.10/$0.50; cache reads $0.20/M (Opus, Sonnet); Batch API −50% | shown (bundled API reference, cached 2026-10-06) | claude-api skill |
| Web-search fee per search | **untested** here; assumed $10 per 1,000 searches. The trial-1 judge cost ($0.21 with ≤2 searches) is the better anchor, because search-result tokens dominate | — |
| The headroom is on **novel names only**: multi-head familiar 0.982 (ceiling), novel 0.565 vs oracle 0.945 | shown | noise SUMMARY |
| Multi-head novel-name accuracy is noisy across seeds: 0.590, 0.523, 0.625, 0.518, 0.570 (sd ≈ 0.045) | shown (computed from `results/noise/multihead_pool_10x.txt`) | — |
| The writer is a per-line function: lines are shuffled across visits on every call, and changing 16 lines must leave the other cards unchanged. It sees reader states only, no token ids | shown | CARD.md §2 |
| 6a-1 was in effect "a tuned known method"; the multi-head reference was never tuned | suggested | REPORT.md, `task/references.py` |

Consequences for the design (suggested):
1. Novelty must be judged on the **core operation in words**, not on code.
2. The comparison that matters is **new idea vs best known idea with equal tuning**, on novel names, over more fresh seeds than 2 (noise sd 0.045 per seed).
3. Spend should go where trial 1 was blind: wide ideation and adversarial prior-art search are cheap per idea; code evaluation is free (CPU) but slow.

## 2. The one change, and what stays fixed

**Changed (the hypothesis under test):** ideation in words + prior-art gate **before** code, replacing code evolution with an end-of-run judge.

**Kept exactly as trial 1 (shown in `task/`):** the toy, the frozen reader, the isolated child-process scorer and its checks, the static AST check, the 20,000-parameter cap, evolution seeds 0/1/2, KNOWN.md including its §C rule ("a direct combination of two known items is known"), hand-reading of finalist code.

**Not hypotheses, just settings** (stated so nobody reads them as a second change):
- model choice per role (cost knob);
- the pass bar is "beat the best known writer", which trial 1 already reported and NEXT.md proposed making required;
- new fresh seeds 2001–2006 (1001/1002 have been seen).

**Small card experiments and the village model stay separate.** Everything here runs on the CPU toy under `research/shinka/`. Nothing under `premonition/` is touched. A toy winner becomes a *candidate* for PremonitionMini D (d_model 128, card writer 25,089 params, spec §1) only through a separate pre-registered run with its own approval (section 8).

## 3. Model per role (and why)

| role | model | why | tricks |
|---|---|---|---|
| ideators (hard, creative) | Opus 5.5 effort high **and** Sonnet 5.5 effort high, half each | two model families give more spread than one (suggested); Opus for depth | 1-hour cached context pack (~12k tokens); **Batch API** (−50%), ideation is not urgent |
| dedup/cluster of idea cards | Opus 5.5, one call per wave | one global view of ~200 one-line cores; cheap at 1 call | — |
| quick screen (fits interface? names a KNOWN item outright?) | Haiku 5.5 | high volume, simple yes/no | batch + cache |
| prior-art **prosecutor** (web search) | Sonnet 5.5 + `web_search` (max 6 searches) | most tokens are search results; Sonnet input is half Opus's price | not batched (untested with server tools) |
| prior-art **judge** (rules on the prosecution file, no search) | Opus 5.5 effort high | the verdict is the expensive mistake; Opus's job is reading, not searching | cache KNOWN.md |
| implementer (idea card → `CardWriter`) | Sonnet 5.5 | code from a precise spec; up to 3 fix attempts with the scorer's error text | cached interface + initial.py |
| fidelity check (does the code do the card's core operation, and nothing else new?) | Opus 5.5 effort medium | stops "the code drifted to a known trick" | — |
| refinement steps | Sonnet 5.5; Haiku "family lock" check on each child | keeps the core operation; avoids trial 1's drift | — |
| final novelty judge on finalist code | Opus 5.5 + web search, as trial 1 | same instrument as trial 1, so the results compare | budget reserved in advance |

Opus runs at effort high for ideation and judging; medium elsewhere (Opus 5.5's default is medium, so it must be set explicitly; shown in the API reference).

## 4. Stages, gates and caps

Every paid call goes through `ledger.py` into a new `results/TRIAL2_LEDGER.jsonl`. Each stage has a **cap** (a call is refused if its worst case could pass the cap) and a **gate** written below and sealed in `CARD2.md` before Stage 1. A failed gate ends the trial: nothing after it is spent.

### Stage 0 — build and seal ($0 API, CPU only; plumbing test ≤ $0.50)
- A Sonnet worker session writes the scripts: `ideate.py`, `screen.py`, `prosecute.py`, `implement.py`, `refine.py`, reusing `ledger.py`, `task/evaluate.py`, `confirm.py`, `novelty_judge.py`.
- The **context pack** (cached prefix, ~12k tokens): the toy and interface in plain words; the per-line constraint; the error table (multi-head sends 43% of novel-name questions to another person's card, mean over seeds 100–104, shown); KNOWN_SHORT + KNOWN §C; the 6 trial-1 finalists described in one line each and why they were judged known. **No scores of any candidate idea are ever shown to a judge.**
- CPU: noise for multi-head on seeds 2001–2006 is **not** run (they are fresh); instead run the baseline and multi-head on noise seeds 105–109 to tighten the sd estimate (≈ 5 min CPU).
- CPU, $0: the per-line person-position probe from risk 2 (section 7). If it is near chance on novel-name lines, report to the coordinator before any spend.
- Seal `CARD2.md` (pass card, section 6) and get the coordinator's GO.

### Stage 1 — ideation in words (cap **$8**; expected ≈ $5)
- 12 **lenses**, each a different starting point. Suggested: hippocampal indexing/pattern separation; linguistics (argument structure, which slot is the agent); information theory (what is cheapest to transmit about a line); error-correcting codes; immune-system recognition of the never-seen; signal processing (onset/contrast detectors); databases (how a key is formed when the key value is unseen); physics (symmetry breaking, conserved quantities); evolution/ecology; cryptography (keyed permutations); compilers (type inference for an unseen identifier); "inversion" (list precisely what multi-head pooling cannot do for an unseen name, then design for that).
- 24 calls = 12 lenses × {Opus, Sonnet}; each returns **5 idea cards** as JSON:
  `core_operation` (one sentence), `mechanism` (≤150 words), `why_novel_names` (why it helps an unseen person token specifically), `nearest_known` (KNOWN item or paper, and the exact difference), `prediction` (a number it should move on the toy, e.g. person-lost errors on novel names), `fits_interface` (per-line, no token ids, ≤20k params).
- ≈ 120 cards. Cost (suggested): Opus ~12k cached in + ~8k out ≈ $0.16/call, Sonnet ≈ $0.08/call; Batch halves both → ≈ $1.5 + cache writes ≈ $2–3. A second **"far" pass** reruns the 6 lenses with the most unique cores, told the cores already found and asked for something unlike all of them (12 calls, ≈ $1.5).
- **Gate G1:** ≥ 60 parseable cards that state `fits_interface: yes`. Else stop (the pipeline is broken; fix at $0 and re-GO).

### Stage 2 — dedup, screen, and calibrate the gate (cap **$4**; expected ≈ $2.5)
- One Opus call clusters all `core_operation` sentences into families (≈ $0.30). Keep one representative per family (the most specific card).
- Haiku screens each representative: implementable as a per-line writer? names a KNOWN item outright or a §C combination? (≈ $0.002 each.)
- **Gate calibration (before any verdict counts).** 6 **planted** cards go through Stages 3a+3b blind, mixed in with the real ones: 5 known methods paraphrased in fresh words (OTKE/optimal-transport pooling, matching-pursuit deflation, slot attention, tensor-product binding, NetVLAD) and 1 deliberately trivial "new" card (a temperature schedule on the pool). ≈ $2.
- **Gate G2:** ≥ 15 distinct families pass the screen. Else stop (ideation does not reach outside known territory).

### Stage 3 — adversarial prior-art search (cap **$16**; expected ≈ $10)
- **3a prosecutor** (Sonnet + up to 6 web searches per family, cap 30 families + 6 planted): instructed to *find* the closest published or project method and argue the card is known; returns citations and a one-paragraph case. ≈ $0.25–0.35 each (suggested from trial 1's $0.21 at 2 Opus searches, scaled to Sonnet price and 6 searches) → ≈ $9–12.
- **3b judge** (Opus, no search, reads the card + the prosecution file + KNOWN.md): `KNOWN: X` / `NOT FOUND: closest is Y`, a confidence, and a 1–5 **plausibility** score for "should help unseen-name binding on this toy", written before any code exists. ≈ $0.12 each → ≈ $4. Anything that is not a clean verdict counts as KNOWN (as in trial 1).
- **Gate G3a (calibration):** the planted known cards are called KNOWN in ≥ 4 of 5. If not, the gate is too lenient: STOP, report, $0 more (the gate cannot be trusted, so neither can anything downstream).
- **Gate G3b (novelty):** ≥ 1 real family NOT FOUND. If 0: **STOP**. This is the main "no money after a failed novelty check" rule. Spent at that point ≈ $12–20.
- The ranking for Stage 4 is frozen here: NOT FOUND families by judge plausibility, then confidence. Max 8 go forward.

### Stage 4 — implement and score once (cap **$6**; expected ≈ $4; CPU ~1 h)
- Sonnet implements each card (≤ 3 attempts using the scorer's error text; ≈ $0.10–0.30 per card).
- Opus fidelity check (≈ $0.08): does the code do the card's core operation, with no extra known trick bolted on (e.g. multi-head pooling)? A fail gets one re-implementation, then the card is dropped.
- Scored on evolution seeds 0/1/2 with the unchanged `task/evaluate.py` (≈ 3 min each on 4 CPUs).
- **Known control, same effort (CPU + ≈ $1.5):** the multi-head pool also gets one "implementation round": Sonnet writes up to 3 tuned variants **restricted to KNOWN items** (more heads, two-pool + multi-head, role-specific projections). The best becomes **BEST-KNOWN** for every later comparison.
- **Gate G4:** at least one novel family has evolution-seed novel-name accuracy ≥ BEST-KNOWN − 0.05. Else STOP: the new ideas are new but not useful at first try (spent ≈ $20–25).

### Stage 5 — refine inside the family (cap **$8**; expected ≈ $4; CPU ~3–4 h)
- The top ≤ 3 families from G4 each get **15 refinement steps** (Sonnet; tells it the core operation must stay). Each child is first checked by Haiku: "same core operation as the parent card?" A drift is rejected without scoring. An Opus "what has not been tried within this family" note every 5 steps.
- **Equal effort for BEST-KNOWN:** 15 steps of the same loop, restricted to KNOWN items. This is the fairness rule trial 1 lacked (suggested: 6a-1 was mostly tuning).
- A plain loop around `task/evaluate.py` is enough (suggested); ShinkaEvolve is not needed for 15 steps on a fixed family, and its code-novelty rejection is what failed. If the coordinator prefers Shinka, its islands are seeded with the family's Stage 4 program and the Haiku family lock becomes its novelty call.
- Finalists: the best program of each family by evolution score (≤ 3), plus BEST-KNOWN.
- **Gate G5:** a finalist beats BEST-KNOWN on evolution-seed novel-name accuracy by ≥ 0.03. Else STOP before the final judge (no judge money on a non-winner).

### Stage 6 — confirm, then judge (cap **$3**; expected ≈ $1.5)
- `confirm.py` on **6 fresh seeds 2001–2006** (CPU only, ≈ 20 min), finalists vs BEST-KNOWN vs multi-head vs baseline, paired by seed.
- The final novelty judge (trial 1's `novelty_judge.py`, Opus + web search, sees code but no scores) runs **only on finalists that pass the fresh-seed marks**: up to 3 × ≈ $0.6 worst case, reserved before Stage 5.
- Hand-read for sandbox evasion (as trial 1).

### Whole-trial stop
- **$45 hard stop** across all stages (sum of caps; suggested), **$40 warning**, both far under Ben's $100 ceiling.
- Plumbing tests count against Stage 0's $0.50.
- No stage borrows unspent money from another; a stage's leftover is simply not spent.

## 5. Dollar tally (estimates, suggested)

| stage | expected | cap | stops here if |
|---|---|---|---|
| 0 build + plumbing | 0.3 | 0.5 | — |
| 1 ideation (36 calls, batch + cache) | 4.5 | 8 | G1 fails |
| 2 cluster, screen, plant | 2.5 | 4 | G2 fails |
| 3 prosecutor + judge (~36 files) | 10 | 16 | G3a or G3b fails (spent ≈ $12–20) |
| 4 implement + known control | 4 | 6 | G4 fails |
| 5 refine (3 families + known, 15 steps each) | 4 | 8 | G5 fails |
| 6 final judge | 1.5 | 3 | — |
| **total** | **≈ 27** | **45** | |

Why not spend closer to $100 (suggested): the measurements that decide the trial are G3 (novelty) and G4 (usefulness). Money beyond ~$30 buys more ideas past a gate that already failed or more tuning past a gate that already passed; neither changes the answer much. If G3b and G4 pass but G5 fails narrowly, the reasonable next step is a **new** card with more refinement steps, approved separately, not quiet spending of the remainder.

## 6. Sealed pass card (to copy into `CARD2.md` before Stage 1)

Paired by seed on fresh seeds 2001–2006, BEST-KNOWN = the best of {multi-head pool, its Stage 4 and Stage 5 known-only tunings} by evolution score.

**WINNER** needs all of:
1. **NOT KNOWN twice:** NOT FOUND from the Stage 3 judge on the idea card **and** from the Stage 6 judge on the finalist code. My own check of the reasoning against KNOWN.md must agree; if I disagree, it counts as known.
2. **Useful on the gap:** mean over the 6 seeds of (finalist − BEST-KNOWN) novel-name accuracy **≥ +0.05**, and positive on **≥ 5 of 6** seeds. (Per-seed sd of multi-head novel accuracy ≈ 0.045, shown; the mean of 6 paired differences should have sd well under 0.02, suggested. The 5-of-6 rule guards against one lucky seed.)
3. **No hidden cost:** mean familiar-name accuracy no more than 0.02 below BEST-KNOWN; within the 20,000 parameter cap; passes every scorer check.
4. Fidelity: the finalist code still does its card's core operation (Opus fidelity check, plus my hand-read).

Reported in four groups as in trial 1: both / better-but-known / novel-but-not-better / neither.

**What would prove the approach wrong** (any one):
- **G3b fails** (0 NOT FOUND families from ~30): with this budget, LLM ideation does not reach outside the known literature on this problem. Also wrong if the post-hoc audit (below) shows the gate is leaky.
- **G4 fails:** novel ideas exist but none comes within 0.05 of BEST-KNOWN: "new" and "useful" do not meet here.
- **Fresh seeds fail after G5 passed:** the gain was tuning to seeds 0–2.
- **Leak audit:** after the trial, a second prosecutor (Opus, fresh search, never sees the first file) re-checks every NOT FOUND family. If it finds clear prior art for **more than half**, the Stage 3 gate is shown leaky and any WINNER is downgraded to "unconfirmed novelty". Cost ≈ $0.5 per family, inside Stage 6's cap only if a WINNER exists; otherwise ≈ $2, inside the $45 stop.

## 7. Biggest risks (labelled)

1. **§C makes "new" almost unreachable** (suggested). "A direct combination of two known items is known" kills most real research ideas, which are recombinations. G3b could fail for that reason alone. I keep §C (changing it would be a bar change, which needs Ben), but the report must say which cards died to §C alone.
2. **The toy's headroom may not be reachable by a per-line writer** (untested). The oracle reaches 0.945 because it is *told* the roles; a writer that sees one line of frozen-random-reader states with a never-trained name token may have a much lower true ceiling. A cheap $0 diagnostic before Stage 1 would bound this: a per-line linear probe for "which position is the person" on novel-name lines. If the probe is near chance, the trial is aimed at the wrong place, and I would tell the coordinator before spending.
3. **The prior-art gate errs both ways** (untested). Web search misses obscure papers (false NOT FOUND); an over-eager prosecutor calls everything "attention pooling with a reweighting" (false KNOWN). The planted cards (G3a) and the leak audit measure this; they do not remove it.
4. **Toy → village transfer** (untested). A toy winner says nothing yet about PremonitionMini D on the ladder or the village.
5. **Cost estimates** (suggested). Web-search pricing and Sonnet search-result token volumes are not measured here; the plumbing test must measure one prosecutor call before the GO, and the Stage 3 cap is the backstop.

## 8. After a pass (not part of this trial)

A WINNER is a candidate for PremonitionMini D's `CardWriter` (spec §1: attention pool, key 128→64 + L2 norm, value 128→128). Porting it is a separate pre-registered card under `premonition/`, compared against both the current writer and a multi-head writer at matched parameters. Any GPU spend there follows the usual caps; 10M-param runs and Modal need Ben.

## 9. What Ben gets, in plain words

Last time, the AI kept writing new code for the same old trick, and we only found out it was old at the end. This time it works like a science fair with a strict librarian:
1. About 36 AI "inventors", each told to think like a different field (brain science, codes, immune systems, …), write about 180 short idea cards in plain words. No code yet.
2. A "librarian" AI searches the web to prove each idea already exists. A second, stronger AI decides. To check the librarian is honest, we slip in five old ideas in disguise; it must catch at least four.
3. Only ideas the librarian cannot find get built and tested on the same small practice task as before. They have to beat the best *known* method, which gets the same amount of tuning, on six brand-new test runs.
4. Each step has a spending limit and a stop rule written down in advance. If no idea is new, we stop there, at roughly $12–20.

Likely total: about $27, never more than $45, out of your $100 ceiling. Possible results: a new card-writing idea that beats the best known one (a candidate to try in your real model later), or a clear "no", which tells us where AI idea search does and doesn't help.
