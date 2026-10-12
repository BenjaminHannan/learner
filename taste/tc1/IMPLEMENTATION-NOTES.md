# TC-1 implementation notes (defaults chosen where the spec was silent)

Run from `/home/user/learner/taste`: `python3 -m tc1.run --arm C --seed 1 --out DIR`, `python3 -m tc1.pretest --seed 1 --out DIR`,
`python3 -m tc1.analyze DIR`. Tests: `python3 -m pytest tc1/tests` (pytest is not in the torch python; the tests were run with
the uv-tool pytest site-packages on PYTHONPATH). Pretrain once per seed first (`--pretrain-only`); the checkpoint is reused by all arms.

## Grammar / tokens
- Vocab 19: PAD0 BOS1 END2 R3 T4 D5, numbers 0..12 = tokens 6..18. Sequence = BOS + commands + END, max 38 tokens, context 40.
- `parse` accepts an optional leading BOS; END must be the last token (tokens after END = invalid); 0 commands (just END) parses
  but fails the check (draws nothing). Arity/range violations, 7th command, missing END = None.
- T: row r-i over columns c+i .. c+w-1-i while width w-2i > 0 and row >= 0, clipped at the right edge.
- random_program: n uniform 1..6; each type uniform; every parameter uniform over its legal range (h,w 1..12; r,c 0..11; k 1..4).

## Houses
- Params drawn then position by rejection: top uniform in [roof rows, 12-bh], left uniform in [overhang, 12-bw-overhang]; overhang 0/1 equally likely.
  Roof rows = ceil(base/2). Door column = left + (bw - dw)//2.
- Novel sub-family: needs bw>=5, bh>=3; door height drawn 1..bh-2 so a window row exists; window row uniform strictly between body top
  row and the door top row; window pair at columns left+j and right-j, j uniform 1..(bw-2)//2 (strictly inside, mirror-symmetric, distinct).
- Seed streams: `default_rng([seed, 4242])`; 200 critic, then held-back and novel regenerated until copy distance >= 1 from the 200.
  Held-back/novel are not de-duplicated against each other.
- Broken houses for the critic exam (built from held-back generator params, exam-only): roof below = body with the stepped roof
  drawn directly under it narrowing downward, whole picture shifted up so it fits; door up 2 = door rectangle painted 2 rows higher
  (original door cells stay body colour); shuffled = cells permuted randomly (same colour counts). The exam AUC "held-back vs broken"
  pools the three kinds (300 pictures); per-kind AUCs are also stored.

## Hidden score (precise choices)
- Body: as specified (bbox >=3x2, no white inside, A >= half the box; largest box, ties lower id).
- Roof: several colours may qualify; the one with most cells wins (ties lower id). Roof rows must be consecutive; each row contiguous; lowest row
  body_left-1<=l<=body_left and body_right<=r<=body_right+1; each higher row no wider than the row below (not required to be nested; spec wording).
- Door: any colour not in {A, B (if roof found), 0} that exactly fills its bbox, bbox inside body box, bottom = body bottom, w<=bw-2 (no height limit; spec wording).
- Symmetric: mirror about body_left+body_right; pair counted once; a non-white cell whose mirror is off-canvas counts as one mismatch; <=1 allowed.
- Clean: non-white cells all inside body box or colour-B (roof colour). Traits 4,5 only count if 1 and 2 hold.
- Mean over 2000 random day-0 programs = 0.0595 (unit test prints it).

## Copy guard
- Shifts/mirror applied to the critic examples (18 variants each, vacated cells white); Hamming via one-hot matmul.
- k = (second smallest held-back distance) - 1, i.e. largest k with at most floor(1%*N) = 1 of 100 held-back at distance <= k.

## Maker / training
- 803,347 parameters (4 layers, d 128, 4 heads, FFN 4x, pre-LN, GELU, learned positions, untied head). Init N(0, 0.02).
- AdamW weight decay 0.01 (all arms, pretraining and nights); gradient clip 1.0 (pretraining, nights). Loss = mean per-token CE, PAD ignored.
- Pretraining: 200,000 programs, 2 epochs of 781 full batches of 256 (remainder dropped) = 1562 steps, cosine 1e-3 -> 1e-4. 20,000-program replay pool and
  2,000 held-out programs come from the same seeded stream and are stored in the checkpoint. Checkpoint filename encodes the pretraining config.
- Sampling: KV-cache, inverse-CDF on pre-drawn uniforms; PAD/BOS are not masked (an emitted one makes the program invalid).
- Night: 256 steps (16 visits x 512 rows / 32 kept) with 32 replay rows drawn uniformly with replacement from the pool per step; fresh AdamW each night.
  If no request passes, the night is skipped.

## Day
- Random streams: request i on day d of seed s uses `default_rng([s, d, i])` for 16x39 token uniforms + 1 pick uniform. Arms use the first 8 (pretest 16),
  so the pretest's first 8 tries equal day-1 tries. R/H/O/ties and C/B ties use the pick uniform; fill-in resampling uses `[s, d, 99991]`.
- Check: parses and draws >= 1 cell. Copy = copyguard distance <= k (checked only on valid tries). Picking uses only passing (valid, non-copy) tries.
- Critic and blank critic rank by logit (monotone in the sigmoid score; avoids saturated ties). Blank critic: same net, init seed (seed+77), never trained.
- Critic buffer = all passing tries so far (duplicates kept). Critic Adam state is continued across days. Critic exam "fresh tries" = today's passing tries,
  computed after today's training (the critic that picks).
- H key = (#commands, mirror mismatch pairs about the picture's own bounding-box column centre), then random.
- O: `oracle.scores` passed in by run.py; night.py never imports hidden_score/oracle/eval (test checks source and a fresh interpreter's sys.modules).
- Arm N: evaluated at night 0 only; the night 1..6 entries copy it (flagged `reused_from_night_0`).

## Evaluation
- 1,000 raw samples per temperature, stream `[seed, 9000+night, temp_index]` (same across arms). Copies score 0 (and count 0 for traits/full house).
- copy_rate = copies / all raw samples (gated for TC1-3); copy_rate_of_valid also stored. valid_program_rate = parses; draws_cells_rate also stored.
- Canonical form: translate drawn cells to top-left, also translate the mirror image tight to top-left, take the byte-wise min.
  distinct_share and top10_share are over drawn pictures; top10_share_of_samples (over all samples, the literal TC1-4 reading) is what is gated.
- Held-out loss = per-token mean CE over the 2,000 held-out random programs.

## Pretest
- Day-1 streams, 16 tries, temperature 1.0; critic trained on the passing tries among the first 8 per request with day-1 settings (seeded `[seed, 7001]`).
  Requests with no passing try score 0 for every picker (`mean_given_pass` also stored). Headroom = O - R at 8 tries.

## Analysis (spec ambiguities resolved)
- All marks use night-6 values, temperature 1.0 unless stated, and means over seeds. TC1-2: best competitor chosen per seed among
  {B, H, R07@1.0, R07@0.7, N@1.0, N@0.7} (stricter than best of seed-means; the latter is also stored). TC1-3/4/5 gated on seed means (per-seed stored).
  TC1-5 loss rise compares the mean day-0 and night-6 held-out loss of arm C.
- SHORTCUT: TC1-1 holds and mean(C-H) < 0.03 or mean(C-B) < 0.03. NO GAIN, TOY TOO HARD (mean O-R at night 6 < M), UNDERPOWERED as specified.
  When several verdicts apply, precedence PASS > SHORTCUT > TOY TOO HARD > NO GAIN > UNDERPOWERED (spec is silent); all that apply are listed.

## --small
requests 64, 2 days, 8,000 pretraining programs (batch 64), pool 2,000, held-out 200, 50 critic steps, 200 eval samples. Smoke only.
