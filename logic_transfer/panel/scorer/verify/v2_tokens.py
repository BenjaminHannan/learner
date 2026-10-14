# Own check of the word-pointer geometry: what the scorer reads (word_spans text at pointer) vs what the loss rewards (progparse gold set).
import json, collections, sys
from custom_io.data import word_spans, MAX_PROMPT, ASCII
from custom_io.models import progparse as pp
E='/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/lt2/rows/eval/'
res={}
for f in ['logic_gate','logic_dev','logic_test_sampler','logic_test_deeper','placebo_dev','placebo_test_wording']:
    rows=[json.loads(l) for l in open(E+f+'.jsonl')]
    sizes=collections.Counter(); wm=0; nonascii=0; longp=0; mode=collections.Counter()
    oracle_ok=0; ptr_in_q=collections.Counter(); sufpos_ok=0
    for r in rows:
        p=r['prompt']; sp=word_spans(p); wm=max(wm,len(sp))
        nonascii+= any(c not in ASCII for c in p); longp+= len(p)>MAX_PROMPT
        toks=[p[a:b] for a,b in sp]
        # suffix = last 5 tokens '(' w '/' w '/' w ')'  -> option tokens at -6,-4,-2
        sufidx=[len(toks)-6,len(toks)-4,len(toks)-2]
        opts=[toks[i] for i in sufidx]
        if opts==[t for t in p[p.rindex('(')+1:-1].split('/')]: sufpos_ok+=1
        t=pp.row_targets(r); mode[t['mode']]+=1
        gs=t['word']; nq=sum(1 for i in gs if i not in sufidx)
        ptr_in_q[nq]+=1
        # oracle: point at any gold-set pos -> text -> norm hit
        i=gs[0] if gs else None
        if i is not None and toks[i].strip().lower()==r['answer']: oracle_ok+=1
    res[f]=dict(n=len(rows),max_word_tokens=wm,nonascii_rows=nonascii,rows_over_208=longp,suffix_tokens_equal_option_words=sufpos_ok,
        target_mode_counts=dict(mode),gold_set_extra_positions_in_question=dict(ptr_in_q),oracle_goldset_first_ok=oracle_ok)
print(json.dumps(res,indent=1))
