"""F-E1: are wrong fresh English answers training answers? (marks fixed in design/info-paths/information-paths.md §4 before this ran)"""
import json,unicodedata,re,collections
def norm(s):
    s=unicodedata.normalize('NFC',s).lower().replace('’',"'").replace('‘',"'").strip()
    s=re.sub(r'[\s]+',' ',s); s=re.sub(r'[.!?,;:]+$','',s).strip(); return s
t=json.load(open('train.json'))
train=set(); words=set()
for e in t['examples']:
    for q in e['questions']:
        for a in [q['canonical_answer']]+q['accepted_answers']: train.add(norm(a))
    words|=set(norm(e['source_text']).replace(',',' ').replace('.',' ').split())
sc=json.load(open('scores.json'))
out={}
tot=collections.Counter()
for run,items in sc['items'].items():
    if 'parent' in run: continue
    c=collections.Counter()
    for it in items:
        o=it['normalized_output']; sub=it['subset']
        if it['correct']: c[sub,'right']+=1; c[sub,'right_is_train']+= o in train; continue
        c[sub,'wrong']+=1; c[sub,'wrong_is_train']+= o in train
        c[sub,'wrong_all_words_in_train_text']+= all(w in words for w in o.split()) if o else 0
    out[run]={f'{k[0]}:{k[1]}':v for k,v in sorted(c.items())}
    tot+=c
out['TOTAL']={f'{k[0]}:{k[1]}':v for k,v in sorted(tot.items())}
w=sum(v for k,v in tot.items() if k[1]=='wrong'); wt=sum(v for k,v in tot.items() if k[1]=='wrong_is_train')
out['share_wrong_equal_train_answer']=round(wt/w,3) if w else None
out['n_wrong']=w
out['subsets']=sorted({it['subset'] for items in sc['items'].values() for it in items})
print(json.dumps(out,indent=1))
