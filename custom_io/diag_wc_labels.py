"""Amendment 4 step 1 (MARKS-D0-T1-2026-10-07.md): the disclosure check, data only (no model, no checkpoint, no re-screen result).
For every gold call operand of the dev rows, compare write_copy's text label ("copied from an earlier result" = its text equals an earlier
call result) with progparse's gold slots (every slot holding that value: prompt numbers, constants, earlier results), per operand length 1-9;
and count the cases the new scorer keeps (UNAMBIGUOUS: the text equals exactly one earlier result and no prompt number or constant).
Answers the same way: NUM rows whose answer equals a call result.
python3 -m custom_io.diag_wc_labels --data DIR_WITH_dev/in_dist.jsonl [--out custom_io/results/WC-LABELS]"""
import argparse, hashlib, json, os
from custom_io.data import load_rows
from custom_io.evalx import subsample
from custom_io.models import progparse as pp

CONST_TXT = {str(c) for c in pp.CONSTS}


def unambiguous(x, results, prompt_nums):
    """The scorer's rule (text only): x equals exactly one of `results` and no prompt number or constant."""
    return sum(r == x for r in results) == 1 and x not in prompt_nums and x not in CONST_TXT


def count(rows):
    op, ans = {}, {}
    for r in rows:
        t = pp.row_targets(r)
        if not t['prog']:
            continue
        nums = pp.prompt_numbers(r['prompt'])
        pn = {m.group() for m in pp.NUM_RE.finditer(r['prompt'])}
        vals = nums + [None] * (pp.N_NUM - len(nums)) + pp.CONSTS + [s[3] for s in t['prog']]
        res = []
        for j, (o, ca, cb, v) in enumerate(t['prog']):
            for c in (ca, cb):
                x = str(vals[c[0]])
                kinds = {'p' if i < pp.N_NUM else 'c' if i < pp.R0 else 'r' for i in c}
                text_e = x in res
                d = op.setdefault(len(x.lstrip('-')), dict(n=0, text_result=0, gold_result_only=0, disagree=0, unambiguous=0, unamb_gold_not_one_result=0))
                d['n'] += 1
                d['text_result'] += text_e
                d['gold_result_only'] += kinds == {'r'}
                d['disagree'] += text_e and kinds != {'r'}
                u = unambiguous(x, res, pn)
                d['unambiguous'] += u
                d['unamb_gold_not_one_result'] += u and not (kinds == {'r'} and sum(i >= pp.R0 for i in c) == 1)
            res.append(str(v))
        if t['mode'] == 0 and r['answer'] in res:
            x = r['answer']
            d = ans.setdefault(len(x.lstrip('-')), dict(n=0, unambiguous=0, also_prompt_or_const=0, several_results=0))
            d['n'] += 1
            d['unambiguous'] += unambiguous(x, res, pn)
            d['also_prompt_or_const'] += x in pn or x in CONST_TXT
            d['several_results'] += sum(y == x for y in res) > 1
    return {k: dict(sorted(v.items())) for k, v in (('operand', op), ('answer', ans))}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--data', required=True)
    ap.add_argument('--out', default='custom_io/results/WC-LABELS')
    a = ap.parse_args(argv)
    path = os.path.join(a.data, 'dev', 'in_dist.jsonl')
    rows = load_rows(path)
    prows = [r for r in rows if pp.row_targets(r)['prog']]
    res = dict(in_dist=path, in_dist_sha256=hashlib.sha256(open(path, 'rb').read()).hexdigest(), n_rows=len(rows), n_prog=len(prows),
               all_program_rows=count(prows), write_copy_rows=count(prows if len(prows) <= 3000 else subsample(prows, 3000)))
    json.dump(res, open(a.out + '.json', 'w'), indent=1)
    L = ['# write_copy labels: text vs gold slots (Amendment 4 step 1; data only)', '',
         f"Dev file {path} (sha256 {res['in_dist_sha256'][:16]}), {len(rows)} rows, {len(prows)} with a gold program. Lengths are the gold operand's digits.",
         'text_result = its text equals an earlier call result (what write_copy labelled a copy); gold_result_only = every gold slot holding the value is a '
         'result; disagree = text says copy but a prompt number or constant also holds the value; unambiguous = the new rule (exactly one earlier result, '
         'no prompt number or constant); the last column must be 0 (the rule agrees with the gold slots).', '']
    for key, title in (('write_copy_rows', "The rows write_copy scores (3000 spread over the file)"), ('all_program_rows', 'All program rows')):
        L += [f'## {title}', '', '| digits | operands | text_result | gold_result_only | disagree | unambiguous | unamb. but gold not one result |',
              '|---|---|---|---|---|---|---|']
        for n, d in res[key]['operand'].items():
            L += [f"| {n} | {d['n']} | {d['text_result']} | {d['gold_result_only']} | {d['disagree']} | {d['unambiguous']} | {d['unamb_gold_not_one_result']} |"]
        L += ['', '| digits | answers = a call result | unambiguous | also a prompt number or constant | equals several results |', '|---|---|---|---|---|']
        for n, d in res[key]['answer'].items():
            L += [f"| {n} | {d['n']} | {d['unambiguous']} | {d['also_prompt_or_const']} | {d['several_results']} |"]
        L += ['']
    open(a.out + '.md', 'w').write('\n'.join(L) + '\n')
    print('\n'.join(L))
    return res


if __name__ == '__main__':
    main()
