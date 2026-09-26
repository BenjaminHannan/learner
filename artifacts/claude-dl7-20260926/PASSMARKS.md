# dl-7: does a KL anchor on the base's shaky short facts stop the forgetting that copy-practice nights cause?
(Fix-sleep thread. Registered when this file is committed, before any run. Code: scripts/claude_dl7_fragile.py; its
docstring is the method. Reuses claude_dl1_nights, dl-3's pool filter and scorer, and dl-4's anchor loss unchanged.)

## Why
- Copy-practice nights (dl-2, registered PASS) learn the day's work but lose 16-39 of the base's 200 right panel items
  by night 7. dl-3 (replay of greedy chat answers) and dl-4 (KL anchor on chat answers; KL fell about 5x) are registered
  FAILs, with losses still 20-36.
- fd-1 (report-only, artifacts/claude-fd1-20260926/RESULTS.md): 17 of the 29 items dl-4's nights lost were in the base's
  least confident third of right answers (the fixed bar was 60%; 58.6% missed it by one item, and the idea was not shown
  wrong). 19 of the 29 were capitals, and 17 of those 19 sat in the less confident half of the base's right capitals.
- Reading (suggested, not shown): nights knock over thin-margin facts; dl-4 anchored long chat replies, not facts.
- How the brain does it (Ben 16:05, brain first): sleep replays old memories alongside new ones, and weak memories get
  extra replay. dl-7 is that idea in one change: the old memories held back each night are the base's weakest facts.

## ONE change from dl-4's K arm: the anchor pool
Anchor items are short quiz questions the BASE wrote (two fixed asking prompts, sampled at temperature 1.0) plus the
BASE's own greedy answer (" Reply with the answer only." appended; finished within 16 tokens), kept only if the base's
confidence in its answer (smallest token probability among the first 4 answer tokens, fd-1's measure) is in the lowest
third of the pool. Questions touching the harm panel's topics are dropped with dl-3's panel_words filter (capitals,
every panel country and city, opposites, plurals, days, months, letters, counts, numbers; any digit). The harm panel is
never used to find, choose or train anchor items. Loss and schedule exactly as dl-4's K: KL(base || current) over the
vocabulary at every answer position (base = the same network with LoRA scale 0), weight 1.0, as many anchor items as
puzzle examples each night (a new random sample), shuffled with the puzzle examples through dl-2's loop (3 epochs,
lr 2e-4, batch 8, one growing LoRA r16 on q,k,v,o).
Arms: S = dl-2's night unchanged; F = S + the shaky-fact anchor. Seeds 12 and 13, 7 nights each. TEST seed 3290 (100
fresh puzzles x 20 guesses). Pool seed 3291, 3000 asks (CPU dev check: 60 asks gave 32 kept questions and 17 finished answers, so about 280 shaky items are expected). HARM: the same 300 items; "lost" = right at base, wrong now.

## Marks: dl-3's F1-F5, unchanged, with F in place of A
- F1 forgetting cut: F's night-7 lost <= 0.5 x S's (sums over seeds), and each F seed is below each S seed.
- F2 low forgetting every night: at most 1 of F's 14 nights has lost > 10.
- F3 still learns: F's night-7 lucky >= 2 x L0 on each seed, and F's gain over L0 >= 0.8 x S's gain.
- F4: at most 1 of F's 14 nights has TEST lucky more than 15% below the night before.
- F5: F's night-7 puzzles reached >= base, on each seed.
Verdict: PASS = F1-F5. INCONCLUSIVE if L0 < 10, or S's night-7 lost sum < 20, or the shaky pool holds fewer than 100
items. Proved wrong: F's night-7 lost >= S's on both seeds.

## Reported, not marked
Pool counts (asked, kept questions, answered, shaky, confidence cut); lost vs the night before; gained; KL per night;
lost by kind (capitals separately); lost by the base's confidence third on the panel (base_panel_conf, measured in the
run); the final night's replies on lost items (to see whether a lost item now names a wrong fact or breaks format).

## Limits stated before the run
One kind of day work (number puzzles). Two seeds (dl-3 saw 39 vs 24 lost under one rule). The shaky pool excludes
capitals entirely, so a pass means protection carried over to facts never rehearsed; a fail does not rule out
rehearsing the same kind of fact. The base's shaky answers may be wrong; the anchor keeps the base's distribution
either way, which is the point (keep, not sharpen).

## Addendum 1 (2026-09-26 16:15:40 UTC, after sealing at b15629064, before any run; the Thread manager's round-3 pushes)
- Premise status: SUGGESTED, not shown. fd-1 missed its own 60% bar (17 of 29 = 58.6%), and its capitals split was not
  in its plan. Premise check, report-only, fixed now: in dl-7's S arm, pool both seeds' night-7 lost items and count how
  many fall in the lowest third of base-right panel items by base_panel_conf (measured in this run). 60% or more =
  premise supported on fresh seeds; 40% or less = premise shown wrong, and then any F-arm result is not evidence for it.
- Anchor source (no panel contact): short quiz questions written by the base from two fixed prompts, filtered with
  dl-3's panel_words (every panel kind, country, city, word, and any digit dropped), answered greedily by the base,
  lowest-confidence third kept. The panel's items and kinds are never used to find, choose or train anchors; every lost
  item the marks count is a fact the nights never rehearsed.
- Brain framing: the brain's answer to forgetting is sleep that replays old memories mixed with new ones
  (complementary learning systems, simplified). dl-7 is a NARROWER version: it replays only the weakest old memories.
  The broad version has already run twice: dl-3 (greedy copies of base chat answers, FAIL) and dl-4 (matching the base's
  whole output distribution on a broad sample of base-written prompts, which is the "silicon" exact-replay idea, FAIL).
- Next fallbacks, one change each, in order: EWC per-weight guard (important weights get less plastic); broad exact
  replay at a higher dose (dl-4's anchor, weight 1 -> more anchor items per night) only if a reason appears why dl-4's
  dose was too low.
