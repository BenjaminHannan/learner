"""Bid C load gate (card sec. 2b, ACCEPTED in this three-check form). CPU only, bit-identical, no tolerance. Run it BEFORE any arm. On any fail it stops, writes the report and exits
non-zero; there is no retry and no patch-and-retry (--report is opened exclusively, so a failed report cannot be overwritten by a second try).

  python3 -m creative.bidc_load_gate run --c2b-parent B2_s200.pt --recorded C2B_RECORD --bidc-parent P0.pt --bidc-recorded P0_RECORD --report GATE.json
  python3 -m creative.bidc_load_gate record --ckpt B2_s200.pt --out C2B_RECORD --rows ROWS     # write a "reload" record of a checkpoint (check 1's C2b parent)
  python3 -m custom_io.train ... --caps custom_io/caps/caps-bidc.json --out P0DIR --record-eval P0_RECORD --record-rows ROWS --record-n 64     # P_0's own end-of-training record (check 3)

Exit codes: 0 PASS, 1 FAIL, 3 PARTIAL (not every check was run; not a pass), 4 REFUSED (the record was made on a different machine / torch / thread count: nothing was compared; make the record and run the gate on the same machine).

  1  caps plumbing   caps-old-defaults.json (max_ans 8, n_reg 9, N_PLACE 16) applied BEFORE load_parent; load the C2b parent; its eval on the fixed batch equals the recorded one.
  2  negative        caps-bidc.json applied, then load_parent on the same C2b parent MUST raise a shape error (reader.place.weight 16 rows vs 37). It loading is a FAIL: the caps were not
                     applied before the load. Any other error is also a FAIL.
  3  round trip      the Bid C parent P_0 (trained under caps-bidc.json) reloaded in a fresh process with the caps applied first reproduces its own end-of-training eval.
Every check runs in its own fresh process (the caps are module globals).

THE EVAL ("recorded"): on a fixed batch (the first --n rows, default 64, of --rows) one Ledger.run and one greedy sampler pass, in eval mode on CPU with one thread:
  right (greedy first try fits and equals the key, c2_pilot.greedy_eval), the decoded answers, the greedy program (ops / a / b / answer pointer / mode / values: long tensors) and the float
  tensors R, lmode, lans, lword and the step-1 logits (compared with torch.equal). A record is a .pt (the ONLY record format; a .json, e.g. a C2b results file, is refused outright: it carries no floats and no row ids of its own). It stores its own row ids, the sha256 of the rows
file it was made on and a "machine" block (see MACHINE), and has "source": "train_process" (custom_io/train.py --record-eval PATH: made by the training process from the in-memory model right
after training, with the sha256 of the checkpoint it saved; the only record check 3 accepts, because it is P_0's own END-OF-TRAINING eval) or "source": "reload" (the `record` command: a checkpoint
loaded from disk; the record check 1 uses for the C2b parent, refused by check 3 because a reload compared with a reload proves nothing about training). compare() checks the record's stored ids and
rows-file sha256 against the gate's rows, so a record made on other rows (e.g. the C2b TEST rows) is never compared with these.
NOTE --rows defaults to the first 64 rows of creative/data/c2/dev.jsonl (card addendum 1, A4): the opened C2 test is not re-read. Check 1's recorded side is therefore made once, from the actual
C2b parent with the unmodified code (`record`), on the machine that runs the gate; the committed C2b-test .json results cannot serve check 1.

MACHINE: bit-exact floats are only meaningful on one machine. Every record stores torch version, platform.platform(), platform.processor() / machine / CPU model / torch CPU capability, the torch thread
count it was made with and whether mkldnn / MKL are available. Checks 1 and 3 compare these with the gate's own BEFORE any bit-exact comparison; a mismatch is REFUSED (exit 4), not FAIL, with a message to
make the record and run the gate on the same machine. So P_0 must be trained (or at least its --record-eval made) on the machine that runs the gate (Bid C venue: BensPC), and the C2b parent's `record`
likewise. Moving a P_0 checkpoint is fine; moving its record is not.
"""
import argparse, hashlib, json, os, platform, subprocess, sys, time
import torch

TOK = 'GATE-RESULT '
REFUSED_CODE = 4                       # exit code of a REFUSED check / gate (a record from another machine): distinct from FAIL (1) and PARTIAL (3)
ROWS = 'creative/data/c2/dev.jsonl'   # not the opened C2 test (card addendum 1, A4)
CAPS_OLD, CAPS_BIDC = 'custom_io/caps/caps-old-defaults.json', 'custom_io/caps/caps-bidc.json'
FLOATS = ('R', 'lmode', 'lans', 'lword', 'lop1', 'la1', 'lb1')
LONGS = ('ops', 'a', 'b', 'ans', 'mode', 'vals', 'valid')


def sha256_file(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def _cpu_model():
    try:
        for l in open('/proc/cpuinfo'):
            if l.lower().startswith('model name'):
                return l.split(':', 1)[1].strip()
    except OSError:
        pass
    return None


def machine_info():
    """What bit-exact CPU floats depend on. Call it AFTER the thread count is set."""
    try:
        cap = str(torch.backends.cpu.get_cpu_capability())
    except Exception:
        cap = None
    return dict(torch=str(torch.__version__), platform=platform.platform(), processor=platform.processor(), machine=platform.machine(), cpu=_cpu_model(), cpu_capability=cap,
                threads=torch.get_num_threads(), mkldnn=bool(torch.backends.mkldnn.is_available()), mkl=bool(torch.backends.mkl.is_available()))


def machine_mismatch(rec_machine, here=None):
    """-> list of the machine fields that differ between a record and this machine ([] = same)."""
    here = here or machine_info()
    if not isinstance(rec_machine, dict):
        return ['the record carries no machine block (made by an older version of the recorder)']
    return [f'{k}: record {rec_machine.get(k)!r}, this machine {v!r}' for k, v in here.items() if rec_machine.get(k) != v]


def refusal(rec, what):
    """A REFUSED result (not a FAIL) if the record was made on another machine, else None."""
    bad = machine_mismatch(rec.get('machine'))
    if not bad:
        return None
    return dict(ok=False, refused=True, differences=bad, record_machine=rec.get('machine'), gate_machine=machine_info(),
                why_fail=f'REFUSED: the {what} record was made on a different machine / torch / thread count ({"; ".join(bad)}). Bit-exact floats are only comparable on one machine: '
                         'make the record and run the gate on the same machine (Bid C venue: BensPC). Nothing was compared.')


def load_rows(path, n):
    """The first n rows with their `nums`. A <name>.jsonl whose sibling MANIFEST.json lists <name> is checked against its sha256 (rules_real.load_split); other files are read as they are."""
    from creative import c2_stones, rules_real as R
    d, name = os.path.split(os.path.abspath(path))
    man = os.path.join(d, 'MANIFEST.json')
    if name.endswith('.jsonl') and os.path.exists(man) and name[:-6] in json.load(open(man)):
        rows = R.load_split(d, name[:-6])
    else:
        rows = [json.loads(l) for l in open(path) if l.strip()]
    if len(rows) < n:
        raise SystemExit(f'{path} has {len(rows)} rows, the gate needs {n}')
    return c2_stones._with_nums(rows[:n])


def evaluate_batch(model, vocab, rows, device='cpu', rows_sha256=None):
    """The eval that is recorded and compared. Deterministic: eval mode, no_grad, greedy."""
    from creative import c2_pilot, sampler
    model.eval()
    batch = sampler.make_batch(rows, vocab, device)
    with torch.no_grad():
        o = model.run(batch)
        g = sampler.sample_run(model, batch, greedy=True)
        s1 = sampler.sample_run(model, batch, stop_at=1)
        answers = model.generate(batch)
    t = dict(R=o['R'], lmode=o['lmode'], lans=o['lans'], lword=o['lword'], lop1=s1['lop'], la1=s1['la'], lb1=s1['lb'], **{k: g[k] for k in LONGS})
    return dict(ids=[r['id'] for r in rows], rows_sha256=rows_sha256, right=[bool(x) for x in c2_pilot.greedy_eval(model, rows, vocab, device)['per_q_right']], answers=list(answers),
                tensors={k: v.detach().cpu().contiguous() for k, v in t.items()})


SOURCES = ('train_process', 'reload')


def record_eval(model, vocab, rows, caps_rec=None, device='cpu', source='reload', checkpoint_sha256=None, rows_sha256=None):
    """-> a record dict (torch.save it). source says where the model came from: 'train_process' = the in-memory model of the training process, right after training (custom_io/train.py
    --record-eval; this is the only record check 3 accepts) or 'reload' = a checkpoint loaded from disk (the `record` command). checkpoint_sha256 = the file the record corresponds to; rows_sha256 = sha256 of the rows FILE the rows came from (compare() refuses a record without it)."""
    if source not in SOURCES:
        raise ValueError(f'source must be one of {SOURCES}')
    return dict(kind='bidc-gate-eval-v1', source=source, checkpoint_sha256=checkpoint_sha256, caps=caps_rec, threads=torch.get_num_threads(), torch=str(torch.__version__),
                machine=machine_info(), **evaluate_batch(model, vocab, rows, device, rows_sha256))


def compare(rec, got):
    """-> list of differences between a recorded eval and a fresh one ([] = bit-identical)."""
    bad = []
    if rec['ids'] != got['ids']:
        return ['the recorded rows are not these rows (ids differ)']
    if rec.get('rows_sha256') is None or rec.get('rows_sha256') != got.get('rows_sha256'):
        return [f"the recorded rows are not these rows (rows file sha256: record {rec.get('rows_sha256')}, gate {got.get('rows_sha256')})"]
    if rec['right'] != got['right']:
        bad.append(f"right differs on {sum(a != b for a, b in zip(rec['right'], got['right']))} of {len(rec['right'])} rows")
    if rec['answers'] != got['answers']:
        bad.append('decoded answers differ')
    for k, v in rec['tensors'].items():
        if k not in got['tensors']:
            bad.append(f'{k}: missing')
        elif v.shape != got['tensors'][k].shape:
            bad.append(f'{k}: shape {tuple(v.shape)} vs {tuple(got["tensors"][k].shape)}')
        elif not torch.equal(v, got['tensors'][k]):
            bad.append(f'{k}: not bit-identical (max abs diff {float((v.double() - got["tensors"][k].double()).abs().max()):.3g})' if v.is_floating_point() else f'{k}: differs')
    return bad


def load_record(path):
    """A .pt record made by `record` or by custom_io/train.py --record-eval. Nothing else: a .json (e.g. a C2b results file) has no row ids of its own and no floats."""
    if path.endswith('.json'):
        raise ValueError(f'{path}: a .json is not a gate record (it carries no row ids, rows sha256 or floats). Check 1 needs a .pt made by the `record` command')
    rec = torch.load(path, weights_only=True)
    if rec.get('kind') != 'bidc-gate-eval-v1':
        raise ValueError(f'{path} is not a gate record')
    return rec


def setup(caps_path, expect):
    """Apply a caps file FIRST (fresh process), assert it ran, and check the values are the ones this check is about. -> caps record."""
    from custom_io import caps
    caps.apply_file(caps_path)
    rec = caps.check_applied(caps_path)
    if expect == 'today' and not caps.is_today(rec['values']):
        raise AssertionError(f'{caps_path} is not the old defaults: {rec["values"]}')
    if expect == 'bidc' and (rec['values']['max_ans'], rec['values']['n_reg']) != (35, 36):
        raise AssertionError(f'{caps_path} is not the Bid C caps (max_ans 35, n_reg 36): {rec["values"]}')
    return rec


def check1(a):
    from creative import sleep
    torch.set_num_threads(1)
    caps_rec = setup(a.caps_old, 'today')
    rows = load_rows(a.rows, a.n)
    rec = load_record(a.recorded)
    refused = refusal(rec, 'check 1')
    if refused:
        return refused
    model, vocab, meta = sleep.load_parent(a.c2b_parent, 'cpu')
    bad = compare(rec, evaluate_batch(model, vocab, rows, rows_sha256=sha256_file(a.rows)))
    return dict(ok=not bad, differences=bad, caps_sha256=caps_rec['sha256'], n_params=model.n_params(), parent_sha256=sha256_file(a.c2b_parent), rows_sha256=sha256_file(a.rows),
                recorded_sha256=sha256_file(a.recorded), compared='torch.equal on floats')


def check2(a):
    from creative import sleep
    caps_rec = setup(a.caps_bidc, 'bidc')
    try:
        model, _, _ = sleep.load_parent(a.c2b_parent, 'cpu')
    except RuntimeError as e:
        msg = str(e)
        shape = 'size mismatch' in msg and 'place' in msg
        return dict(ok=shape, raised='RuntimeError', shape_error=shape, message=msg.split('\n')[0][:200] + ' ... ' + next((l.strip() for l in msg.split('\n') if 'place' in l), '')[:200],
                    caps_sha256=caps_rec['sha256'], parent_sha256=sha256_file(a.c2b_parent), why_fail=None if shape else 'RuntimeError, but not the reader.place shape error')
    except Exception as e:
        return dict(ok=False, raised=type(e).__name__, message=str(e)[:300], why_fail='not a shape error; the negative check needs the shape error itself')
    return dict(ok=False, raised=None, why_fail='the C2b parent LOADED under the Bid C caps: the caps were not applied before load_parent', n_params=model.n_params())


def check3(a):
    from creative import sleep
    torch.set_num_threads(1)
    caps_rec = setup(a.caps_bidc, 'bidc')
    rows_path = a.bidc_rows or a.rows
    rows = load_rows(rows_path, a.n)
    rec = load_record(a.bidc_recorded)
    refused = refusal(rec, 'check 3')
    if refused:
        return refused
    ck = torch.load(a.bidc_parent, map_location='cpu', weights_only=False)
    bad = []
    ck_sha = (ck.get('caps') or {}).get('sha256')
    if ck_sha is None:
        bad.append('the checkpoint carries no caps record (trained without --caps, or a derived file that dropped it); under the Bid C caps that is a fail')
    elif ck_sha != caps_rec['sha256']:
        bad.append(f"the checkpoint was trained under caps sha256 {ck_sha}, not {caps_rec['sha256']}")
    if rec.get('source') != 'train_process':
        bad.append(f"the record's source is {rec.get('source')!r}, not 'train_process': check 3 compares against the eval the TRAINING process made on its in-memory model "
                   "(custom_io/train.py --record-eval), not against another reload")
    if rec.get('checkpoint_sha256') != sha256_file(a.bidc_parent):
        bad.append(f"the record belongs to checkpoint sha256 {rec.get('checkpoint_sha256')}, not {sha256_file(a.bidc_parent)}")
    if (rec.get('caps') or {}).get('sha256') != caps_rec['sha256']:
        bad.append(f"the record was made under caps {(rec.get('caps') or {}).get('sha256')}, not {caps_rec['sha256']}")
    model, vocab, meta = sleep.load_parent(a.bidc_parent, 'cpu')
    bad += compare(rec, evaluate_batch(model, vocab, rows, rows_sha256=sha256_file(rows_path)))
    return dict(ok=not bad, differences=bad, caps_sha256=caps_rec['sha256'], n_params=model.n_params(), parent_sha256=sha256_file(a.bidc_parent),
                recorded_sha256=sha256_file(a.bidc_recorded), checkpoint_caps_sha256=ck_sha, record_source=rec.get('source'),
                record_checkpoint_sha256=rec.get('checkpoint_sha256'))


CHECKS = {1: ('caps plumbing at the old defaults', check1, ('c2b_parent', 'recorded')), 2: ('negative: Bid C caps vs a C2b parent', check2, ('c2b_parent',)),
          3: ('round trip of a Bid C parent in a fresh process', check3, ('bidc_parent', 'bidc_recorded'))}


def run(a):
    """Orchestrate: one fresh process per check, stop at the first failure. -> (exit code, report)."""
    want = sorted({int(x) for x in a.checks.split(',')})
    report = dict(gate='bidc_load_gate', started=time.strftime('%Y-%m-%d %H:%M:%S'), device='cpu', checks_requested=want, rows=a.rows, n=a.n,
                  caps_old_sha256=sha256_file(a.caps_old) if os.path.exists(a.caps_old) else None, caps_bidc_sha256=sha256_file(a.caps_bidc) if os.path.exists(a.caps_bidc) else None, results={})
    code = 0
    for k in want:
        title, _, needs = CHECKS[k]
        missing = [f'--{n.replace("_", "-")}' for n in needs if not getattr(a, n)]
        if missing:
            report['results'][k] = dict(title=title, ok=False, why_fail=f'missing {", ".join(missing)}')
        else:
            argv = [sys.executable, '-m', 'creative.bidc_load_gate', 'check', '--which', str(k)] + child_args(a)
            p = subprocess.run(argv, capture_output=True, text=True)
            line = next((l for l in reversed(p.stdout.splitlines()) if l.startswith(TOK)), None)
            res = json.loads(line[len(TOK):]) if line else dict(ok=False, why_fail='the check process died', stderr_tail=p.stderr[-1500:])
            if res.get('refused') and (p.returncode != REFUSED_CODE or res.get('ok')):
                res = dict(res, refused=False, ok=False, why_fail=f'the check process printed a refusal but exited with code {p.returncode}: ' + str(res.get('why_fail')))
            if p.returncode != 0 and res.get('ok'):             # the printed verdict is not enough: a child that exits non-zero is a fail
                res = dict(res, ok=False, why_fail=f'the check process exited with code {p.returncode} although it printed ok', stderr_tail=p.stderr[-1500:])
            report['results'][k] = dict(title=title, **res)
        if not report['results'][k]['ok']:
            code = REFUSED_CODE if report['results'][k].get('refused') else 1
            report['stopped_at'] = k
            break
    report['not_run'] = [k for k in (1, 2, 3) if k not in report['results']]
    if code == REFUSED_CODE:
        report['verdict'] = 'REFUSED: a record was made on a different machine; nothing was compared. Make the record and run the gate on the same machine'
    elif code:
        report['verdict'] = 'FAIL'
    elif report['not_run']:
        report['verdict'] = 'PARTIAL: checks %s were not run; this is NOT a gate pass' % report['not_run']
        code = 3
    else:
        report['verdict'] = 'PASS'
    return code, report


def child_args(a):
    out = []
    for name in ('c2b_parent', 'recorded', 'bidc_parent', 'bidc_recorded', 'bidc_rows', 'rows', 'n', 'caps_old', 'caps_bidc'):
        v = getattr(a, name)
        if v is not None:
            out += [f'--{name.replace("_", "-")}', str(v)]
    return out


def record(a):
    from creative import sleep
    torch.set_num_threads(1)
    caps_rec = None
    if a.caps:
        from custom_io import caps
        caps.apply_file(a.caps)
        caps_rec = caps.check_applied(a.caps)
    rows = load_rows(a.rows, a.n)
    model, vocab, meta = sleep.load_parent(a.ckpt, 'cpu')
    rec = record_eval(model, vocab, rows, caps_rec, source='reload', checkpoint_sha256=sha256_file(a.ckpt), rows_sha256=sha256_file(a.rows))      # a reload record: check 3 refuses it (use train.py --record-eval)
    with open(a.out, 'xb') as f:                                    # exclusive: a record is not overwritten
        torch.save(rec, f)
    return rec


def parser():
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['run', 'record', 'check'])
    ap.add_argument('--which', type=int, choices=[1, 2, 3], help='(internal) the one check this process runs')
    ap.add_argument('--checks', default='1,2,3', help='which checks to run (all three are needed for a pass)')
    ap.add_argument('--c2b-parent', help='a C2b parent checkpoint (e.g. s200 Nprime.pt or the raw B2_s200.pt)')
    ap.add_argument('--recorded', help='check 1: the recorded eval of that parent: a .pt made by `record` on this machine (a .json is refused)')
    ap.add_argument('--bidc-parent', help='check 3: P_0, trained under caps-bidc.json')
    ap.add_argument('--bidc-recorded', help='check 3: P_0\'s own end-of-training eval (.pt)')
    ap.add_argument('--bidc-rows', help='check 3: the rows file of that eval (default --rows)')
    ap.add_argument('--rows', default=ROWS)
    ap.add_argument('--n', type=int, default=64)
    ap.add_argument('--caps-old', default=CAPS_OLD)
    ap.add_argument('--caps-bidc', default=CAPS_BIDC)
    ap.add_argument('--report', help='run: where to write the report (refuses to overwrite)')
    ap.add_argument('--ckpt'); ap.add_argument('--out'); ap.add_argument('--caps', help='record: apply this caps file first')
    return ap


def main(argv=None):
    ap = parser()
    a = ap.parse_args(argv)
    if a.cmd == 'check':
        try:
            res = CHECKS[a.which][1](a)
        except Exception as e:
            res = dict(ok=False, why_fail=f'{type(e).__name__}: {str(e)[:500]}')
        print(TOK + json.dumps(res), flush=True)
        sys.exit(0 if res['ok'] else REFUSED_CODE if res.get('refused') else 1)
    if a.cmd == 'record':
        if not (a.ckpt and a.out):
            ap.error('record needs --ckpt and --out')
        rec = record(a)
        print(json.dumps(dict(out=a.out, n=len(rec['ids']), right=sum(rec['right']), caps=(rec['caps'] or {}).get('sha256'))))
        return
    if not a.report:
        ap.error('run needs --report')
    if os.path.exists(a.report):
        raise SystemExit(f'REFUSED: {a.report} exists. A failed gate is not retried over its own report.')
    code, report = run(a)
    with open(a.report, 'x') as f:
        json.dump(report, f, indent=1)
    print(json.dumps({k: report[k] for k in ('verdict', 'stopped_at', 'not_run') if k in report}))
    for k, r in report['results'].items():
        print(f"check {k} ({r['title']}): {'ok' if r['ok'] else 'FAIL ' + str(r.get('why_fail') or r.get('differences'))}")
    sys.exit(code)


if __name__ == '__main__':
    main()
