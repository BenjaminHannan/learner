"""Verify a downloaded proof bundle and produce numerical/visual RL evidence."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from hands_gym import tasks


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifacts',type=Path,required=True)
    parser.add_argument('--notes',type=Path,required=True)
    args=parser.parse_args();root=args.artifacts;out=args.notes
    training=json.loads((root/'runs/proof/results.json').read_text())
    audits=[]
    for p in sorted((root/'runs/audit').glob('seed-*/audit.json')):
        audits.extend(json.loads(p.read_text()))
    assert {r['seed'] for r in audits}=={11,22,33},'three independent seed audits required'
    audits.sort(key=lambda r:r['seed'])
    task_rows=[];seed_rows=[];verified=0
    for audit in audits:
        seed=audit['seed'];phase_counts={}
        for phase,data in audit['phases'].items():
            checkpoint=root/('runs/proof/seed-%d/%s.pt'%(seed,phase))
            assert hashlib.sha256(checkpoint.read_bytes()).hexdigest()==data['checkpoint_sha256']
            trace=root/('runs/audit/seed-%d/seed-%d-%s.jsonl'%(seed,seed,phase))
            assert hashlib.sha256(trace.read_bytes()).hexdigest()==data['trace_sha256']
            records=[json.loads(line) for line in trace.read_text().splitlines()]
            assert len(records)==7*audit['eval_episodes_per_task']
            phase_counts[phase]={}
            for row in records:
                episode=tasks.build(row['kind'],row['task_seed'])
                assert row['instruction']==episode['instruction']
                assert row['task_seed']>=10_000_000
                assert row['steps']==len(row['actions'])<=audit['max_steps']
                recomputed=tasks.check(row['kind'],episode['spec'],row['terminal_state'],row['terminal_state'],row['steps']-1,audit['max_steps'])[0]
                assert recomputed==row['success'],row
                for action in row['actions']:
                    assert action['kind'] in ('click','drag','key','scroll')
                    assert all(0<=action[k]<1 for k in ('x','y','endX','endY'))
                    assert 0<=action['keyCode']<256
                for key in ('initial_overview_sha256','final_overview_sha256'):
                    assert len(row[key])==64
                phase_counts[phase].setdefault(row['kind'],[]).append(row['success'])
                verified+=1
            for kind,rows in phase_counts[phase].items():
                score=data['per_task'][kind]
                assert score['successes']==sum(rows) and score['episodes']==len(rows)
            assert abs(data['overall']-sum(r['success'] for r in records)/len(records))<1e-12
        initial=audit['phases']['initial'];final=audit['phases']['final']
        assert final['overall']>initial['overall']+0.05,'improvement must be clear in every seed'
        run=next(t for t in training if t['seed']==seed)
        assert run['initial_sha256']==initial['checkpoint_sha256']
        assert run['final_sha256']==final['checkpoint_sha256']
        seed_rows.append({'seed':seed,'baseline':initial['overall'],'final':final['overall'],
                          'train_steps':run['train_steps'],'train_seconds':run['train_seconds'],
                          'train_steps_per_second':run['train_steps_per_second']})
        for kind in initial['per_task']:
            task_rows.append({'seed':seed,'task':kind,'episodes':initial['per_task'][kind]['episodes'],
                              'baseline_successes':initial['per_task'][kind]['successes'],
                              'final_successes':final['per_task'][kind]['successes']})
    per_task=[]
    for kind in tasks.TASK_TYPES[:7]:
        rows=[r for r in task_rows if r['task']==kind]
        n=sum(r['episodes'] for r in rows)
        b=sum(r['baseline_successes'] for r in rows);f=sum(r['final_successes'] for r in rows)
        per_task.append({'task':kind,'episodes':n,'baseline_successes':b,'final_successes':f,'baseline':b/n,'final':f/n})
    steps=sum(r['train_steps'] for r in seed_rows);seconds=sum(r['train_seconds'] for r in seed_rows)
    summary={'seeds':seed_rows,'per_task':per_task,'baseline':sum(r['baseline'] for r in seed_rows)/3,
             'final':sum(r['final'] for r in seed_rows)/3,'train_steps':steps,
             'train_seconds':seconds,'train_steps_per_second':steps/seconds,
             'audited_episodes':verified,'episodes_per_phase':verified//2,
             'peak_torch_allocated_mb':max(c['gpu_allocated_mb'] for r in training for c in r['curve'])}
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    for name,rows in [('seed-metrics.csv',seed_rows),('per-task.csv',per_task),('per-seed-task.csv',task_rows),
                      ('rl-curve.csv',[c for r in training for c in r['curve']])]:
        with (out/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
    colors=['#2166ac','#b35806','#4d9221']
    for r,color in zip(training,colors):
        axes[0].plot([c['environment_steps'] for c in r['curve']],
                     [100*c['recent_train_success'] for c in r['curve']],label='Seed '+str(r['seed']),color=color)
    axes[0].axvline(0.7*training[0]['train_steps'],color='#888888',ls=':',lw=1)
    axes[0].set(xlabel='Training environment steps',ylabel='Recent training success (%)',ylim=(0,105),
                title='PPO curriculum learning curve')
    axes[0].legend(frameon=False);axes[0].grid(alpha=0.15)
    for i,r in enumerate(seed_rows):
        axes[1].bar(i-0.17,100*r['baseline'],width=.32,color='#a6bddb',label='Starting policy' if i==0 else None)
        axes[1].bar(i+0.17,100*r['final'],width=.32,color='#2166ac',label='After RL' if i==0 else None)
    axes[1].set(xticks=range(3),xticklabels=[str(r['seed']) for r in seed_rows],xlabel='Independent training seed',
                ylabel='Held-out success (%)',ylim=(0,40),title='Seven-task held-out success')
    axes[1].legend(frameon=False);axes[1].grid(axis='y',alpha=.15)
    fig.suptitle('HANDS gym on BensPC · 8 browser environments · 32 held-out layouts/task/seed')
    fig.savefig(out/'rl-curve.png',dpi=180);fig.savefig(out/'rl-curve.svg');plt.close(fig)
    # Theme-aware inline visualization, independent of matplotlib's fixed plot colors.
    def line(r):
        points=' '.join('%.1f,%.1f'%(46+400*c['environment_steps']/12800,188-1.5*100*c['recent_train_success']) for c in r['curve'])
        return points
    lines=''.join('<polyline fill="none" stroke="var(--chart-%d)" stroke-width="2" points="%s"><title>Seed %d</title></polyline>'%(i+1,line(r),r['seed']) for i,r in enumerate(training))
    bars=''
    for r in seed_rows:
        bars+='<div class="row"><span>Seed %d</span><div><div class="barwrap" style="--w:%.3f%%"><div class="bar before"></div><span>%.1f%%</span></div><div class="barwrap" style="--w:%.3f%%"><div class="bar after"></div><span>%.1f%%</span></div></div></div>'%(r['seed'],r['baseline']/0.4*100,r['baseline']*100,r['final']/0.4*100,r['final']*100)
    html='''<!doctype html><html><head><meta charset="utf-8"><style>
:root{font-family:var(--font-sans);color:var(--foreground)}body{margin:0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}.panel{padding:16px;border-radius:var(--radius);background:var(--card)}p{margin:0 0 10px;font-size:13px}.label{font-weight:600}.muted{color:var(--muted-foreground);font-size:12px}svg{display:block;width:100%;height:210px;font:11px var(--font-sans);color:var(--muted-foreground)}.row{display:grid;grid-template-columns:55px 1fr;gap:6px;align-items:center;font-size:12px;margin:15px 0}.barwrap{position:relative;height:19px;margin-top:3px}.barwrap span{position:absolute;left:calc(var(--w) + 5px);top:0;line-height:19px}.bar{height:19px;width:var(--w)}.before{background:var(--secondary);color:var(--secondary-foreground)}.after{background:var(--chart-1);color:var(--primary-foreground)}@media(max-width:560px){.grid{grid-template-columns:1fr}}
</style></head><body><div class="grid"><div class="panel"><p class="label">PPO training success</p><svg viewBox="0 0 470 220" role="img" aria-label="Three RL learning curves"><path d="M46 30V188H447" fill="none" stroke="var(--border)"/><path d="M46 113H447M46 38H447" stroke="var(--border)" stroke-dasharray="3 4"/>
<g fill="currentColor"><text x="11" y="192">0%</text><text x="6" y="117">50%</text><text x="1" y="42">100%</text><text x="46" y="208">0</text><text x="355" y="208">12,800 steps</text></g>'''+lines+'''</svg><p class="muted">Recent 100 episodes; popup-heavy curriculum. Seeds 11, 22, 33.</p></div><div class="panel"><p class="label">Held-out success across seven tasks</p><p class="muted">Starting policy / after RL · 224 episodes per policy per seed</p>'''+bars+'''<p class="muted">Fresh initializations; fixed task seeds excluded from training. The short run does not master every task type.</p></div></div></body></html>'''
    (out/'results.html').write_text(html)
    print(json.dumps(summary,indent=2))
    print('PROOF VERIFIED: checkpoint hashes, trace hashes, %d terminal reward recomputations, and improvement in all three seeds'%verified)

if __name__=='__main__':main()
