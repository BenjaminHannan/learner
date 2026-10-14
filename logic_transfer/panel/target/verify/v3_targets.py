import json, itertools
from custom_io.models import progparse as pp
SCR='/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows'
for f in ['logic_train','placebo_train']:
    rows=[json.loads(l) for l in itertools.islice(open(f'{SCR}/{f}.jsonl'),130000)]
    cov=pp.coverage(rows); print(f,cov['all'])
    del rows
for f in ['logic_dev','logic_gate','logic_test_sampler','logic_test_deeper','placebo_dev','placebo_test_wording']:
    rows=[json.loads(l) for l in open(f'{SCR}/eval/{f}.jsonl')]
    print(f,pp.coverage(rows)['all'])
