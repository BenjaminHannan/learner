# Pre-maze adaptation correction

Written 2026-09-27 22:46 UTC, after the source-training processes began and **before any maze adaptation or maze panel score**.

Reviewing xfer-1 trial diffs 0003 and 0004 showed that the kept Adapter retains its 50-update linear AdamW learning-rate warm-up. The initial fewex harness copied its four deep-supervision updates and omitted the warm-up. The baseline Learner now applies that same 50-update warm-up for both loop and plain maze adaptation, and for each fixed sleep branch. The loop still uses four updates, three free rounds plus two gradient rounds, and no maze stop-head loss; plain still gets four updates per batch. The source-training code path, panels, ladder, marks, and all seeds are unchanged. Source training was still in progress; no source result or maze panel score had been viewed when this correction was made.

This addendum and the one-line scheduler change must be committed and pushed before starting adaptation. Use the new harness commit hash as the execution seal, and retain the original pass-mark seal commit in RESULTS.md.
