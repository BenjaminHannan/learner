"""Cap-hit counters (scorecard row 6, "no truncation"; roadmap sec. 4 "target 0"; 8a addenda E and G).

Every place in the code that can cut a training or evaluation case to fit a fixed size calls hit(name) before it cuts. The counters change nothing
in what the models compute. train.py prints them as {"event": "cap_hits", ...} at every evaluation, at the end, and once at the start (all 0).
A nonzero count means a row was cut, skipped or reduced to an answer-only row, and the run does not meet the no-truncation rule.

  prompt_over_max      prompt longer than data.MAX_PROMPT (data.Dataset asserts; counted for the evaluation paths that do not)
  answer_over_max      answer chars past data.MAX_ANS (the answer slots of Dataset / collate)
  numbers_over         prompt numbers past N_NUM (progparse.prompt_numbers, ledger.spans: the workspace has no slot for them)
  number_clipped       a prompt number above 10**18 (ledger.spans clips it)
  words_over           prompt words past W_MAX (ledger / tool / progparse word slots)
  steps_over           a program with more than N_RES steps (progparse._targets drops it: the row then trains answer-only, no program)
  gen_answer_over      a GEN answer longer than GEN_MAX letters (the register targets are cut)
  operand_cells_over   a calculator operand (tool.py, the outside calculator) with more than CELLS - 1 = 10 characters: cell_ids cuts it
  plain_target_over    a plain_tf_steps / plain_lm target longer than CAP + 12 characters
Counts are per distinct prompt / row id where the code caches (ledger.spans, progparse.row_targets), per call elsewhere.
"""
from collections import Counter

HITS = Counter()
NAMES = ('prompt_over_max', 'answer_over_max', 'numbers_over', 'number_clipped', 'words_over', 'steps_over', 'gen_answer_over', 'plain_target_over', 'operand_cells_over')


def hit(name, n=1):
    HITS[name] += n


def snapshot():
    d = {k: HITS.get(k, 0) for k in NAMES}
    d['total'] = sum(d.values())
    return d


def reset():
    HITS.clear()
