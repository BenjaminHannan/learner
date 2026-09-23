# Exp 271 PREDICTIONS (CPU-only diagnostic, sealed BEFORE any 271 computation)

Diagnostic, not a registered test: no panel is run, no new model calls, no PASS
is possible. Question: on the fresh 267 dev set, does ANY cutoff on the YES/NO
checker's score separate good ear frames from wrong ones?

Inputs (read-only, never edited): artifacts/claude-diag267-20260923/ (c1.json
per-frame p-values, score.json rows, earpreds267.json, checks/c1/manifest.json
with the 155 kept TEACH frames) and artifacts/claude-devset267-20260923/
dev.jsonl (gold, sha-checked against its SEAL before loading, as 267 did).
No earpanel* is opened. Nothing is tuned: there is no threshold to pick for a
bar, only a curve to report.

Method (frozen before the seal; CPU only, at most 4 parallel processes):
- Frames: the 155 kept TEACH frames in checks/c1/manifest.json, used as-is.
  Fidelity check (not tuning): single-frame S.match over all 155 reproduces
  267's C0 totals (90 hits / 65 wrong); any mismatch is reported, not fixed.
- Base label: 267's gold via its loader conversion + S.match with
  rel_ok_narrower (261b Ruling 1), imported read-only (never reimplemented).
  A frame matching a gold TEACH frame is good; else wrong; then the two
  brief-ordered relabels, each listed by frame id in the report for audit:
  (a) appositive-relative: normalized value equals the normalized subject of
  a DIFFERENT gold TEACH frame on the same turn, value non-empty, and the
  value appears as a case-insensitive substring in the turn text -> good
  (267's D-GOLD note: these are truly stated; the dev writer left them out
  of gold while the 264 panel counts them correct).
  (b) plural: turn family is plural_relative, frame relation is sibling-kind
  (sister/brother/sibling or a narrower word of sibling), a gold sibling-kind
  frame with a DIFFERENT value exists on that turn, and the frame value
  appears as a case-insensitive substring in the turn text -> good (the
  "A and B are my sisters" case: naming either true name counts).
  Normalization for (a)/(b) is the sealed scorer's own norm (case/space).
- Score: p(YES) from c1.json. AUC = Mann-Whitney P(p_good > p_wrong) with
  ties 0.5, computed by hand (no sklearn). AUC 0.5 = no separation.
- Cutoff grid: every distinct p value (kept = p >= t), plus t=0 (keep all)
  and t above max (keep none). Table: t, kept, kept-good, kept-wrong,
  wrongs-per-20-saved = kept_wrong/kept*20. Integer counts everywhere.
- Best cutoff: among t with kept > 0 and kept_wrong/kept <= 1/20 (0.05),
  maximize kept-good; ties -> fewer kept-wrong, then larger t. If no t
  qualifies, report NO QUALIFYING CUTOFF plus the closest t (min wrong
  rate; ties -> max kept-good). Also reported by family (counts + family
  AUC with n) at the same rule.

Basis (267 REPORT, published before this seal): C1 @0.25 held only 2 of 155
frames (both wrong: 1 stale p=0.04, 1 no-save p=0.001); only 7 frames sit
below p=0.5. Raw wrongs 63/153 saved; D-GOLD moves ~40 of them to good,
leaving ~23 non-relative wrongs; C1 removed 0 true frames.

## Numbered predictions

- P271.1 Relabeled totals over the 155 frames: good 126-137, wrong 18-29
  (40 D-GOLD frames move wrong->good; the plural fix moves 0-4 more).
- P271.2 Best-cutoff ROC AUC: 0.50-0.70. The checker is a near pass-through
  on this dev (only 7 frames below p=0.5), so the score carries at most a
  weak low-tail signal; AUC near 0.5 would mean no separation at all.
- P271.3 Best cutoff under "at most 1 wrong per 20 saved" (wrong/kept <=
  0.05): NO cutoff qualifies (predicted ~80%). At most 7 wrongs can sit
  below p=0.5 while ~13+ wrongs sit at high p mixed with goods, so every
  non-trivial cutoff keeps roughly 2-4 wrongs per 20 saved. Closest t ~= 0.5
  keeps ~145-150 frames with ~13-19 wrongs, losing ~0-3 good frames. If a
  cutoff does qualify, it keeps at most ~100 frames (loses a third of goods).
- P271.4 Wrong saves concentrate in typo_filler + stale_value +
  relation_trap (non-relative); plural_relative keeps ~0 wrongs after the
  plural fix; plain_teach keeps ~0-2 non-relative wrongs (rest is D-GOLD).
- P271.5 Family AUCs are noise (n per family <= ~76 frames, wrongs <= ~20):
  no family shows clean separation (all family AUCs predicted 0.45-0.75).
- P271.6 Falsifier: if any cutoff keeps >= 90% of good frames at <= 1 wrong
  per 20 saved, P271.3 is wrong and the report says so plainly.
