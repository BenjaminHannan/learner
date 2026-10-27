#!/usr/bin/env python3
"""Union the sealed scorer's pairs with anonymous IDs for two fresh judges.
No training data, arm names, aggregate performance, or verdict is shown to judges.
Both readers use this same union and both judge files with the unchanged scorer.
"""
import argparse,hashlib,json,random,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from claude_lis319_fullclaim import key,load

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--dir',required=True);a=ap.parse_args();d=Path(a.dir)
    pairs={}
    for arm in ('old','new'):
        for row in load(d/f'pairs_panel_{arm}.jsonl'):
            pairs[key(row['id'],row['saved'],row['gold'])]=row
    ordered=sorted(pairs.items(),key=lambda x:x[0]);random.Random('lis320-blind-pair-order-v1').shuffle(ordered)
    dst=d/'blind_pairs.jsonl'
    with dst.open('x') as f:
        for i,(_,row) in enumerate(ordered):f.write(json.dumps(dict(row,pid=i),ensure_ascii=False)+'\n')
    seal=dict(pairs=len(ordered),sha256=hashlib.sha256(dst.read_bytes()).hexdigest(),judges_required=2)
    with (d/'BLIND-INPUT.json').open('x') as f:f.write(json.dumps(seal,indent=2)+'\n')
    print(json.dumps(seal))
if __name__=='__main__':main()
