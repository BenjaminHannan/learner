# y1u: does plain LFM2.5-1.2B already answer from memory better than MiniCPM5-1B? Eval only, no training (Answering-from-memory thread, rules fixed 2026-09-27 18:20 UTC, before any LFM reply on this bank exists; sealed in SEAL.sha256.txt)

**Why:** y1t (trained doubt on MiniCPM5-1B) was NO-GO on DEV: right 22 of 56, wrong 20, "don't know" 5 of 10
(VERIFY-y1t.md, main e510853fb). The Thread manager (18:17 UTC): don't train a new MiniCPM adapter yet. c1-dev showed
plain LFM2.5-1.2B far ahead of the MiniCPM talker, and c1-dl (LFM as the talker) is running. The cheapest useful test is
eval only: plain LFM2.5-1.2B, no training, on the same DEV, scored with the same bars.

**The one change:** y1t's eval_plain step with the model changed from MiniCPM5-1B to LFM2.5-1.2B-Instruct at commit
0f604ada3f766f9f257460c4c9f0b5d6f69d431b (bm-390's and c1-dev's pinned snapshot). Everything else is the same:
scripts/claude_y1g_doubt.py unchanged (its sha256 and its imports' are checked against SEAL-y1t-rental.sha256.txt before
the run), the DEV bank artifacts/claude-e2e331-dev-20260924 (71 asks: 56 answerable, 5 partial, 10 never-told), seed
4024, y1f's L1 layout (system line plus every earlier user turn), thinking off, the same checks. Command:
`python -B scripts/claude_y1g_doubt.py --model <LFM snapshot> --out artifacts/claude-y1u-20260927/run/lfm`.

**Machine:** this thread's cloud container, CPU only (4 cores, torch 2.14.0+cpu, transformers 5.17.0, float32), $0.
The earlier references ran on GPUs in bfloat16, so greedy replies can differ by a few tokens. To compare on one machine,
plain MiniCPM5-1B (commit 87179e5c1f455ef22e6223592d2d61351b525bfc) then runs the same command on the same CPU
(`--out .../run/minicpm`, report and proved-wrong test only). LFM runs first, so its verdict does not wait on the second arm.

## Decision rule (fixed before the run; y1t's bars, A1 on DEV)
- GO if LFM's A1 has answerable right >= 22 of 56 AND answerable wrong-candidates <= 8 AND never-told "don't know"
  >= 8 of 10.
- References, not part of the rule: plain MiniCPM5-1B 26 / 24 / 2 (y1g, and y1t's eval_plain on another GPU); y1t's
  trained MiniCPM 22 / 20 / 5.
- GO: plain LFM clears the bars trained MiniCPM missed. The recall path's answerer choice goes to the Thread manager
  (a talker or answerer switch is Ben's call); bank E stays unused until marks for it are sealed.
- NO-GO: the candidate next test is y1t's recipe (trained doubt from its own graded drafts) on LFM, under its own
  sealed plan, and only if the proved-wrong test below does not fire.

## Proved wrong
"LFM's lead in c1-dev carries over to answering from memory" is wrong if LFM's A1 is not ahead of plain MiniCPM's A1
on the same CPU by at least 3 on either count: (LFM right - MiniCPM right) <= 2 AND (MiniCPM wrong - LFM wrong) <= 2.
If the MiniCPM arm does not finish, the GPU reference (26 / 24) is used instead and the verdict says so.

## Report (after the verdict)
Per ask type; C3, C4 and V (report only); which of MiniCPM's right asks LFM also gets right; seconds per ask; whether any
ask hit the 200-token cap.

## Predictions (thread, before the run)
GO: 0.1. Right >= 22: 0.65. Wrong <= 8: 0.1. Never-told "don't know" >= 8: 0.25. Proved wrong: 0.35.

## Limits
DEV has 56 answerable and 10 never-told asks, so a difference of 1 or 2 is noise. CPU float32 against GPU bfloat16 is
why the same-CPU MiniCPM arm exists. The DEV bank has been used for y1g and y1t, so it is not blind; bank E stays blind.

## Plain summary for Ben
Training the small MiniCPM model to say "I don't know" didn't work well enough: it still gave 20 wrong answers out of
56. Another small model, LFM, did much better than MiniCPM in the everyday-chat test. Here LFM answers the same 71
memory questions with no training, on this thread's own computer (free). It passes if it gets at least 22 right, at most 8
wrong, and says "I don't know" to at least 8 of the 10 things it was never told. MiniCPM then answers the same questions on
the same computer, so the two can be compared fairly. If LFM is not at least 3 answers better, its chat lead doesn't
help memory answers.
