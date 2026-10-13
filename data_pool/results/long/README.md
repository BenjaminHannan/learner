# Long-chunk cloze pools (big-run REPLAN 10-09), 2026-10-09

Code: `data_pool/cloze_long.py` (imports `custom_io/g8a/cloze.py` from the 8a build branch `claude/project-thread-f1to6a`; not copied). Mix by word pieces (a default,
untested at training time): prompt ceiling 280 letters 80%, 700 7%, 1300 7%, 2000 6%. Built from the nested web slices (`web_slices_8a.tgz`, commit 3ebd488915), seed 400:

| slice | rows | pieces | of web budget | share by pieces 280/700/1300/2000 |
|---|---|---|---|---|
| rung3 | 167,478 | 11.70M | 12.4M (94.4%) | .826/.067/.060/.048 |
| rung10 | 500,582 | 35.05M | 37.2M (94.2%) | .825/.068/.061/.046 |
| rung30 | 1,664,488 | 116.41M | 117.8M (98.8%) | .826/.067/.061/.046 |

Rows of rung3 are a byte prefix of rung10's, and rung10's of rung30's (cmp). sha256 of the three row files (seed 400):
rung3 e2bd0bb38d3bba2de7e9f621f4619a38c76155df27e0a69467bb39f3ed5c2c67, rung10 c23c779fe4b5e46fc66818464b5894967030eff9472bda2593e2465acb01aa5b,
rung30 3c4ea24f956ce3ace1cc5bc849209c367a14df539f3c9c074115e9187e69acd6. Rebuild takes ~1 min (rung3) to ~4 min (rung30) on one CPU core.
Because rung3/rung10 slices were cut exactly to their budgets, their pieces fall 5.6-5.8% short of 12.4M/37.2M (builder tolerance is 6%): safer to feed the rung30 slice to every rung with `--max-pieces`.

Cap check against the pinned `caps_g.json` (addendum G), web cloze rows only (no torch here; same measures as `caps.measure`): longest prompt 2000 (cap 280), numbers 240 (cap 91),
words 727 (cap 208), answer 12 (cap 35). Rows over G's caps on rung30: prompt 91,279, words 33,637, numbers 28. So the caps must grow to at least max_prompt 2000, n_num 240, w_max 727 (own72 rows may raise them further; compute with `caps.py compute` on pool+dev); answer, n_reg, plain_target are unchanged.
