# Pass marks: smaller hearer and talker (LFM2.5-350M), written before any run (2026-10-04)

Fast lane. Never scored on GOLD-PRIVATE-v1.json; no reserved or blind panel touched.

## One change
Round 4 English recipe (`reasoner_ptr/real/english/run_english.py`, branch `claude/project-thread-ajo58u`,
`--arm allptr --gen 8000`, 6 practised kinds, 2000 steps) with only
`--lm LiquidAI/LFM2.5-350M --revision 9e6c6ccf47cd318696e137d381a7ded8fe4df09f` changed.
The reader and exit adapter shrink with the LM width (2048 -> 1024); the core is unchanged.

## Data and seeds
Same fresh test as round 4: `FRESH-EN-R3.json`, 192 questions. Seeds 0-5, paired with the round 4 1.2B seeds
(89-96%, mean 92.6%). Reference rows: bare LFM2.5-350M zero-shot and 8-shot (`lm_alone`, `lm_fewshot`), seed 0.

## Marks
- **M1, enough size (non-inferiority):** mean paired drop vs the 1.2B system is at most 5 points
  (350M system mean >= 87.6%), and no seed drops more than 10 points.
- **M2, beats a bigger model:** 350M system mean >= 85.0% (bare 1.2B 8-shot was 75.0%, mark is +10),
  and every seed above 75.0%.
- **Speed (reported, no mark):** prompt-read questions/s at batch 1 and 64, same 5090 and script as PR #35.

## What would prove it wrong
- M1 fails (mean drop > 5 points): the 1.2B's size matters on this task. Next step is the half-depth hearer
  (keeps the big talker), not a smaller LM.
- M2 fails but M1 passes: cannot happen by arithmetic unless seeds are very spread; if it does, report as mixed.
- Zeroing the core's 8 vectors (existing lesion) should still drop the 350M system to near 0%; if it does not,
  the small LM is answering without the core and the comparison is not about the core.

## Caveat (suggested)
The fresh set is in-family with the practice generator. A pass says "350M is enough for this kind of reading",
not "350M is enough for everything".

## Cost cap
Six 5090 boxes, about one hour each, about $1 total; stop at $2.
