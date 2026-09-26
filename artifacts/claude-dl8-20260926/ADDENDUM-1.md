# dl-8 Addendum 1 (written 2026-09-26T18:58:21Z, before dl-7b or dl-8 reported; asked by the Thread manager 19:00 UTC)

Question: if dl-7b (replay of the base's shakiest facts, KL anchor) passes first, does dl-8 still test something the
next build needs, or should dl-8 run on top of dl-7b's recipe?

Decision, fixed now: dl-8 runs as sealed (on dl-2's plain night), whatever dl-7b shows.
- The two tests pull different levers. dl-7b protects old facts during the night (the forgetting side); dl-8 picks
  which new rows are practised (the cost side: half the training, same learning?). A pass on one does not answer the
  other.
- Running dl-8 on top of dl-7b would make it two changes from dl-2 at once, so a result could not be pinned on the
  row choice (one change per experiment).
Next build after both verdicts (rule fixed now, not after seeing results):
- both PASS: a new numbered test combines them (dl-7b's anchor + dl-8's E rows) against dl-7b alone, with its own marks;
  the joined build waits for that result.
- only dl-7b PASS: the build uses dl-7b's recipe with every row (S).
- only dl-8 PASS: the build uses E rows without the anchor, and forgetting stays open (next: EWC per-weight guard).
- neither: EWC per-weight guard next (dl-7 PASSMARKS Addendum 1 fallback order).
