# ch12 notes: "Built or planned, not yet proven" (Part 12 of 14, accent untested)

16 scenes, 596 s (audit minimum, 0 flags). The brief asked 300-380 s and the continuation task asked for about 400 s. I kept ~596 s on purpose: the project owner's relayed request was that the chapter "should also have all the information I want", the guide (sec. 11) says longer is welcome, and every brief cluster A-H is covered. If a shorter cut is wanted, the cheapest cuts are: s03 tape detail, s07 ST1 practice half, s09 band/even labels, s15 (merge into s16).

## SOURCES READ (paths under PFS = project-files snapshot)
- architecture/FINISHED-MODEL-2026-10-09.md sec. 4 (B3 groups, table), sec. 6 (Being tested / Not in run-1): decided status of every idea.
- sources/pr-56-b3-group1-and-token-test.md and architecture/B3-GROUP1-BUILD-2026-10-09.md sec. 0, 3, 9: two real switches (eg_embed, any_round), tape of 16, 0-2 extra rounds in 1 row of 4.
- big-run/PLAN.md sec. 5 (marks B3-1 and B3-5, lines 219-229), REPLAN path lines 39-46: marks and order (dates removed).
- architecture/B3-GROUP2-BUILD-2026-10-09.md, no-hardcoding/INVENTORY-B3-2026-10-09.md: counts 0/2/6/4/6, learned writer, L1, ST1.
- architecture/EXPERTS-TEST-2026-10-09.md lines 10, 14, 32, 76, 108-110, 125, 166-167: dead old experts, 52x154, balance, even share 1/52 (about 1.9%), Mac 25.0 s per update, about 6.9 days.
- architecture/TOKENS-EXPERIMENT-2026-10-09.md: 3.08 / 4.27 letters per token, TK / TKN, earlier loss 3.1 and 5.4.
- architecture/running-summary-2026-10-08.md, important-links-2026-10-09.md: long-text plan.
- sources/pr-58-domain-mode.md, domain-mode/DESIGN-AND-MARKS-2026-10-09.md (sec. 1, 2, 5 and addendum A10): domain mode.
- creative-roadmap/creative-roadmap-2026-10-06.md: plans in s15. Consistency: dossiers ch12-B.md.

## NUMBERS I COMPUTED
- 8 x 154 = 1,232 (s08). The source also states 1,232; the caption shows the multiplication.
- Near marker in s14 sits at 3.33 + 30 = 33.33 on the 0-100 bar (the mark was a gain of 30 points; our addition for the dashed marker only).
- Everything else is quoted: 1,228; 52; 154; 10,553,929; 3,579,225; 3,544,913; 3.08; 4.27; 3.1; 5.4; 0.49; 1.9 percent; 25.0 s; 6.9 days; 11.7 -> about 74; 3.33 -> 2.86; 1.07 -> 0.36; counts 0/2/6/4/6; toy 100.0 / 99.0 / 99.8; marks +3.0, +1.0, 10 points, 20 points, 1.0 point, +30.
- "about 74" is the source's pooled own-quiz value (74.22, 75.78, 73.83 in the last nights); the bar shows ~74.
- "3 to 4 times cheaper" is the spec's own wording for the thinker's reading only.

## DISAGREEMENTS between sources and what the video shows
- PR #56 body and spec sec. 0 say "four switches"; the code has two (eg_embed, any_round). The video shows two real switches and two non-switches (2,000 letters from the settings file, stop always on). Newer PR "After" wording wins.
- Domain mode: PR #58 body / brief say the first run is "running" and give 4.67 / 2.50; newer addendum A10 says it ran and DM1 was proved wrong (seed 200). The video uses A10: 3.33 -> 2.86 near, 1.07 -> 0.36 far (7 trainable kinds).
- Tokens: the older test lost 3.1 and 5.4 points; the source does not say these are "two copies", so the video does not call them copies.
- Input length: group 1 uses 2,000 letters (caps_b3); the tested G1 keeps 280 (ch03 s07). s01/s02 say 2,000 for the new build only.
- Brief says grey = plan; glossary says grey = placeholder. Plans use S.chip('placeholder',{label:'plan only'}).
- Brief said the 3M expert width "old 1,228" = 4.8 x width 256 (the 3M thinker); ch04 counts the 100M thinker at width 512. The video says "at the 3 million size".
- Plan dates in PLAN.md are not shown anywhere ("Dates are not promised").

## STATUS CHIPS
Amber (built, never tested): s02-s11, s13, s05 (counted in code only). Grey (plan): s12, s15, s16. The only green chips: domain mode "run once, not passed" in s01 and s14 (a result file exists, and it failed).

## ILLUSTRATIONS (tagged on screen "picture only" or "made-up example")
s03 round/tape picture (from the build's own test plan); s04 mark bar (marks, not a result); s06 Tom's apples; s07 which of the 4 tries pass; s08 which 8 experts are picked; s09 bar heights (random, not measured picks); s10 the word-piece grouping; s12 pieces and notes; s13 the loop. s02 toggles and the one-at-a-time arrow are also illustrative (the bisect plan).

## OPEN QUESTIONS
- s13: which loop steps are built is only partly stated in the design file; boxes use neutral borders and the chip says "partly built, one run".
- s06 toy numbers (100.0 / 99.0 / 99.8) are the build thread's own small code check on made-up rows, quoted from PLAN.md; not rerun.

## KIT REQUESTS
- S.hbars has no prefix option (needed "~74"); I wrote a local row/bar helper in s14.
- No kit dashed line or toggle; built from S.card.

## For the next chapter's author
Terms introduced here: experts, router, switch, caps file ("settings file" on screen), tape of 16, domain mode.
