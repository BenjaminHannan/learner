# rsn-296 results (builder): varied "sleep school" practice — registered verdict FAIL

Verdict first: **FAIL**. P296.1 fails on both plain seeds (fresh panel: 5 and 6 invented answers vs bar ≤ 2) and
P296.4 fails on both plain seeds (fresh-panel totals 225 and 217 vs bar ≥ 228). P296.2 passes both seeds
(transfer 238 and 238 vs bars 204/209 — the idea-killer did NOT trigger) and P296.3 passes both seeds
(code-doable 173 and 169 of 178 vs bar ≥ 168). PASS needed P296.1–P296.4 on both plain seeds.

Design: design/v3/30-modes/296-sleep-school-practice.md. One change from rsn-294: practice/dev episodes from
scripts/claude_rsn296_gen.py. Arms, sizes (~30.9M plain / ~30.8M loop), steps (6000 copy + 6000 practice),
batches, LR, reward, fact-check, seeds 1–2, eval code identical to 294. Reasoner code sealed and unpatched;
all code/panel seals verified OK on the GPU box before training (SEAL-code 6/6, panel296-v2 2/2, panel294-v3 2/2)
and `python scripts/claude_rsn296_gen.py` printed "selftest ok" (gold-action mismatches 0).

## Training (4 runs, 2 at a time, --workers 6, RTX 5090, torch 2.8.0+cu128)

| run | minutes | copy loss first → last | practice reward first → last |
|---|---|---|---|
| plain-s1 | 38.0 | 4.1244 → 0.0065 | 0.5944 → 0.9307 |
| loop-s1 | 78.4 | 4.2000 → 1.8531 | 0.0875 → 0.2565 |
| plain-s2 | 37.0 | 4.1609 → 0.0003 | 0.6296 → 0.9801 |
| loop-s2 | 77.2 | 4.2580 → 1.9657 | -0.0074 → 0.2544 |

Loop copy loss stays high both seeds (1.85/1.97): 294's loop seed-1 copy problem (D2) reproduced, deliberately unfixed.

## Panel totals (checked_right; each checkpoint evaluated exactly once)

reasonpanel296 v2 (298 items; code arm 208: 178/178 code-doable + 30/30 three-step, 0 counting/comparing/before-after):

| run | copy-only | final |
|---|---|---|
| plain-s1 | 167 | 225 |
| loop-s1 | 57 | 106 |
| plain-s2 | 181 | 217 |
| loop-s2 | 47 | 101 |

reasonpanel294 v3 (300 items; 294 plain finals were 184 seed 1 / 189 seed 2; code arm 210):

| run | copy-only | final |
|---|---|---|
| plain-s1 | 195 | 238 |
| loop-s1 | 59 | 89 |
| plain-s2 | 205 | 238 |
| loop-s2 | 49 | 87 |

Final-checkpoint category detail, fresh panel (checked_right / n): plain-s1 — backwards 30/30, before_after 24/30,
comparing 16/30, counting 12/30, three-step 0/30, missing 30/30, newest_correction 23/28, one_step 30/30,
two_step 30/30, yes_no 30/30. plain-s2 — backwards 30/30, before_after 20/30, comparing 16/30, counting 12/30,
three-step 0/30, missing 30/30, newest_correction 19/28, one_step 30/30, two_step 30/30, yes_no 30/30.
Transfer panel finals: both plain seeds 30/30 on backwards, missing, newest_correction, one_step, two_step, yes_no
plus 15/15 big-notebook; three-step 0/15; before_after 19/18, comparing 12/12, counting 12/13 (s1/s2).

## Marks (plain arm, final checkpoints, integer counts)

| mark | bar | seed 1 | seed 2 |
|---|---|---|---|
| P296.1 invented answers (answered without a fact), per panel ≤ 2/300 | ≤ 2 | fresh 5 FAIL / transfer 0 PASS → **FAIL** | fresh 6 FAIL / transfer 0 PASS → **FAIL** |
| P296.2 right on reasonpanel294 (≥ same-seed 294 plain + 20) | s1 ≥ 204, s2 ≥ 209 | 238 **PASS** (+54) | 238 **PASS** (+49) |
| P296.3 fresh code-doable (≥ code arm − 10) | ≥ 168/178 | 173 (30+30+23+30+30+30) **PASS** | 169 (30+30+19+30+30+30) **PASS** |
| P296.4 fresh total (≥ code arm + 20) | ≥ 228/298 | 225 **FAIL** (miss by 3) | 217 **FAIL** (miss by 11) |

Loop (no marks, same format): fresh final 106 (s1) / 101 (s2) of 298; transfer final 89 (s1) / 87 (s2) of 300;
invented fresh 4 (s1) / 0 (s2), transfer 2 (s1) / 1 (s2); loop copy-only checkpoints never learned one/two-step
(0/30), as in 294.

## Money

~$2.09 total across 4 rentals (dph × hours): training box 5090 $0.4727/h × ~3.52 h ≈ $1.66; recovery rentals
~$0.43 (one 6-min timeout, one success:false, one ssh-broken — all destroyed, 0 live after). Under the $4 combined cap.

## Checkpoints

Kept at ~/premonition-models/rsn296/<run>/ (copy_only.pt + final.pt per run); all 8 local sha256 match
SEAL-run.sha256.txt above. Weights never pushed.

## Deviations (all reported; code never patched, panels never read)

1. DATA LOSS (major): runs/*.json (train logs/summaries, dev, panel files) were staged on the training box but
   never copied back before its destroy; a 4th rental could not re-enter (ssh key rejected, box destroyed).
   Panel counts in this file are the verbatim category-level outputs printed from the one-per-checkpoint evals
   before the destroy; runs/<R>/ holds a DATA-LOSS note instead of the JSONs. train_log.jsonl full step series
   is unrecoverable; endpoints are in the table above.
2. Evals ran once per checkpoint (24/24, no FAILED lines) — the planned file-recovery re-run never happened
   (rental cap of 4 reached: 1 training success + timeout + success:false + ssh-broken).
3. Fresh-container torch 2.8.0+cu128 + numpy 2.3.2 used in place of a new venv (brand-new container).
4. RESULTS.md written on the Mac from transcript counts after the destroy (GPU gone); no numbers invented —
   every count above was printed from an actual eval output.
5. Pilot loop seed was 9 for both arms as specified (an earlier tangled launch with a wrong-cwd loop start
   failed instantly with no training; clean pilots: plain copy 0.23 min + practice 0.20 min, loop copy
   0.51 min + practice 0.33 min → pair estimate ~142 min wall, under the 150-min gate).

## What it means (plain high-school English)

Varied practice worked for carrying skills to differently written notebooks: both plain models jumped from
~184–189 to 238 on the old blind test, learned two-step fully (30/30 fresh), and beat the pass bars for
transfer and code-doable questions. But it did not make a full reasoner: both models still invent answers
5–6 times when no fact exists (bar: at most 2), still get zero three-step questions, and fall 3 and 11 points
short of the fresh-panel total bar. Comparing sits at 16/30 and counting at 12/30 — better than chance now,
not solved.

## What it doesn't mean

It doesn't mean varied practice failed — the transfer mark passed big on both seeds, which is exactly what
would have proven the idea wrong had it failed. It doesn't mean the loop arm works — loop never learned to
copy (same as 294, still broken). It doesn't mean models reason like the code — the code gets 208 with zero
guessing, while the models guess without facts and miss every three-step question.
