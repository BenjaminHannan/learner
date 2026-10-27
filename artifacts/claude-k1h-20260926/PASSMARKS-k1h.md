# PASSMARKS k1h: the LFM creative writer, taught from GLM's answers (Creative answers in chat thread, written 2026-09-26 19:48 UTC)

Fixed before any k1h training or run, and before any k1f result exists (k1f has not run anywhere: rent-k1f HOST-FAIL,
k1f-benspc NOT-RUN; k1f-benspc2 is queued). Sealed in SEAL-k1h.sha256.txt with the code, the data gate, the judge
instructions and k1f's and the panel's seals. Registered FAILs stay FAILs.

## Why
The Thread manager, 19:33 UTC (the "obvious fix first" rule after Ben's 19:20 message): list the plain, well-known fixes
and test the simplest one. For a small model that writes weak answers, the textbook fixes are (1) a better base model
of the same size, which is k1f, and (2) teaching the model from a stronger teacher's answers (distillation /
instruction tuning), which had never been tried here: no script had trained the creative writer (k1c, k1d and k1e
worked on picking among its drafts). On DEV, a useful draft was among the writer's 4 on 26 of 40 chats but the first
passing draft was useful on only 12 (VERIFY-k1c.md correction): training raises the first draft; picking only works
above it.
Brain picture (Ben 16:05; textbook-level, the mapping to our parts is a guess): young songbirds and children first
copy a tutor's output, and only then refine by trial and reward. We tried the reward/choice stage first.

## The single change
k1h, scripts/claude_k1h_cre.py (build_null_k1h): k1f's writer (the k1a writer on LFM2.5-1.2B-Instruct
@0f604ada3f766f9f257460c4c9f0b5d6f69d431b) with one LoRA adapter merged into its weights, trained by
scripts/claude_k1h_train.py on GLM's answers. Everything else is k1f's: routing by is_creative333c (a hand-written
regex in the build since 0.2c; Ben chose "Remove" for the next build at 18:39:38 and Month-end owns that; here it is
disclosed test scaffolding), the prompt (SYSTEM333D + notebook facts, the chat's last 12 messages, the request), 4
samples at temperature 0.7 and top_p 0.9, 200 new tokens, thinking off, trim, guard333d, the FALLBACK line, no notebook
writes, and the rest of the build on MiniCPM5-1B with 0.2c's sleep adapter. Why the LFM writer and not MiniCPM5-1B:
the build's MiniCPM writer shares the model that carries the sleep adapter (scripts/claude_e2e02c.py:59-72), so an
adapter there would be two changes at once; LFM is also the stronger same-size base (plain: 103 vs 46 of 160 in k1c).
Tests: scripts/claude_k1h_test.py (5/5: the adapter's sha is checked, it is merged once, and the prompt, drafts'
handling, reply, counters and WORK entry equal k1f's for the same drafts).

## Data (GLM's words only; no Claude-written text is a target)
DATA-GATE-k1h.md, written 19:32 UTC before any answer existed, applies in full: the 240 k1e practice chats plus about
650 new GLM chats (claude_k1h_glm.py chats), one GLM answer each (claude_k1h_glm.py answer), the build's own filters,
gate 1 (no fixed frame), gate 2 (a blind 60-answer check: useful >= 48, made-up <= 3), gate 3 (size >= 600; no
near-copy of a DEV chat or, by a blind agent, of a k1fpanel item). If any gate fails, nothing below runs.

## Training (BensPC, free; one job with the H arm below)
1. Practice prompts: the k1f build runs over the kept practice chats (claude_panel382_run.py --panel creative, arm
   claude_k1h_cre:build_null_k1f_prompts, F env plus K1H_PROMPTS), so each chat's last request is logged with the
   exact messages the writer gets at run time, the build's own replies to the earlier messages included.
2. Rows: each logged last request paired with the chat's kept GLM answer; 10% of chats held out as dev (seed 4612).
3. A smoke first (practice rows only, --limit 16 --max-steps 2, into a scratch folder that is then deleted): it must
   pass the end-of-turn check, give every trainable weight a gradient and save an adapter.
4. The recipe, fixed in claude_k1h_train.py: LoRA rank 16, alpha 32, dropout 0.05 on every linear layer; AdamW lr
   2e-4, no weight decay; 2 epochs; batch 8 (4 x 2); warmup 5% then cosine to 0; rows over 1536 tokens dropped
   (counted); seed 4613; bf16 base, float32 adapter; the last step's adapter is used (dev loss is reported, not used to
   choose). Torch 2.11 (BensPC's). Loss on the answer tokens only; the prompt is rendered and tokenized exactly as the
   writer does at run time.
The adapter stays on BensPC (never pushed); its sha256 is reported and checked by the H arm at load.

## Arms (one panel run for H; runner claude_panel382_run.py unchanged)
- H = claude_k1h_cre:build_null_k1h (SLEEP02C_ADAPTER = 0.2c's adapter02c.pt sha256 a33211dc...36f5, K1F_WRITER_MODEL
  = the LFM snapshot, K1H_WRITER_ADAPTER and K1H_ADAPTER_SHA256 = the trained adapter). Registered (marks K1h).
- F, T, Q, L: the replies of k1f's registered run (artifacts/claude-k1f-20260926/run/creative_{F,T,Q,L}.jsonl), used
  unchanged. Per-turn seeds come from (turn number, text), so H and F are paired item by item. If k1f's run does not
  produce all four files with 100 items, the k1h job runs the missing arms itself with k1f's exact commands
  (k1f-benspc2 step 4), before H.
- DEV gate for H, before the panel: H on the 40 DEV chats (artifacts/claude-k1a-dev-20260926); it must exit 0 with 40
  item lines, print the V1 lines, and have at most 2 fallback lines and no empty reply on the last request.
- V1 (logH and the DEV log): "mu402: adapter loaded = " with the 0.2c adapter path; a line starting "k1h: creative
  writer = install_creative_k1h; writer = lfm2 @0f604ada + adapter " followed by the adapter's first 8 sha256 hex
  characters; no "k1a:" line.

## Panel
k1fpanel (artifacts/claude-k1fpanel-20260926/creative, 100 items, sealed, TEST-ONLY). Fresh for k1h: every k1h choice
above was fixed before any k1f command ran, so nothing in k1h was chosen from this panel. H runs on it once.

## Judging (JUDGE-k1f.md's words and procedure)
claude_k1h_score.py --gather (H from the k1h run; F, T, Q, L from k1f's run), then the runner's --score with names
H,F,T,Q,L (seed 3822), then --dedupe (one line per distinct reply to each item, ids E...., seed 3824). Judges 1 and 2
(blind Opus agents, private folders, chunks of at most 150 lines) judge every line; judge 3 decides the lines they split
on (useful, or made-up >= 1). k1f's own judging is separate and is not reused. A blind recount by a separate agent before
anything is reported.

## Marks for k1h (H vs F over all 100 items; PASS = all three)
| Mark | What | Bar |
|---|---|---|
| K1h.1 | useful, H - F; and a one-sided exact sign test on the items where exactly one of H, F is useful | >= +8 and p <= 0.05 |
| K1h.2 | replies with a made-up fact about the user, H vs F | H <= F + 4 |
| K1h.3 | fallback lines on the last request, H vs F | H <= F + 2 |

## The K1 line (the owner problem's bar; its own verdict, reported beside k1h)
H useful on >= 60 of 100 AND H >= T, H >= Q and H >= L on useful.

## 0.2d's K1 row as a dry run (registered readings, not part of the k1h verdict)
For H and for F: claude_k1rival_score.score (sealed for 0.2d) on this panel: per rival T, Q, L the reading and the
made-up margin; the row passes when all three pass.

## Report only
H - F on lead, no-lead and uses_facts items; H vs L and H vs Q (difference, items only one side got, reading); per
arm: made-up, fallbacks, empty replies, bare list endings, median words; the training summary (rows, dropped rows,
dev loss before and after each epoch).

## Expected before running (nothing about this training has been measured)
F is not known yet (k1f's expectation: about 50 to 65 of 100). Teaching from about 800 good answers usually moves a
small model's style and form a lot and its content less. My guess: H - F about +5 to +15, so K1h.1 passes maybe half
the time; H >= Q is the hardest part of the K1 line. K1h.2 is the mark most at risk if GLM's answers state details
about people that the chats never gave (gate 2 counts this before training).

## What would prove it wrong
K1h.1 failing (H - F below +8, or sign p above 0.05) means teaching the LFM writer from GLM's answers, with this recipe
and about this much data, does not make its replies more useful. H's made-up replies above F's + 4, or its fallbacks
above F's + 2, also fail it. Report-only: H vs L "behind" would mean the adapted writer lost what plain LFM had.

## After the verdict
- PASS: tell the Thread manager (for Ben) and Month-end: the creative writer can be install_creative_k1h (LFM2.5-1.2B
  plus a small adapter, loaded for creative turns only). It joins 0.2d only with Ben's yes.
- FAIL: read H's DEV replies and the training summary to find where it loses; the next single change is sealed before
  any run.
