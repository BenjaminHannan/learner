"""Execution replay: run each found program on fresh inputs to make new prompts of the same rule. Everything comes from what the model saw that day
(Ben's rule 10-07: it must all run on its own while deployed): the new inputs are drawn from the inputs shown in the day's questions, a replayed example
is kept only if all its outputs fall within the range of outputs shown that day and are not all equal, and the prompt is the source question's own text
with its numbers swapped. No rule table, no test generator settings."""
import random
from creative import fewshot
from creative import programs as P


def experience(pool):
    """(inputs shown in the day's questions, smallest and largest output shown)."""
    xs, ys = set(), []
    for row in pool:
        p = fewshot.parse(row['prompt'])
        if p is None:
            continue
        xs.update(p['xs'] + [p['q']])
        ys += p['ys']
    return sorted(xs), min(ys), max(ys)


def reprompt(prompt, nums):
    """The prompt with its numbers (in order) replaced by nums."""
    spans = fewshot.parse(prompt)['spans']
    out, last = [], 0
    for (a, b), v in zip(spans, nums):
        out += [prompt[last:a], str(v)]
        last = b
    return ''.join(out) + prompt[last:]


def _value(t, x, q_slot):
    nums = [0] * P.N_NUM
    nums[q_slot] = x
    vals, valid = P.run(nums, t)
    return vals[t.ans] if valid[t.ans] else None


def replay_per_record(records, k, seed, inputs, lo, hi, arm='Y', tries=40):
    """k fresh prompts per record (keeps the records' own mix of rules)."""
    rng = random.Random(f'replay-rec|{seed}')
    out = []
    for r in records:
        tf = P.train_form(fewshot.record_try(r))
        p0 = fewshot.parse(r['prompt'])
        if tf is None or p0 is None:
            continue
        t, n_ex = P.Try.make(*tf), len(p0['xs'])
        made = 0
        for _ in range(tries * k):
            if made >= k:
                break
            xs = rng.sample(inputs, n_ex + 1)
            ys = [_value(t, x, p0['q_slot']) for x in xs]
            if None in ys or len(set(ys)) == 1 or min(ys) < lo or max(ys) > hi:
                continue
            nums = [v for x, y in zip(xs[:n_ex], ys[:n_ex]) for v in (x, y)] + [xs[n_ex]]
            row = {'id': f'{r["id"]}:{made}', 'prompt': reprompt(r['prompt'], nums)}
            if not fewshot.structure(fewshot.parse(row['prompt']), t)[0]:
                continue
            out.append(fewshot._record(row, t, arm, len(out)))
            made += 1
    return out
