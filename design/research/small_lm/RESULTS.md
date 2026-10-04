# LFM2.5-350M as hearer and talker: results (5 of 6 seeds; seed 4 re-running)

Marks: `../PASS-MARKS-SMALL-LM.md` (commit 51fcdcfb5 / bba53c04e, before any run). Numbers: `ANALYSIS-partial.json`.
Fast lane, in-family fresh set (FRESH-EN-R3.json, 192 questions).

## Verdict: both marks FAIL (shown, 5 paired seeds)

| | fresh exact | generated held-out | bank fit |
|---|---|---|---|
| 1.2B system (round 4) | 92.6% | 99.7% | 95% |
| **350M system** | **65.7%** (60.9-72.0) | 93.0% | 68% |
| bare 350M, zero-shot / 8-shot | 33.9% / 50.0% | | |
| bare 1.2B, 8-shot | 75.0% | | |

- M1 (drop at most 5 points): drop **26.9 points, CI 18.9 to 34.9**, every seed 21-34. FAIL.
- M2 (350M system at least 85%): 65.7%. FAIL. It is even below the bare 1.2B model.
- Lesion: zeroing the core's 8 vectors drops it to 0%, so the core is still doing the work.

## What it suggests (suggested, not tested)
- The trained parts add about the same on top of either LM (+15.7 over bare 350M 8-shot; +17.6 over bare 1.2B
  8-shot). The LM's own reading skill sets the level.
- 93% on generated held-out vs 66% on fresh text: the small LM learns the generator's style but transfers worse.
- Size of the borrowed LM matters here, so shrinking the whole LM is out. Next lever on the shortlist: keep the
  1.2B talker and stop paying for the second full read (half-depth hearer).

## Cost
~$1.6 on vast (two boxes were very slow and were replaced). `LEDGER.md`.
