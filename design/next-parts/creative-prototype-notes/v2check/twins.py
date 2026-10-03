import itertools, collections
exec(open('blind.py').read().split("print('P-tier instances'")[0])
by=collections.defaultdict(list)
for nums,t,c,v in inst: by[nums].append(t)
n=len(by); multi=sum(1 for s in by.values() if len(s)>=2)
print('number sets with a P puzzle',n,'with >=2 targets',multi,'(%.1f%%)'%(100*multi/n))
# practice/T1 number-set overlap if split by canonical form (numbers+target): draw 1024 practice + 256 T1 at random
import random
random.seed(0); allinst=[(a,b) for a,b,_,_ in inst]; random.shuffle(allinst)
prac=allinst[:1024]; t1=allinst[1024+128:1024+128+256]
ps=set(a for a,_ in prac)
print('T1 puzzles sharing a number set with practice: %d of 256'%sum(1 for a,_ in t1 if a in ps))
