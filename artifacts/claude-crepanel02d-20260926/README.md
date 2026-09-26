# crepanel02d: the sealed creative panel for 0.2d row K1 (Creative answers in chat thread, written 2026-09-26 16:54 UTC)

TEST-ONLY. Written for Month-end's 0.2d, where K1 is a no-harm row against plain same-size models (Month-end accepted
the bar at 16:31 UTC 09-26 and fixes it in a dated 0.2d addendum). Never run before 0.2d.

## How it was made (nobody who builds the model read an item)
- A separate agent wrote 100 items blind from the 382 creative spec, with the same recipe as k1cpanel: 35 idea with
  1 lead-in turn, 35 idea with none, 30 uses_facts with 1, 2 or 3 teach turns (10 each). Ids kd-001..kd-100.
- A third agent audited it blind (creative/AUDIT.md, counts only). It changed 49 items that were near-copies of an
  item in the DEV set, k1apanel or k1cpanel (14, 18 and 22 matches; 5 items matched two sets), keeping kinds and turn
  counts. No other spec check failed.
- Escrow: /mnt/project-files/escrow-k1-02d/creative/. The audited items_v2.jsonl was copied unread to
  creative/items.jsonl here and sealed in SEAL.sha256.txt (sha256 503bcd52...0535).

## How it is scored (scripts/claude_k1rival_score.py, main 6fdf00563, selftest 4/4)
Arms, each run once with scripts/claude_panel382_run.py --panel creative (fresh agent per item, per-turn seeds): the
joined build, and plain T MiniCPM5-1B @87179e5c, Q Qwen3.5-2B @15852e8c16360a2fea060d615a32b45270f8a8fc and
L LFM2.5-1.2B-Instruct @0f604ada3f766f9f257460c4c9f0b5d6f69d431b on the plain twin recipe
(scripts/claude_e2e336_twinb.py via claude_twinb_wrap.py), downloaded on the rental. Then the runner's --score, then
claude_k1rival_score.py --dedupe (one line per distinct reply to an item, ids D...., seed 3824). Blind Opus judges 1
and 2 judge every line with artifacts/claude-k1c-20260926/JUDGE-k1c.md word for word; judge 3 decides the lines they
split on; a blind recount by a separate agent before anything is reported.

## The bar (Month-end's, accepted as proposed)
Against each of T, Q and L: the build is not "behind" on useful replies (one-sided exact sign test on the items only
one side got, p <= 0.05 in the rival's favour), and the build's replies with a made-up fact about the user are at most
the rival's + 3. The row passes when all three pass. "Ahead" (p <= 0.05 in the build's favour) is reported as the
stronger claim. The K1 60% line (build useful on >= 60 of 100 and >= T) is reported beside it.
