# Plain baseline: scored question set equals D's (checked 2026-10-23)

Both D and the plain baseline enumerate questions with `learnlab.step1.read_questions(text, meta, split)` over the shard files
of a split directory (D inside `premonition.data._shard_questions`, called by `build_cache`; the plain baseline in
`v1.plain_baseline.read_shard`; dev shards are read with split "train" in both). D scores every question of its dev/validation
cache (`v1.run.make_eval_batches` -> `premonition.train.validate`); the baseline scores every question of the same shards, with
`step1.exact_match` on `step1.answer_text`, the same exact-match rule as `premonition.train.judge`.

Checked with `python -m v1.plain_equiv --root <root> --expect`, which builds D's own caches (`v1.dtrain.open_data`) and compares
question ids, in order, against the baseline's list. Result on the real data (box_build output: train shards 0-3, dev shards
380-399, validation; byte-identical to the committed build, hashes checked): dev 42,653 and validation 8,675 questions, ids equal
in order, matching PREREG. The same comparison runs on a tiny generated village in `v1/tests/test_plain_baseline.py`.
`final_dev.json` is written only after the scored counts equal 42,653 / 8,675 (the run raises otherwise). The `test` split is
never listed: `open_split` raises `SealedSplitError` for "test" and "test-*", and the equivalence check reads only dev/validation.
