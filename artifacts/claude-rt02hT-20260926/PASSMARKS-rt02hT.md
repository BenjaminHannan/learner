# PASSMARKS rt-02h-T: how many examples of a new way of asking does the learned puzzle check need? (registered 2026-09-26 17:34 UTC)

Owner: Plain-English puzzles thread. The time comes from `date -u`. Written before the script was run. Never edited;
changes go in a dated addendum before the run.

## Why
rt-02h (registered FAIL, e62b1069e) read 0 of 10 puzzles in one blind wording, wording 5, and 86 of 90 in the other
nine. The Thread manager asked: "How many examples of it does the head need before it reads 9 of 10? If it needs 50, it
memorised wordings. If it needs 3, it learned 'request for a puzzle'." Ben's main mark is carry-over, meaning how few
examples a new kind needs. Wording 5 cannot be used, because reading the blind panel is forbidden. So the question is
asked of the 6 asking styles in rt-02h's practice instead.

## What runs (practice data only; no blind panel; $0 on this container's CPU)
- Data: rt-02h's 337 kept 1B drafts (artifacts/claude-rt02h-20260926/train/drafts_1b.jsonl) and their saved features
  (claude_rt02h_probe.py feats, sha256 in SEAL-code). The 144 positive drafts come in 6 asking styles (the 6 prompts
  the 1B was given). Negatives are 193 drafts in 75 prompt groups.
- For each style h: the head is trained the rt-02h way (layer 18, L2 0.001, as registered) on the other 5 styles'
  positive drafts, k drafts of style h, and the training negatives. The cut uses rt-02h's rule: 5-fold CV by prompt,
  with held-out negatives firing on 1% or less. k = 0, 1, 3, 5, with 3 random draws of the k examples for k > 0. The
  median over draws counts.
- Test: style h's drafts from half of its prompts, never the prompts the k examples came from. Test sizes by style
  are 24, 20, 5, 8, 13, 9, and example pools are 17, 13, 5, 6, 14, 10. A k larger than the pool is not measured.
- Recognised = the head's score is at or above the cut. This is the step where wording 5 failed. The copy step is not
  part of this test.
- One fifth of the negative prompt groups is held out of training, and their fires are reported.

## Marks (fixed now)
- k* for a style is the smallest k at which 90% or more of its test drafts are recognised.
- T1, "learned a request": the median k* over the 6 styles is 3 or less. A style that never reaches 90% counts as
  infinity.
- T2, "memorised wordings": 3 or more of the 6 styles are below 90% at their largest measured k.
- Verdict: T1 gives "learned a request". Otherwise T2 gives "memorised wordings". Otherwise "in between".
- Report only: the rate by k per style (the carry-over curve), k = 0 for each style (pure carry-over), and held-out
  negative fires.

## Limits (stated now)
- All 6 styles were written by the 1B from Claude-written instructions. They sit closer together than real people's
  wordings, so T1 here is weaker evidence than it looks. A T2 here is strong evidence of memorising.
- The largest k is 5, not 50, because the pools are small. "Needs more than 5" is the most this can show.
- Nothing here changes rt-02h's registered FAIL.

## What would prove the "learned a request" reading wrong
Most styles need 5 or more examples, or never reach 90%. The head would then key on the surface of each style, and
the next change is breadth of wording (GLM plus the 1B), as rt-02h's VERIFY already says.
