"""Independent check: how well can a TARGET-BLIND policy do on tier P (k=3, distinct 2..40,
STRICT-solvable target 0..99, target not a given number, no 2-number shortcut)?
Intermediate and final results must be in 0..99 (UMAX=99) as in the math report."""
import itertools, collections
UMAX=99
def trajs(nums):
    # all ordered 2-call trajectories that use each number exactly once (structure-valid shape)
    out=[]
    for i,j in itertools.permutations(range(3),2):
        k=3-i-j
        for op1 in '+-':
            r1 = nums[i]+nums[j] if op1=='+' else nums[i]-nums[j]
            ok1 = 0<=r1<=UMAX
            for first_is_result in (True,False):
                for op2 in '+-':
                    a,b = (r1,nums[k]) if first_is_result else (nums[k],r1)
                    r2 = a+b if op2=='+' else a-b
                    ok2 = ok1 and 0<=r2<=UMAX
                    out.append((ok2, r2 if ok2 else None, (i,j,op1,first_is_result,op2)))
    return out  # 6*2*2*2 = 48
def signvec(nums, t):
    # sign vectors over sorted order that give t (with a valid ordering)
    pass
inst=[]
for nums in itertools.combinations(range(2,41),3):
    tr=trajs(nums)
    reach=collections.Counter(r for ok,r,_ in tr if ok)
    pair=set()
    for a,b in itertools.permutations(nums,2):
        for r in (a+b,a-b):
            if 0<=r<=UMAX: pair.add(r)
    for t,c in reach.items():
        if t in nums or t in pair: continue
        inst.append((nums,t,c,sum(1 for ok,_,_ in tr if ok)))
print('P-tier instances',len(inst))
# (a) structure-only uniform over the 48 shapes: p = c/48 ; (b) uniform over arithmetic-valid shapes: c/valid
import statistics
pa=[c/48 for _,_,c,_ in inst]; pb=[c/v for _,_,c,v in inst]
pk=lambda ps,k: sum(1-(1-p)**k for p in ps)/len(ps)
print('structure-only (48 shapes): mean p %.3f pass@1 %.3f pass@8 %.3f pass@32 %.3f'%(statistics.mean(pa),pk(pa,1),pk(pa,8),pk(pa,32)))
print('structure+valid arithmetic: mean p %.3f pass@8 %.3f pass@32 %.3f'%(statistics.mean(pb),pk(pb,8),pk(pb,32)))
# sign pattern over sorted numbers (small, mid, large); in k=3 STRICT the coefficient of each number is +/-1
cnt=collections.Counter()
for nums,t,c,v in inst:
    pats=set()
    for s in itertools.product((1,-1),repeat=3):
        if sum(si*x for si,x in zip(s,nums))==t: pats.add(s)
    for s in pats: cnt[s]+=1/len(pats)
tot=len(inst)
for s,n in cnt.most_common(): print('sign over (small,mid,large)',s,'share %.3f'%(n/tot))
