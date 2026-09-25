from fractions import Fraction as F
from itertools import combinations_with_replacement as cwr
from functools import lru_cache
@lru_cache(None)
def reach(t):
    if len(t)==1: return {t[0]}
    out=set(); n=len(t)
    for i in range(n):
        for j in range(n):
            if i==j: continue
            a,b=t[i],t[j]; rest=[t[k] for k in range(n) if k not in (i,j)]
            vals={a+b,a-b,a*b}
            if b!=0: vals.add(a/b)
            for v in vals: out |= reach(tuple(sorted(rest+[v])))
    return frozenset(out)
for lo,hi in [(1,13),(1,9),(1,10)]:
    hands=list(cwr(range(lo,hi+1),4)); s=sum(1 for h in hands if F(24) in reach(tuple(F(x) for x in h)))
    print(f"cards {lo}-{hi}: {len(hands)} hands, {s} solvable, {len(hands)-s} unsolvable")
