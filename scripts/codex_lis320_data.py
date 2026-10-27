#!/usr/bin/env python3
"""Build and seal lis-320 DATA only after all 6,000 seed-324 dialogs parse.
Only the registered seeder, cleaner, checks and builder determine training rows.
Prints counts, never text. Outputs are new files, not edits to any prior artifact.
"""
import argparse, collections, gzip, hashlib, json, subprocess, sys
from pathlib import Path
A=Path('artifacts/claude-lis320-20260926')
F=A/'full-luna'
SHA='9d17c5fe3e6171e0cb0ab87390d0144e325903de54200ef60f074302a29678d2'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return [json.loads(s) for s in p.read_text().splitlines() if s.strip()]
def call(script,*args,out=None):
    r=subprocess.run([sys.executable,'-B','scripts/'+script+'.py',*map(str,args)],capture_output=True)
    if out is not None:out.write_bytes(r.stdout)
    if r.returncode:raise RuntimeError(f'{script} exited {r.returncode}; counts/log retained locally')
    return r.stdout

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--outbox',required=True);ap.add_argument('--work',required=True);a=ap.parse_args()
    if (A/'DATA.md').exists() or (F/'final').exists():raise RuntimeError('DATA or final already exists; refusing overwrite')
    w=Path(a.work);w.mkdir(parents=True,exist_ok=False)
    for s in [A/'PASSMARKS.sha256.txt',*sorted(A.glob('SEAL-ADDENDA*.sha256.txt'))]:
        subprocess.run(['shasum','-a','256','-c',str(s)],check=True,stdout=subprocess.DEVNULL)
    call('claude_lis320_seed_cr','--seed',324,'--n',6000,'--ask-back','--avoid-names',A/'avoid_names_dev.txt','--avoid-hashes',A/'avoid_test.sha256','--out',w/'seeds.jsonl',out=w/'seed-counts.json')
    if digest(w/'seeds.jsonl')!=SHA:raise RuntimeError('changed seed hash')
    sys.path.insert(0,str(Path(__file__).resolve().parent))
    from codex_lis320_continue import summary
    joined=[];chunks=[]
    for k in range(1,101):
        base=str(F/f'chunk{k}')
        r=subprocess.run(['git','show',a.outbox+':'+base+'/RESULTS.md'],capture_output=True)
        if r.returncode:break
        d=summary(r.stdout.decode(),k)
        data=subprocess.check_output(['git','show',a.outbox+':'+base+'/raw.new.jsonl.gz'])
        rows=[json.loads(s) for s in gzip.decompress(data).splitlines() if s.strip()]
        if len(rows)!=int(d['new']):raise RuntimeError(f'chunk {k} count mismatch')
        joined.extend(rows);chunks.append(dict(chunk=k,sha256=hashlib.sha256(data).hexdigest(),**d))
    (w/'joined.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in joined))
    call('claude_lis320_resume_clean','--raw',w/'joined.jsonl','--out',w/'raw.jsonl',out=w/'resume.json')
    raw=load(w/'raw.jsonl');seeds=load(w/'seeds.jsonl')
    if len(raw)!=6000 or any(r.get('parsed') is None for r in raw) or {r['dialog_id'] for r in raw}!={r['dialog_id'] for r in seeds}:raise RuntimeError('not all 6000 seed dialogs have a parsed row')
    call('claude_lis320_rawcheck2','--raw',w/'raw.jsonl','--seeds',w/'seeds.jsonl','--models','gpt-6-luna',out=w/'rawcheck.json')
    call('claude_lis320_check_we3','--seeds',w/'seeds.jsonl','--raw',w/'raw.jsonl','--out',w/'kept.jsonl','--drops',w/'drops.jsonl',out=w/'check.json')
    call('claude_lis320_build','--kept',w/'kept.jsonl','--out',w/'data','--dev-pct',3,out=w/'BUILD.json')
    call('claude_lis320_style','--kept',w/'kept.jsonl','--out',w/'style.json')
    kept=load(w/'kept.jsonl');seeded=collections.Counter(t['intent'] for d in seeds for t in d['turns'])
    dialog_families=collections.Counter(f for d in seeds for f in {t['intent'] for t in d['turns']})
    ck=json.loads((w/'check.json').read_text());build=json.loads((w/'BUILD.json').read_text())
    if build['overlap_dialogs']!=0:raise RuntimeError('train/dev dialog overlap')
    hashes={p:digest(w/p) for p in ('seeds.jsonl','raw.jsonl','kept.jsonl','data/train.jsonl','data/dev.jsonl')}
    counts=dict(dialogs=6000,parsed=6000,writer='gpt-6-luna',temperature=None,
                seeded_by_family=dict(sorted(seeded.items())),kept_by_family=ck['kept_by_family'],
                dialogs_by_writer_and_family={'gpt-6-luna':dict(sorted(dialog_families.items()))},
                rows_by_writer={'gpt-6-luna':len(raw)},kept_by_writer={'gpt-6-luna':len(kept)},
                kept_by_writer_and_family={'gpt-6-luna':ck['kept_by_family']},
                recased=ck['counts'].get('recased',0),build=build,hashes=hashes,outbox=a.outbox,chunks=chunks)
    final=F/'final';final.mkdir()
    for name in ('seed-counts.json','resume.json','rawcheck.json','check.json','BUILD.json','style.json'):(final/name).write_bytes((w/name).read_bytes())
    (final/'COUNTS.json').write_text(json.dumps(counts,indent=2)+'\n')
    (final/'DATA-HASHES.json').write_text(json.dumps(hashes,indent=2)+'\n')
    # The original chunk files remain authoritative. No training-text file is added to a second corpus.
    stamp=subprocess.check_output(['date','-u','+%FT%TZ'],text=True).strip()
    table='\n'.join(f'| {f} | {seeded[f]} | {ck["kept_by_family"].get(f,0)} | {dialog_families[f]} |' for f in sorted(seeded))
    text=f'''# lis-320 DATA (sealed before training)

Written {stamp}. Source outbox: {a.outbox}. Seed: 324, 6,000 dialogs.

Shown: all 6,000 dialogs have one parsed row after the registered resume cleaner;
rawcheck2 is OK, writer GPT-6 Luna only, temperature null (route default).
No Claude-written or Claude-judged training rows or labels are used.
The legacy src tag `glm320` and style key `glm_kept` name the existing code format;
provenance is Luna. GLM contributes 0 dialogs and 0 kept turns.

Code-kept turns: {len(kept)}. Train: {build['train']} turns / {build['train_dialogs']} dialogs.
Dev: {build['dev']} turns / {build['dev_dialogs']} dialogs. Split: sealed builder, dev-pct 3.
Dialog overlap: 0. Existing code recased {counts['recased']} labels; no manual fixes.
Counts and all hashes are in full-luna/final/COUNTS.json. Chunk compressed hashes
pin the exact raw data. DATA-HASHES.json pins the reconstructed seeds, raw, kept,
train and dev bytes. The training job must reproduce and match every hash.

| Family | Seeded turns | Kept Luna turns | Luna dialogs containing family |
|---|---:|---:|---:|
{table}

A dialog can contain several families. Per-writer counts are in COUNTS.json.
Style versus DEV chats and bank: full-luna/final/style.json (report only).
Suggested: this meets the sealed data provenance and completion gates.
Untested: the trained reader and all readpanel320 marks.

Training remains MiniCPM5-1B revision 87179e5c1f455ef22e6223592d2d61351b525bfc,
LoRA rank 32, 2 epochs, lr 2e-4, batch 16, max-len 512, seed 300,
claude_lis319_common.build_prompt_hist; unchanged compiler, T=0.995.
'''
    with (A/'DATA.md').open('x') as f:f.write(text)
    paths=[A/'DATA.md',*sorted(final.iterdir())]
    with (A/'SEAL-DATA.sha256.txt').open('x') as f:
        for p in paths:f.write(digest(p)+'  '+str(p)+'\n')
    print(json.dumps({'data':'SEALED','dialogs':6000,'kept':len(kept),'train':build['train'],'dev':build['dev'],'outbox':a.outbox}))
if __name__=='__main__':main()
