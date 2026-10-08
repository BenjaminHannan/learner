# Literature: fast consolidation without forgetting (10-08, five Haiku scouts, about 75-85k tokens each)

Each scout had at most 12 searches and 6 fetches. "verified" = the scout saw the abstract or page this session. Numbers are as the scouts
reported them from abstracts or summaries, not checked against full papers unless noted. Nothing here was checked against code. It is
background for choosing candidates, not evidence about B2.

## What the literature says, grouped by the question it answers

**Why re-reading a small set hurts (our 7d diagnosis)**
- Muennighoff et al. 2023, NeurIPS, arXiv 2305.16264 (verified): up to about 4 epochs of repeated data is worth almost as much as unique data; beyond that, extra passes add little. Our night re-reads each record 32 times (7d) or 80 times (research-loop sleep).
- Verwimp, De Lange, Tuytelaars 2021, ICCV, arXiv 2104.07446 (verified): rehearsal models memorise and overfit the buffer.
- Chaudhry et al. 2019, arXiv 1902.10486, "Tiny episodic memories" (verified): repeating a tiny memory helped (+7-17%) only because fresh new-task data flowed alongside it.
- Ibrahim et al. 2024, TMLR, arXiv 2403.08763 (verified, fetched): re-warm + re-decay lr with about 5% replay matched from-scratch training (405M model). Their replay is a fraction of a fresh stream, not re-reading a fixed small set.

**Self-made replay (no stored data, no teacher)**
- Robins 1995, Connection Science (from memory): pseudo-rehearsal.
- Shin et al. 2017, NeurIPS, arXiv 1705.08690 (verified): deep generative replay (needs a separate generator).
- Sun, Ho, Lee 2020, ICLR, arXiv 1909.03329, LAMOL (verified): the same LM generates old-task samples; 2-3% below multitask.
- Ellis et al. 2021, PLDI, DreamCoder (verified, summary): wake (search) / abstraction / dreaming. Dreams = programs sampled from the library, run to make their own tasks, used to train the recognition model. Targets are programs, not answers.
- Zelikman et al. 2022, NeurIPS, arXiv 2203.14465, STaR (verified): train on own kept rationales; uses gold answers for "rationalization" (we would use the fit check instead).
- Marek et al. 2026, arXiv 2605.26097 (verified, summary only): self-generated replay with a KL penalty; reports a capacity limit for near-saturated models.

**Choosing what old material to replay**
- Saxena, Shobe, McNaughton 2022, PNAS 119(27) (verified): similarity-weighted interleaved learning. Replaying only the old items similar to the new ones gives similar accuracy with far fewer old items.
- McClelland, McNaughton, Lampinen 2020, Phil Trans B (verified): new items consistent with old structure integrate fast.
- Lopez-Paz & Ranzato 2017 (GEM), Chaudhry et al. 2019 (A-GEM, arXiv 1812.00420) (verified): gradient projection on a memory; GEM defines backward transfer (BWT). A secondary source gives GEM BWT +0.025 on permuted MNIST (unverified).
- Riemer et al. 2019, ICLR, arXiv 1810.11910, MER (verified): Reptile-style replay aligns gradients across examples (aims at positive transfer).
- Lin et al. 2022, NeurIPS, arXiv 2211.00789, CUBER (verified, snippet): positive BWT by changing weights for positively correlated old tasks.
- Scouts' summary: positive BWT is rare and appears mainly when old and new tasks share structure.

**Weight space: keep the night's change, but scaled**
- Wortsman et al. 2022, CVPR, arXiv 2109.01903, WiSE-FT (verified): interpolate fine-tuned and original weights; an intermediate mix beats both ends under shift.
- Ilharco et al. 2023, ICLR, arXiv 2212.04089, task arithmetic (verified): the night's change is a task vector; scale it by lambda.
- Yadav et al. 2023 TIES (arXiv 2306.01708), Yu et al. 2024 DARE (arXiv 2311.03099), Wortsman et al. 2022 soups (arXiv 2203.05482) (verified).
- Arani, Sarfraz, Zonooz 2022, ICLR, arXiv 2201.12604, CLS-ER (verified): fast and slow EMA copies of the learner.
- Biderman et al. 2024, TMLR, arXiv 2405.09673 (verified): LoRA learns less and forgets less.
- Scout's gap: no paper found with positive BWT from merging alone.

**Regularisers, lr and flat minima**
- EWC (Kirkpatrick 2017, arXiv 1612.00796), SI (Zenke 2017, arXiv 1703.04200), MAS (Aljundi 2018, arXiv 1711.09601), L2-SP (Li 2018, arXiv 1802.01483) (verified ids).
- van de Ven & Tolias 2019, arXiv 1904.07734 (verified): regularisers fail when the task must be inferred from the input (our case: one model, no task id). Replay is needed there.
- Mirzadeh et al. 2020, NeurIPS, arXiv 2006.06958 (verified): lr decay, dropout and batch size widen minima and reduce forgetting.
- Mehta et al. 2023, JMLR, arXiv 2112.09153 (verified): flatness (SAM) and forgetting.
- Kosson, Messmer, Jaggi 2024, NeurIPS (title verified): warm-up mainly limits early update size under Adam.

**Learned update rules (inside the model)**
- OML (Javed & White 2019, arXiv 1905.12588), ANML (Beaulieu 2020, arXiv 2002.09571), La-MAML (Gupta 2020, arXiv 2007.13904), fast-weight programmers (Schlag 2021, arXiv 2102.11174; Irie 2022, arXiv 2202.05780; Irie 2023, arXiv 2312.00276) (verified). All need an offline meta-training phase, so they are larger projects than one sleep.

## Fit to Ben's rules, and the three candidates

Ruled out for now: EWC / SI / MAS (van de Ven: weak without task identity, and the strength is a researcher's setting); GEM / GPM (per-step
projection cost; GPM can block the new skill); meta-learned rules (need meta-training outside the sleep); self-distillation targets from a frozen
copy (a "teacher", even if it is the old self; avoided to stay clearly inside the rules); SAM (doubles the step cost).

Picked (all three use only the model's own finds, its own training rows and outside tools it calls; no teacher, no answer-only targets):

1. **Fresh dreams (DreamCoder dreaming + Muennighoff/Verwimp):** every update's new-skill half is newly made: a found program is run by the
   executor on fresh inputs (drawn from inputs the day showed) to write a new prompt of the same rule. No prompt is read twice. The skills half
   is fresh rows, as now. Tests the 7d diagnosis directly: if harm is from re-reading, it goes away; if it stays, it comes from the skill itself.
2. **Self-chosen step size on the night's change (WiSE-FT / task arithmetic):** the deployed weights are N + a (W - N), with a chosen by the
   model from its own signals (fit rate on its held practice questions and its held self-check on its own skills training rows). Costs only checks.
3. **Interference-weighted fresh replay (similarity-weighted interleaving, Saxena 2022):** the skills half is drawn more from the families whose
   loss on the model's own held training slice rises during the night, measured by the model as it sleeps. Fresh rows only (Test R failed by reusing rows).
