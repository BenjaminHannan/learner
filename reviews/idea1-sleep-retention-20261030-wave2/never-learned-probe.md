# Never-learned probe: do the hard facts fail because they were not stored, or because the new wording does not transfer?

**Verdict: TRANSFER** (reproduction exact; WRONG not triggered; UNDERFIT rejected). Measurement only: same ON-arm training as r5/wave 2, seeds 0, 1, 2, LFM3 on MPS (`lfm3_mps`, LoRA r8). `evaluate()` also asks each fact its training wording (the first string of the plan row, same "Answer with just the name." system text used in training) and logs it beside the scored paraphrase. Preregistration committed before the first baseline (commit f91f48166a, `probe/preregistration.json`). Harness: `probe/run_hf.py` (only change: the extra generation and `train_*` fields; `diff` against wave-2 `run_hf.py` is 3 changed lines). Manifest: all 33 source hashes verified (dry-run and the in-run assertion). Raw reports: `probe/raw-s0..2/`. Data: `never-learned-probe.json`.

Note on the real recipe (coordinator, checked): it generates k paraphrases plus k Q&A pairs per fact in both directions (prompts.py:47-50, recipe.py:3, recipe.py:1024). This harness uses one wording per fact, so it overstates the paraphrase failure relative to the real app.

## Pre-registered marks

| Mark | Result |
| --- | --- |
| Reproduction: scored hits and general hits per phase equal existing reports exactly | **PASS, all 3 seeds.** Held 0/1/4/4 (s0), 0/1/3/4 (s1), 0/1/3/4 (s2); general 6/7/5/6, 6/7/6/6, 6/7/4/4. HARM unchanged. |
| TRANSFER: at the own-block checkpoint >=2 of 3 hard facts right under training wording, wrong under scored wording, in >=2 of 3 seeds | **PASS: 3 of 3 hard facts in 3 of 3 seeds** (Copperfern and Sunwillow at phase 1, Starmeadow at phase 2). |
| UNDERFIT: >=2 of 3 hard facts wrong under training wording in >=2 of 3 seeds | **Not met: 0 of 3 facts wrong in all seeds.** |
| WRONG: Starmeadow also wrong under its training wording at phase 2 | **Not triggered:** right in 3 of 3 seeds. |

## Per fact x seed (T = training wording, S = scored paraphrase; Y = hit, n = miss, greedy 32 tokens)

Own = checkpoint after the fact's own block (1 for Copperfern/Sunwillow/Moonhaven, 2 for the block-2 facts). Final = after block 3.

| Fact | Seed | Own | At own checkpoint | At final (phase 3) |
| --- | --- | --- | --- | --- |
| Copperfern | 0 | 1 | T:'Copperfern'Y / S:'Copper'n | T:'Copperfern'Y / S:'Copper'n |
| Copperfern | 1 | 1 | T:'Copperfern'Y / S:'Moon'n | T:'Copperfern'Y / S:'Copper'n |
| Copperfern | 2 | 1 | T:'Copperfern'Y / S:'Copper'n | T:'Copperfern'Y / S:'Copper'n |
| Sunwillow | 0 | 1 | T:'Sunwillow'Y / S:'Sunrise'n | T:'Sunwillow'Y / S:'Sunwillow'Y |
| Sunwillow | 1 | 1 | T:'Sunwillow'Y / S:'Sunrise'n | T:'Sunwillow'Y / S:'Sunwillow'Y |
| Sunwillow | 2 | 1 | T:'Sunwillow'Y / S:'Sunrise'n | T:'Sunwillow'Y / S:'Sunwillow'Y |
| Starmeadow | 0 | 2 | T:'Starmeadow'Y / S:'Sunroom'n | T:'Starmeadow'Y / S:'Moonlight'n |
| Starmeadow | 1 | 2 | T:'Starmeadow'Y / S:'Sunroom'n | T:'Starmeadow'Y / S:'Moonlight'n |
| Starmeadow | 2 | 2 | T:'Starmeadow'Y / S:'Sunroom'n | T:'Starmeadow'Y / S:'Moonlight'n |
| Moonhaven | 0 | 1 | T:'Moonhaven'Y / S:'Moonhaven'Y | T:'Moonhaven'Y / S:'Moonhaven'Y |
| Moonhaven | 1 | 1 | T:'Moonhaven'Y / S:'Moonhaven'Y | T:'Moonhaven'Y / S:'Moonhaven'Y |
| Moonhaven | 2 | 1 | T:'Copperhaven'n / S:'Moonhaven'Y | T:'Moonhaven'Y / S:'Moonhaven'Y |
| Mistbrook | 0 | 2 | T:'Mistbrook'Y / S:'Mistbrook'Y | T:'Mistbrook'Y / S:'Mistbrook'Y |
| Mistbrook | 1 | 2 | T:'Mistbrook'Y / S:'Mistbrook'Y | T:'Mistbrook'Y / S:'Mistbrook'Y |
| Mistbrook | 2 | 2 | T:'Mistbrook'Y / S:'Moon'n | T:'Mistbrook'Y / S:'Mistbrook'Y |
| Pinecrest | 0 | 2 | T:'Pinecrest'Y / S:'Pinecrest'Y | T:'Pinecrest'Y / S:'Pinecrest'Y |
| Pinecrest | 1 | 2 | T:'Pinecrest'Y / S:'Pinecrest'Y | T:'Pinecrest'Y / S:'Pinecrest'Y |
| Pinecrest | 2 | 2 | T:'Pinecrest'Y / S:'Pinecrest'Y | T:'Pinecrest'Y / S:'Pinecrest'Y |

Training-wording hits of all 9 cards per phase: s0 0/3/6/8, s1 0/3/6/9, s2 0/2/6/8 (scored: 0/1/4/4, 0/1/3/4, 0/1/3/4). **Shown.**

## What the probe shows

- **Shown:** Copperfern, Sunwillow and Starmeadow are stored. Under the training wording each is right at its own checkpoint in every seed (and stays right through phase 3), while the scored wording gives "Copper"/"Moon"/"Sunrise"/"Sunroom". The earlier "never learned" label was a paraphrase-transfer failure, not a storage failure.
- **Shown:** the block-1 underfit worry (pooled loss 0.5) does not show as lost facts: Copperfern and Sunwillow are right at phase 1 under their own wording. Per-card loss was still not logged.
- **Shown:** the wording gap is not only a hard-fact effect. Under the training wording the other block-1/2 cards are also mostly right where the scored wording is wrong (e.g. Mistbrook s2 phase 2: T right, S "Moon"; Moonhaven s1 phase 2: T right, S "Mistbrook"). Training-wording hits per phase (3 / 6 / 8-9) lead scored hits (1 / 3-4 / 4) throughout. Moonhaven is the only fact whose paraphrase works from phase 1.
- **Shown:** after block 3 the ON arm answers the training wording of 8-9 of 9 cards but the scored wording of only 4 of 9 (all-9 counts, which include the 3 unscored block-3 cards).
- **Shown (new):** at phase 1, Mistbrook/Pinecrest/Starmeadow (not yet trained) answer with block-1 stems ("Moon", "Moonfire", "Sunflower") under the training wording, so name pieces leak onto untrained questions. Not the cause of the misses.
- **Suggested:** Sunwillow turns up under the scored wording at phase 2 because rehearsal adds draws that strengthen generalisation, but the fact itself was already stored at phase 1. Copperfern and Starmeadow never cross to the scored wording (suggested: rare names starting with a common-word token such as Cop/Star; untested).
- **Untested:** whether several training wordings (as the real recipe does) close the gap, and whether the gap depends on the wording style ("Name the X assigned to Y" vs "What is the fictional Y X?").

## Next single change (not run)

Train each fact on two wordings (the first string plus one other), score on a third unseen wording. Pass marks fixed now: ON arm, seeds 0-2, >=2 of the 3 hard facts right under the unseen wording at their final checkpoint in >=2 of 3 seeds (currently Sunwillow only, from phase 2), general hits no more than 2 below baseline in every run; proof it is wrong: Copperfern and Starmeadow still miss the unseen wording in all 3 seeds. Runtime about 3 runs x 3 min.

## Run facts

Wall time 162, 175, 162 s; exit 0, no watchdog or abort; min free disk 14.7 GiB; min available memory 7.3 GiB (s1), 8.8 (s2), 10.8 (s0); pressure level 1. Scratch (`/tmp/idea1-probe`, adapters, isolated home) deleted. App untouched, nothing exported or promoted.

## For Ben

- **Shown:** The three "never learned" facts WERE learned. When I asked the exact question the model was taught, it got all three right, every time (9 out of 9 tries).
- **Shown:** What fails is a question with different words. "What is the fictional Fennel garden room name?" works. "Name the room assigned to the Fennel garden." does not.
- **Shown:** This is true for the other facts too, only less. The model is better at the sentence it practised than at the idea behind it.
- **Shown:** I changed nothing about the teaching. The old scores came out exactly the same, so the new look is trustworthy.
- **Suggested:** The real app teaches every fact in several wordings, so it probably does better than this small test.
- **Untested:** Whether teaching two wordings fixes it. That is the next step.
