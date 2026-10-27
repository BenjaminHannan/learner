# 119g outcome + diagnosis (director, 2026-09-22 12:05)

**Registered verdict: FAIL** (M1 fails on 3/3 seeds). The seal verifies (PASSMARKS OK). The code hashes match the recorded prefixes (model 38ba94b9, train 062eab5a, score 0feefe2e, smoke 9067d69e, wave f5e1cd82, scp 06e63112, doc c6bdef13). The only post-seal change is the disclosed D1 scorer wrapper (DEVIATIONS-director.md). The wave ran 11:04:02–11:40:28 (2186 s).

## Marks (reading94b, 400 sentences, 378 gold facts, 94 occupation golds; every seed)

| Mark | Bar | 11911 | 11912 | 11913 | Result |
|---|---|---|---|---|---|
| M1 occupation exact (K=3) | >= 10/94 each seed | 1/94 | 1/94 | 1/94 | **FAIL** |
| M2 raw exact (K=3) | >= 33/40/37 | 91 | 82 | 100 | PASS |
| M3 ungated precision (K=3) | >= step-0 − 0.10 (0.085/0.065/0.090) | 0.193 | 0.166 | 0.204 | PASS (vacuous guard; precision actually ~2.3x step 0) |
| M4 wrong-write rate | <= 5% if writes | 0 writes | 0 writes | 0 writes | PASS (vacuous) |
| F1 slot stealing | only if M1 passes | n/a | n/a | n/a | does not fire |

Descriptive numbers:
- Step 0 (119f checkpoints, old decode): raw exact 24/19/27.
- 119g old unconditioned decode (K=1): 15/11/14.
- 119g top-1 conditioned (K=1): 52/48/61.
- reading94 (descriptive panel) K=3: raw exact 73/64/68, occupation 0/44.

**What it means:** giving each relation its own read-out works. The model now reads **3.4–4.3 times as many correct facts** from real encyclopedia sentences as 119f (91/82/100 against 24/19/27), at about twice the precision. **What it doesn't mean:** occupation is still missed; the target skill did not improve at all. Also, 0 facts pass the write gate, so none of this reaches the notebook yet.

## Diagnosis (inference only; scratchpad diag119g.py on the 3 checkpoints; panel looked at in AGGREGATE only)

1. **On its own training shape the skill is perfect.** On 40 synthetic occupation training rows, occupation is ranked 1st 40/40 and the forced-occupation read-out is exact 40/40 on all 3 seeds.
2. **The relation picker never offers occupation on real sentences.** Over the 51 reading94b occupation sentences, occupation ranks 1st in 1/51. It ranks 6th or lower in 48–50/51, and has p < 0.03 in 49–50/51. With K=3 it essentially never gets a read-out.
3. **The reader is also weak off-template.** Forced to read occupation (oracle relation), the result is exact 7/2/10 of 51. The most common outcome is subject right, wrong object (18–26), then broken object span (6–20), then boundary errors (1–8).
4. **Fresh director sentences (fictional, per-sentence, kept outside the repo) show the cause:**
   - "NAME **was** a NAT JOB." gives occupation ranked 1st at p ≈ 0.95 and the right job.
   - "NAME **is** a NAT JOB." gives country of citizenship first (occupation ranked 2nd–12th).
   - Any "(born 12 May 1970)" or "(4 March 1901 – 9 June 1966)" bracket puts date of birth/death first (occupation ranked 5th–35th).
   - Forced read-outs grab "Czech pianist", "Samoan", "Italian", "Brno".

**Cause.** The 5,000 synthetic occupation rows (fable_ears119f_data.occ_rows) use exactly two templates, both past tense: "NAME was a/an NAT JOB." and "NAME (Y1-Y2) was a/an NAT JOB and JOB2.". Each row labels ONLY occupation, although the same sentence also states a nationality (and dates). The model therefore learned surface cues ("was", year-only brackets) instead of "a job word". It also learned that these shapes carry no citizenship and no dates, while real WebRED "is a NAT …" rows teach citizenship. The single-label relation head then puts occupation's probability near zero on real sentence shapes.

**Follow-up (one change): 119h.** Replace the occupation generator, and nothing else, keeping the 119g model/recipe/seeds/K/FLOOR and the pool size, so the step count stays 8838. The new generator:
- varies the shape: is/was; "(born D Month YYYY)", "(born YYYY)", "(D Month YYYY – D Month YYYY)", "(YYYY–YYYY)", "born in PLACE"; retired/former/professional; multi-word jobs; job lists;
- labels every fact each sentence states, one row per fact (occupation, citizenship, birth/death date, birthplace), following the pool's own WebRED span conventions.

Because the relation head is a softmax trained on one row per fact, it should learn to split its probability across the stated relations. That puts occupation into the K=3 read-outs.
