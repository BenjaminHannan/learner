# PASSMARKS k1f: LFM2.5-1.2B-Instruct writes the creative replies (Creative answers in chat thread, written 2026-09-26 17:26 UTC)

Fixed before any registered run. Sealed in SEAL.sha256.txt with the code, the judge instructions and the panel's
seal. Registered FAILs stay FAILs. Not launched until Ben says yes (or doesn't object) through the Thread manager:
which model writes creative replies is an architecture choice, so it is his.

## Why
k1c (VERIFY-k1c.md, blind judges and a blind recount): on the same plain recipe (the twin's system line, the whole
chat, thinking off, greedy, at most 160 new tokens) plain MiniCPM5-1B was useful on 46 of 160 creative requests,
plain LFM2.5-1.2B-Instruct on 103 and plain Qwen3.5-2B on 114. Our writer (k1a, 46) and the 1B picking among its own
drafts (k1c, 47) stayed level with plain MiniCPM5-1B. The drafts are the limit, so the model that writes them is the
thing to change. LFM2.5-1.2B is the same-size choice (Qwen is 2B).

Brain picture (Ben 16:05; textbook-level, inferred, not checked here): the brain's generator for new ideas is not the
system that parses language or keeps track of the conversation; different circuits propose and select. Here the part
that proposes creative drafts becomes a model that proposes better ones, while the rest of the build stays as it is.
No hand-written rule is added (Ben's Redirect, 16:04).

## The single change
k1f, scripts/claude_k1f_cre.py (build_null_k1f): the k1a writer, unchanged, with its model swapped from the build's
MiniCPM5-1B to LFM2.5-1.2B-Instruct @0f604ada3f766f9f257460c4c9f0b5d6f69d431b (env K1F_WRITER_MODEL; no sleep
adapter on it). Same routing (is_creative333c), same prompt (SYSTEM333D + notebook facts, the chat's last 12 messages,
the request), same sampling (4 samples, temperature 0.7, top_p 0.9, 200 new tokens, thinking off), same trim, same
guards (guard333d: 140 words, refusals, memory claims, unknown relatives' names), same FALLBACK line, no notebook
writes. Everything else in the build, the sleep adapter included, stays on MiniCPM5-1B.
Tests: scripts/claude_k1f_test.py (6/6; the prompt, reply, counters and WORK entry equal k1a's for the same drafts).
The LFM model is not in the cloud container, so no CPU check with the real model was possible; the DEV gate below
is the first run with it.

## Arms (one rental; runner scripts/claude_panel382_run.py unchanged; per-turn seeds identical in F and K)
- K = claude_k1a_cre:build_null_k1a (k1a as registered: 0.2c's build with the k1a writer, NullReader, per-turn seeds,
  SLEEP02C_ADAPTER = 0.2c's adapter02c.pt, sha256 a33211dc...36f5). The base.
- F = claude_k1f_cre:build_null_k1f = K with the writer on LFM2.5-1.2B-Instruct. Registered (marks K1f).
- T = plain MiniCPM5-1B @87179e5c, Q = plain Qwen3.5-2B @15852e8c16360a2fea060d615a32b45270f8a8fc,
  L = plain LFM2.5-1.2B-Instruct @0f604ada3f766f9f257460c4c9f0b5d6f69d431b, all on the plain twin recipe
  (scripts/claude_e2e336_twinb.py), downloaded on the rental at those pins (Benchmarks' pins; Ben approved both rivals
  02:12 UTC 2026-09-25). Nothing comes from BensPC's copies.

## Panel (TEST-ONLY, never read by the builder)
k1fpanel, artifacts/claude-k1fpanel-20260926/creative: 100 fresh items written blind by a separate agent from the same
spec as k1cpanel and crepanel02d (35 idea with 1 lead-in turn, 35 idea with none, 30 uses_facts with 1, 2 or 3 teach
turns), audited blind by another agent against the DEV set, k1apanel, k1cpanel and crepanel02d (near-copies
reworded). Fresh because LFM was chosen from k1c's results on k1cpanel and k1apanel. Never run before.

## DEV gate (before any panel run; readable DEV data, artifacts/claude-k1a-dev-20260926, 40 chats)
F runs once on the 40 DEV chats. It must exit 0 with 40 item lines, print the V1 line, and have at most 2 fallback
lines and no empty reply on the last request. Otherwise the rental stops with DEV-FAIL before any panel run and the
thread diagnoses on DEV (the F replies are readable). Why: LFM might write past guard333d's 140 words on all 4 samples
more often than MiniCPM does, which would show up as fallbacks.

## Judging (JUDGE-k1f.md)
Every arm's reply to the last request, shuffled together by the runner's --score step (seed 3822), cut to one line
per distinct reply to each item by claude_k1f_score.py --dedupe (seed 3824, ids F....). Judges 1 and 2 (blind Opus
agents, private folders, chunks of at most 150 lines) judge every line; judge 3 decides the lines they split on
(useful, or made-up >= 1). Keys applied by scripts/claude_k1f_score.py. A blind recount by a separate agent before
anything is reported.

## Marks for k1f (F vs K over all 100 items; PASS = all three)
| Mark | What | Bar |
|---|---|---|
| K1f.1 | useful, F - K; and a one-sided exact sign test on the items where exactly one of F, K is useful | >= +8 and p <= 0.05 |
| K1f.2 | replies with a made-up fact about the user, F vs K | F <= K + 4 |
| K1f.3 | fallback lines on the last request, F vs K | F <= K + 2 |

## The K1 line (the owner problem's bar; registered, its own verdict, reported beside k1f)
F useful on >= 60 of 100 AND F >= T, F >= Q and F >= L on useful.

## 0.2d's K1 row as a dry run (registered readings, not part of the k1f verdict)
For F and for K: claude_k1rival_score.score (sealed for 0.2d, 6fdf00563) on this panel: per rival T, Q, L the
reading ("behind" / "level" / "ahead", one-sided exact sign test at p <= 0.05) and the made-up margin (build <= rival
+ 3); the row passes when all three pass.

## Report only
F - K on lead, no-lead and uses_facts items; F vs L (the same model on our writer vs on the plain recipe): difference,
items only one side got, reading; per arm: made-up, fallbacks, empty replies, bare list endings, median words.

## Expected before running (from k1c's counts; nothing about LFM in our writer has been measured)
On k1c's 160 items K was useful on 29% and plain L on 64%. If F keeps most of L's lead on a fresh panel of the same
recipe: F about 50 to 65 of 100, K about 25 to 35, F - K about +20 to +35, and K1f.1 passes in most draws. K1f.3 is the
mark most at risk (the 140-word guard; see the DEV gate). The K1 line needs F >= Q too; Q led L by 11 of 160 in k1c,
so the K1 line and 0.2d's row against Q may still fail even if k1f passes.

## What would prove it wrong
F - K < +8, or F-only items not clearly more than K-only items: the k1c gap came from the plain recipe (greedy
decoding, the twin's system line, no guards), not from the model. Then the F vs L reading says which: F well below L
means our prompt, sampling or guards cost LFM its lead.

## After the verdict
- PASS: tell the Thread manager (for Ben) and Month-end: 0.2d's creative writer can be install_creative_k1f, with
  LFM2.5-1.2B-Instruct as a second small model loaded for creative turns only. It joins 0.2d only with Ben's yes.
- FAIL: read F's DEV replies and the F vs L reading to find where it loses; the next single change is sealed before
  any run.
