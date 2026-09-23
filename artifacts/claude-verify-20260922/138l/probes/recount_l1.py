import json,sys
R='artifacts/claude-merge138l-20260922/'
pred=json.load(open(R+'predicted_moves138l.json'))['L1']
P={(x['piece'],x['id']):x for x in pred}
tot={}
def units(p,a):
    d=json.load(open(f'{R}run/l1/l1-{p}-{a}.json'))
    u={}
    for c in d:
        if p=='226':
            for i,t in enumerate(c['turns']):
                if 'reply' not in t: continue
                u[f"{c['id']}.t{i}"]={'reply':t['reply'],'triples':t['triples'],'events_added':t['events_added']}
        else:
            u[c['id']]={'replies':c['replies'],'triples':c['triples'],'snap209':c.get('snap209'),'_intent':c['intent']}
    return u
for p in ['209','212','216','222','223','226']:
    o,k,l=units(p,'own'),units(p,'k'),units(p,'l')
    K=lambda x:{a:b for a,b in x.items() if a!='_intent'}
    same=[i for i in o if K(o[i])==K(l[i])]; diff=[i for i in o if K(o[i])!=K(l[i])]; intd=[i for i in o if o[i].get('_intent')!=l[i].get('_intent')]
    kl=[i for i in o if K(k[i])!=K(l[i])]
    predids={i for (pp,i) in P if pp==p}
    unpred=[i for i in diff if i not in predids]
    notseen=[i for i in predids if i not in diff]
    exact=[]; bad=[]
    for i in predids:
        e=P[(p,i)]['expect_l']
        if p=='226':
            ok = l[i]['reply']==e['reply'] and l[i]['triples']==e['stored'] and l[i]['events_added']==e['events_added']
        else:
            st = l[i].get('snap209',l[i]['triples']) if p=='209' else l[i]['triples']
            ok = l[i]['replies']==e['replies'] and st==e['stored']
        (exact if ok else bad).append(i)
        if P[(p,i)]['l_equals_k'] != (K(k[i])==K(l[i])): bad.append(i+'(l_equals_k claim wrong)')
    # stored-only diffs own vs l
    sk='triples'
    stdiff=[i for i in o if o[i].get(sk)!=l[i].get(sk)]
    print(p,'units',len(o),'same',len(same),'diff',len(diff),'unpred',unpred,'pred-not-seen',notseen,'pred exact',len(exact),'bad',bad,'k!=l',len(kl),'stored own!=l',stdiff,'intent-only own!=l',[i for i in intd if i not in diff])
