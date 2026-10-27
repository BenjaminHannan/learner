import os,re,sys,json,collections
ROOT='artifacts'
# 1) every path named in any seal/sha file anywhere in artifacts, scripts, design
sealed=set()
for base in ['artifacts','scripts','design','data']:
    for dp,dn,fn in os.walk(base):
        for f in fn:
            if re.search(r'(SEAL|seal|sha256|SHA256)',f) and f.endswith(('.txt','.sha256','.md','.json')) and os.path.getsize(os.path.join(dp,f))<5_000_000:
                try: txt=open(os.path.join(dp,f),errors='ignore').read()
                except: continue
                for m in re.finditer(r'[0-9a-f]{64}\s+\*?(\S+)',txt):
                    p=m.group(1).strip()
                    sealed.add(os.path.normpath(p))
                    sealed.add(os.path.normpath(os.path.join(dp,p)))
# 2) dialog roots = dirs holding inbox/ or outbox/ subdirs; work-ish dirs
cands=collections.OrderedDict()
def dsize(d):
    t=0;n=0;hit=[]
    for dp,dn,fn in os.walk(d):
        for f in fn:
            p=os.path.normpath(os.path.join(dp,f))
            try: t+=os.lstat(p).st_blocks*512; n+=1
            except: pass
            if p in sealed: hit.append(p)
    return t,n,hit
for dp,dn,fn in os.walk(ROOT):
    s=set(dn)
    if ('inbox' in s or 'outbox' in s) :
        cands[dp]=1; dn[:]=[]  # don't descend
tot=0;ntot=0;sealedhits=0;byexp=collections.Counter()
out=[]
for d in cands:
    t,n,hit=dsize(d)
    if hit: sealedhits+=1; continue
    tot+=t;ntot+=n;byexp[d.split('/')[1]]+=t; out.append(d)
print('dialog roots:',len(cands),'unsealed:',len(out),'with sealed files:',sealedhits,'size %.2f GB'%(tot/1e9),'files',ntot)
for k,v in byexp.most_common(12): print('  %.2f GB %s'%(v/1e9,k))
json.dump(out,open(sys.argv[1],'w'))
print('sealed paths known:',len(sealed))
