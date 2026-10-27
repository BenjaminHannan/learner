# PASSMARKS k1c: the 1B picks among its own 4 drafts (Creative answers in chat thread, written 2026-09-26 16:25 UTC)

Fixed before any registered run. Sealed in SEAL.sha256.txt with the code, the judge instructions and both panels'
seals. Registered FAILs stay FAILs.

## Why
k1a PASSED (VERIFY-k1a.md: the creative writer that sees the chat was useful on 20 of 40 lead items vs 7), but K1
is still open: k1a useful on 28 of 60, plain MiniCPM5-1B 24, bar 36. On the 40 DEV practice chats
(artifacts/claude-k1a-dev-20260926, readable) the k1a writer's first passing draft was useful 12 times, while at least
one of its 4 drafts was useful 26 times (blind judges, two plus a third on splits). So most of the loss is in which
draft is kept, not in what the 1B can write.

Brain picture (Ben 16:05, "how does the brain do this?"; textbook-level, inferred, not checked here): people
drafting a reply hold a few candidates and keep the one that fits the conversation best; the fit is judged by the
same system that produced them, not by a separate rulebook. Here the "fit" is the 1B's own reading of how much each
draft depends on this conversation. No training, no hand-written rules (Ben's Redirect, 16:04): a regex that counted
list items and poem lines did better on DEV (17 of 40) and is dropped for that reason.

## The single change
k1c, scripts/claude_k1c_cre.py (build_null_k1c_k): the k1a writer draws the same 4 samples (same generate call, same
random draws), trims and guards them exactly as k1a does, and among the drafts that pass the guards keeps the one with
the largest pointwise information under its own 1B: the mean over the draft's tokens of
log p(token | the writer's prompt) - log p(token | the system line and an empty user message). Ties go to the earliest
draw. Nothing else changes: routing, prompt, samples, guards, fallback, adapter, no notebook writes.
Tests: scripts/claude_k1c_test.py (7/7). Integration check on DEV (CPU, the real 1B, the writer function against the
pilot's own picks): the earlier version with the regex form rule returned the pilot's pick on all 40 items; the same
check of this model-only version was still running when this file was sealed, and its count goes in VERIFY-k1c.md.

## Arms (one rental; runner scripts/claude_panel382_run.py unchanged; per-turn seeds identical in C and K)
- K = claude_k1a_cre:build_null_k1a (k1a as registered: 0.2c's build with the k1a writer, NullReader, per-turn seeds,
  SLEEP02C_ADAPTER = 0.2c's adapter02c.pt, sha256 a33211dc...36f5). The base.
- C = claude_k1c_cre:build_null_k1c_k = K with the k1c pick. Registered (marks K1c).
- T = plain MiniCPM5-1B @87179e5c, Q = plain Qwen3.5-2B @15852e8c16360a2fea060d615a32b45270f8a8fc,
  L = plain LFM2.5-1.2B-Instruct @0f604ada3f766f9f257460c4c9f0b5d6f69d431b. All three on the plain twin recipe
  (scripts/claude_e2e336_twinb.py: its fair system line, the whole chat, thinking off, greedy, at most 160 new
  tokens), the same recipe as everyday chat's C1 rivals. Where the rivals' replies come from: the rental downloads
  Qwen and LFM at those pinned snapshots (Benchmarks' pins; Ben approved both rivals 02:12 UTC 2026-09-25) and runs
  them there; nothing comes from BensPC's copies.

## Panels (both TEST-ONLY, never read by the builder)
- A = k1cpanel, artifacts/claude-k1cpanel-20260926/creative (100 fresh items, sealed fa6f32a87: 35 idea with 1
  lead-in turn, 35 idea with none, 30 uses_facts with 1, 2 or 3 teach turns). Never run before.
- B = k1apanel, artifacts/claude-k1apanel-20260926/creative (the 60 items k1a ran on; 40 with earlier turns). k1c was
  designed on DEV only; nothing from k1apanel but k1a's aggregate counts has been seen. Used again for power: on 100
  items alone the chance of passing K1c.1 at DEV's rates is about 32%; on 160 about 46%.
All 160 items count in every mark. Every arm is re-run on both panels in this rental (no reply from the k1a run is
reused).

## Judging (JUDGE-k1c.md)
Per panel, every arm's reply to the last request, shuffled together by the runner's --score step (seed 3822), cut to
one line per distinct reply to each item by claude_k1c_score.py --dedupe (seed 3824, ids A.... and B....): C and K
share a verdict wherever they wrote the same reply. Judges 1 and 2 (blind Opus agents, private folders) judge every
line of both packets; judge 3 decides the lines they split on (useful, or made-up >= 1). Keys applied by
scripts/claude_k1c_score.py. A blind recount by a separate agent before anything is reported.

## Marks for k1c (C vs K over all 160 items; PASS = all three)
| Mark | What | Bar |
|---|---|---|
| K1c.1 | useful, C - K; and a one-sided exact sign test on the items where exactly one of C, K is useful | >= +8 and p <= 0.05 |
| K1c.2 | replies with a made-up fact about the user, C vs K | C <= K + 4 |
| K1c.3 | fallback lines on the last request, C vs K | C <= K + 2 |

## The K1 line (the owner problem's bar; registered, its own verdict, reported beside k1c)
C useful on >= 96 of 160 (60%) AND C >= T, C >= Q and C >= L on useful over all 160.

## Against same-size plain models (registered readings, not part of the k1c verdict)
For C and for K against each of T, Q, L over all 160: useful difference, items only one side got, two-sided exact
sign test, and a reading "ahead" / "behind" (one-sided p <= 0.05 either way) or "level". Made-up counts per arm.

## Report only
C - K on panel A, panel B, lead items, no-lead items, uses_facts; how many of C's replies differ from K's; empty
replies, fallbacks and bare list endings per arm.

## Expected before running (DEV, 40 practice chats, k1a writer without the adapter)
First draft 12 of 40, the 1B's pick 15 (8 gained, 5 lost), any draft 26. At those rates on 160 items: C - K about
+12 (about 32 gained, 20 lost); K1c.1 passes about 46% of the time; if the pick does nothing it passes about 4% of
the time (simulation, 20000 draws). The adapter makes first drafts better (k1a run: 28 vs 21 of 60 without it), which
may leave less room. The K1 line is unlikely to be met (K was 28 of 60 and T 24; 96 of 160 needs a jump of ~20
points).

## What would prove it wrong
C - K <= 0 over 160 items, or K-only items >= C-only items: the 1B's own reading does not find the better draft.
Then the DEV result (+3 of 40) was noise, and picking needs a judge that knows what the user asked for.

## After the verdict
- PASS: tell Month-end that the 0.2d creative writer can be install_creative_k1c (k1a + the pick), one line.
- FAIL: the fallback, sealed separately while this runs (brain-first): the 1B is asked, as a listener, whether each
  draft does what the user asked, and the draft with the highest "yes" probability is kept (the brain's evaluation
  of its own candidates before speaking; no rules, no training). Piloted on the same 40 DEV chats only.
