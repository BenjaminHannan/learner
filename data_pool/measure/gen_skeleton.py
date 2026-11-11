# Needs the same as gen_yield.py. Counts distinct passage skeletons (names and pool words masked). Run: python3 gen_skeleton.py 60000 12
import os, sys, json, random, re, collections
sys.path.insert(0, os.environ.get('B1_TEACH','/tmp/b1t/b1_teach')); import gen_english as G
G.fits = lambda texts: True
N=int(sys.argv[1]); kinds=int(sys.argv[2])
pool = set()
for L in (G.NOUNS, G.ADJS, G.PLACES, G.SURFACES, G.FEELINGS, G.PETS): pool |= {w.lower() for w in L}
r=random.Random(778); P=G.Pools("train", G.BLOCK_R6)
fl,nl=(G.FAMS,G.FAM_NAMES) if kinds==6 else (G.FAMS12,G.FAM_NAMES12)
def skel(s):
    s=re.sub(r"\b[A-Z][a-z]+\b", lambda m: "N" if m.start()>0 and s[max(0,m.start()-2):m.start()] not in (". ","! ","? ") else m.group(0), s)
    s=re.sub(r"[A-Za-z']+", lambda m: "w" if m.group(0).lower() in pool else m.group(0), s)
    return s
sk=collections.defaultdict(set); curve={}
for i in range(N):
    j=i%len(fl); fam,s,para,qs=fl[j](r,P); sk[nl[j]].add(skel(s))
    if i+1 in (10000,50000,100000,300000): curve[i+1]=sum(len(v) for v in sk.values())
print(json.dumps(dict(kinds=kinds,N=N,skeletons={k:len(v) for k,v in sk.items()},total=sum(len(v) for v in sk.values()),curve=curve),indent=1))
