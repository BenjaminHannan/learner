import sys, json, collections
sys.path.insert(0, sys.argv[1])
from custom_io.models import progtext as PT, tool
rows, fams = [], collections.Counter()
mx = dict(call=0, entry=0, answer=0)
long_ = collections.Counter()
for line in sys.stdin:
    r = json.loads(line)
    fams[r.get('family', '?')] += 1
    if not r.get('steps') and not r.get('program'):
        continue
    rows.append(r)
    s, _ = PT.steps_of(r, True)
    for x in s or ():
        mx['call'] = max(mx['call'], len(PT.text(x).encode()))
        mx['entry'] = max(mx['entry'], len(PT.entry(x).encode()))
        if len(PT.text(x).encode()) + 1 > 69: long_['writer_over'] += 1
        if len(PT.entry(x).encode()) > tool.LE: long_['tape_entry_over'] += 1
    mx['answer'] = max(mx['answer'], len(str(r.get('answer', '')).encode()))
rep = PT.report(rows, True)
print(json.dumps(dict(families_all=fams.most_common(), rows_with_steps=len(rows), maxlen=mx, LE=tool.LE, over=long_,
      all=rep['all'], per_family={f: {k: v for k, v in c.items() if k != 'reasons'} for f, c in rep.items() if f != 'all'}), indent=1))
