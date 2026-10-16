import json,collections,sys
A='/tmp/claude-0/-home-user/6e3fd48b-869d-5cdd-b158-7710e164d592/scratchpad/adv/'
rows=[json.loads(l) for l in open('/home/user/sk200k/dev/in_dist.jsonl')]
P=json.load(open(A+'parent.trace.json')); C=json.load(open(A+sys.argv[1]+'.trace.json'))
c2=collections.Counter(); byk=collections.defaultdict(collections.Counter)
for i in range(len(rows)):
    p,c=P[i],C[i]
    if not p['hit'] or c['hit']: continue
    pc=[tuple(x[:3]) for x in p['calls']]; cc=[tuple(x[:3]) for x in c['calls']]
    j=0
    while j<min(len(pc),len(cc)) and pc[j]==cc[j]: j+=1
    if pc==cc: k='calls identical -> answer/mode readout'
    elif j==len(pc) and len(cc)>len(pc): k='overrun: parent calls reproduced then extra calls' if pc else 'overrun from 0: calls where parent made none'
    elif j==len(cc) and len(cc)<len(pc): k='early stop (prefix right, too few calls)'
    else:
        x=cc[j] if j<len(cc) else None; y=pc[j]
        k='diverge at call %d: '%j + ('op' if x and x[0]!=y[0] else 'operand')
    c2[k]+=1; byk[k][rows[i]['family']]+=1
tot=sum(c2.values()); print('lost',tot)
for k,v in c2.most_common(): print(f'{v:5d} {100*v/tot:5.1f}%  {k}   top fams {byk[k].most_common(4)}')
