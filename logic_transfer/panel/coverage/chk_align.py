from common import *
import sys
bad=0; n=0
for name,p in list(EVAL.items())+[(k,v) for k,v in TRAIN.items()]:
    c=Counter(); 
    for i,r in enumerate(stream_jsonl(p)):
        if i>=20000: break
        body,opts=split_prompt(r['prompt'])
        ss=sentences(body)
        m=r['meta']
        ok = len(ss)==len(m['template_ids'])
        c['aligned' if ok else 'misaligned']+=1
        c['opts%d'%len(opts)]+=1
        # kind check: last tid must be Q
        c['lastQ' if m['template_ids'][-1].startswith('Q') else 'lastNotQ']+=1
        if len(ss)!=m['n_rules']+m['n_facts']+1: c['count_mismatch_prog']+=1
        if r['answer'] not in opts: c['ans_not_in_opts']+=1
        if r['answer']!=m['label']: c['ans!=label']+=1
        if r['accepted']!=[r['answer']]: c['accepted_diff']+=1
    print(name, dict(c))
