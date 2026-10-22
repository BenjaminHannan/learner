# Reads sample/10BT/000_00000.parquet (path hard-coded; run in the folder holding shard/ and all.npz). Per doc: token_count, int_score, reading grade, 13-gram hits.
import sys,json,re,time
sys.path.insert(0,'/home/user/learner/data_pool'); import overlap13 as O
import pyarrow.parquet as pq
from multiprocessing import Pool
by,_=O.load_index('all.npz')
def fk(text):
    sents=max(1,len(re.findall(r'[.!?]+(?:\s|$)',text))); ws=re.findall(r"[A-Za-z']+",text); n=max(1,len(ws))
    syl=sum(max(1,len(re.findall(r'[aeiouy]+',w.lower()))) for w in ws)
    return 0.39*n/sents+11.8*syl/n-15.59
def work(rows):
    out=[]
    for tx,tc,sc in rows:
        out.append((tc,sc,round(fk(tx),1),O.doc_hits(tx,by)))
    return out
def gen(pf):
    for b in pf.iter_batches(batch_size=1000,columns=['text','token_count','int_score']):
        d=b.to_pydict(); yield list(zip(d['text'],d['token_count'],d['int_score']))
if __name__=="__main__":
    pf=pq.ParquetFile('shard/000_00000.parquet'); t=time.time(); res=[]
    with Pool(4) as p:
        for i,ch in enumerate(p.imap(work,gen(pf),chunksize=1)):
            res+=ch
            if i%50==0: print(i,len(res),round(time.time()-t),flush=True)
    json.dump(res,open('shard_stats_full.json','w')); print('DONE',len(res),time.time()-t,flush=True)
