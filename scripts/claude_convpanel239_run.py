"""Exp 239 conversation-panel runner (version-agnostic).

Runs every conversation of the sealed panel on an agent, each in its own fresh
workdir, and saves per-turn user / reply / stored triples. Does NOT grade.
Uses the same daemon plumbing as the scratchpad probe runner dialog_nb.py
(fable_marks123_all.load_agent / make_daemon, inbox->process_file->outbox),
but reads the notebook triples after EVERY turn instead of once per dialog.

usage: python -B scripts/claude_convpanel239_run.py --agent A.py --config C.json
         --out artifacts/claude-convpanel239-20260922/transcripts-<ver>
         [--panel ...panel.jsonl] [--work <scratch dir>]
Writes <out>.jsonl and <out>.md.
"""
import argparse, json, shutil, sys, time, traceback, tempfile
from pathlib import Path

sys.path.insert(0, 'scripts')
import fable_marks123_all as M
import fable_notebook_contract as C
import fable_loop90_agent as L90

ap = argparse.ArgumentParser()
ap.add_argument('--agent', required=True)
ap.add_argument('--config', required=True)
ap.add_argument('--out', required=True, help='output path without extension')
ap.add_argument('--panel', default='artifacts/claude-convpanel239-20260922/panel.jsonl')
ap.add_argument('--work', default=None, help='scratch dir for per-conversation workdirs')
a = ap.parse_args()

panel = [json.loads(l) for l in open(a.panel) if l.strip()]
work = Path(a.work or tempfile.mkdtemp(prefix='convpanel239-'))
work.mkdir(parents=True, exist_ok=True)
mod, dcls, _, _ = M.load_agent(a.agent)
base = M.load_base_cfg(a.config)


def triples(d, root):
    try:
        nb = d.loop.nb if hasattr(d, 'loop') else C.Notebook(root / 'notebook')
        return [list(x) for x in L90.notebook_triples(nb)], None
    except Exception as e:
        return None, f'{type(e).__name__}: {e}'


rows, t0 = [], time.time()
for conv in panel:
    root = work / conv['id']
    shutil.rmtree(root, ignore_errors=True); root.mkdir(parents=True)
    ct = time.time()
    try:
        d = M.make_daemon(dcls, base, root); init_err = None
    except Exception:
        d, init_err = None, traceback.format_exc(limit=3)
    for j, t in enumerate(conv['turns']):
        row = {'id': conv['id'], 'turn': j, 'user': t['user'], 'intent': t['intent'],
               'expect': t['expect'], 'reply': None, 'error': None, 'triples': None}
        if d is None:
            row['error'] = 'daemon init failed: ' + init_err
        else:
            try:
                f = root / 'inbox' / f'm{j:02d}.txt'; f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(t['user']); d.process_file(f)
                o = root / 'outbox' / f'm{j:02d}.txt'
                row['reply'] = o.read_text().strip() if o.exists() else None
                if not o.exists(): row['error'] = 'no outbox file'
            except Exception:
                row['error'] = traceback.format_exc(limit=3)
            row['triples'], terr = triples(d, root)
            if terr: row['triples_error'] = terr
        rows.append(row)
    print(f"{conv['id']} {len(conv['turns'])} turns {time.time()-ct:.1f}s", flush=True)

elapsed = time.time() - t0
out = Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
with open(str(out) + '.jsonl', 'w') as f:
    for r in rows: f.write(json.dumps(r, ensure_ascii=False) + '\n')

md = [f'# Conversation panel 239 transcripts — {out.name}', '',
      f'Agent: `{a.agent}`  ', f'Config: `{a.config}`  ', f'Panel: `{a.panel}`  ',
      f'Run time: {elapsed:.0f}s. Ungraded (TEST-ONLY).', '']
by = {}
for r in rows: by.setdefault(r['id'], []).append(r)
for conv in panel:
    md += [f"## {conv['id']} — {conv['persona']}", '']
    for r in by[conv['id']]:
        md.append(f"**{r['turn']+1}. User** ({r['intent']}): {r['user']}  ")
        rep = r['reply'] if r['reply'] else ('*(ERROR)* ' + r['error'].strip().splitlines()[-1] if r['error'] else '*(empty)*')
        md.append(f"**Reply:** {rep}  ")
        md.append(f"*Expect:* {r['expect']}")
        md.append('')
    last = by[conv['id']][-1].get('triples')
    md += [f"Stored triples at end: `{last}`", '']
open(str(out) + '.md', 'w').write('\n'.join(md))
n_empty = sum(1 for r in rows if not r['error'] and not r['reply'])
n_err = sum(1 for r in rows if r['error'])
print(f'DONE rows={len(rows)} empty={n_empty} errors={n_err} elapsed={elapsed:.0f}s work={work}')
