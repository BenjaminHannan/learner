# Answer-word scores of the six R2a replicas (replicas, not the measured originals)

Scorer: `answer_words.py` here (also `logic_transfer/answer_words.py` on branch `claude/lt2-r2a-replica`, commit after `b30cfc8d18`). Defined in MARKS-LT2 Addendum 11 section 4. CPU only, 3 to 4 seconds per run.

Per row of dev (386), newwords (205), hard (32): for each of true / false / unknown, the log-probability of that full answer through the model's own answer path: log P = logsumexp( log P(mode WORD) + log P(the prompt word), log P(mode GEN) + log P(the 9 parallel character registers write the word) ). On all 3,738 rows the model is in WORD mode (P = 1.000), so in practice the score is the softmax of the word pointer over the option words; the three candidates hold at least 0.90 of the mass on every row (mean 1.000).

Files: `<run>.jsonl` (one line per row: set, id, gold, greedy pred, mode, logp per word with the word-path and gen-path parts, p_mode, argmax) and `SUMMARY.json`.

Checks (Addendum 11 section 4, bar 98%): scorer argmax = greedy prediction on 3,738 of 3,738 rows (100%); greedy exact counts re-computed here equal the box's own final evals for every run and set (dev 265/253/250/255/242/251, hard 12/4/7/3/6/3 for s200-s1, s200-s2, s201-s1, s201-s2, s204-s1, s204-s2).

Rows: rebuilt locally from the sealed ladder build for rung 6; file hashes equal the sealed ones (dev b40b61e3, hard 3f91da10, newwords 6af2a481, train dfcd5d2c).

Reproduce: `PYTHONPATH=<repo> python3 -m logic_transfer.answer_words score --ckpt <run>/checkpoint.pt --rows dev=dev.jsonl --rows newwords=newwords.jsonl --rows hard=hard.jsonl --out OUT.jsonl`
