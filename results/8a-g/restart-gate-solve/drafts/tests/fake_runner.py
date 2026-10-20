#!/usr/bin/env python3
"""A stand-in for custom_io.local_runner + g8a.job + train.py, for test_supervisor.py only (Linux, no GPU).

fake_runner.py --work W --queue Q.txt-path --job J --arm B3G2 --steps N --step-s 0.02 --ckpt-every 100 [--crash-at K] [--nan-at K] [--offset X] [--seg2-offset X] [--jitter X] [--force-resume-step K]
The "runner" starts one child ("train", same command line + --child) in its own process group and, like g8a.job --local, writes the job-level RESULT.json
(status ok / arm_failed) when the child ends; the child writes OUT/events.jsonl like train.py does with --ckpt-every / --resume (events: segment, resumed, train),
OUT/ckpt/step-<k>.pt/.json, and OUT/RESULT.json at the end. The loss is a deterministic function of the update, so a resume reproduces it exactly."""
import argparse, json, math, os, subprocess, sys, time, zlib
from pathlib import Path


def loss_at(step, offset, seg_offset, seg, jitter=0.0, job=''):
    base = 6.0 * math.exp(-step / 150.0) + 1.0 + 0.04 * (((step * 7919) % 13) - 6) / 6.0
    noise = jitter * ((zlib.crc32(f'{job}:{step}'.encode()) % 2001) - 1000) / 1000.0          # +-jitter, different for every job name (two resumes of one checkpoint)
    return base + offset + (seg_offset if seg >= 2 else 0.0) + noise


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work'); ap.add_argument('--queue'); ap.add_argument('--job'); ap.add_argument('--arm', default='B3G2')
    ap.add_argument('--steps', type=int, default=900); ap.add_argument('--step-s', type=float, default=0.02); ap.add_argument('--ckpt-every', type=int, default=100)
    ap.add_argument('--crash-at', type=int, default=0); ap.add_argument('--crash-always', action='store_true')
    ap.add_argument('--nan-at', type=int, default=0); ap.add_argument('--offset', type=float, default=0.0); ap.add_argument('--seg2-offset', type=float, default=0.0); ap.add_argument('--jitter', type=float, default=0.0); ap.add_argument('--force-resume-step', type=int, default=0)
    ap.add_argument('--child', action='store_true'); ap.add_argument('--busy', default='')
    ap.add_argument('--device', default='cuda'); ap.add_argument('--hang-at', type=int, default=0); ap.add_argument('--die-after-resume-once', action='store_true')
    ap.add_argument('--seg2-lr', type=float, default=0.0)          # drafts only (tests/test_gatefix.py): the logged lr of a resumed segment, to make an exact-field mismatch
    a = ap.parse_args()
    q = Path(a.queue).stem
    out = Path(a.work) / 'results' / q / a.job
    arm = out / a.arm
    if not a.child:                                              # the runner
        arm.mkdir(parents=True, exist_ok=True)
        if (out / 'RESULT.json').exists():
            print('job already has a RESULT.json: skipped (like local_runner)')
            return
        if a.busy:
            with open(a.busy, 'a') as f:
                f.write(f'custom-io {q}/{a.job} {os.getpid()} now\n')
        p = subprocess.Popen([sys.executable] + sys.argv + ['--child'], stdout=open(arm / 'stdout.txt', 'w'), stderr=subprocess.STDOUT)
        rc = p.wait()
        res = json.load(open(arm / 'RESULT.json')) if (arm / 'RESULT.json').exists() else {}
        json.dump(dict(status='ok' if rc == 0 else 'arm_failed', job=dict(arms={a.arm: dict(rc=rc, status=res.get('status', 'no_result'))})), open(out / 'RESULT.json', 'w'))
        if a.busy and os.path.exists(a.busy):                    # local_runner removes its own GPU-BUSY line when the run ends
            keep = [ln for ln in open(a.busy).read().splitlines() if not ln.startswith(f'custom-io {q}/{a.job} ')]
            open(a.busy, 'w').write('\n'.join(keep) + ('\n' if keep else ''))
        return
    # the child = train.py
    ck = arm / 'ckpt'
    ck.mkdir(exist_ok=True)
    ev = open(arm / 'events.jsonl', 'a', buffering=1)

    def jp(**k):
        line = json.dumps(k)
        print(line, flush=True)
        ev.write(line + '\n')
    seg = 1 + sum(1 for ln in open(arm / 'events.jsonl') if '"segment"' in ln)
    jp(event='segment', ckpt_every=a.ckpt_every, resume=True)
    side = sorted(ck.glob('step-*.json'), key=lambda p: int(p.stem.split('-')[1]))
    if a.die_after_resume_once and side and not (arm / 'died.flag').exists():
        (arm / 'died.flag').write_text('x')              # a segment that dies before its first update
        sys.exit(1)
    jp(event='start', device=a.device)
    step, t0 = 0, time.time()
    if side:
        step = a.force_resume_step or int(side[-1].stem.split('-')[1])
        jp(event='resumed', step=step, msg=f'RESUMED step={step}')
    el = 0.0
    while step < a.steps:
        time.sleep(a.step_s)
        step += 1
        el += a.step_s
        if a.hang_at and step == a.hang_at and not (arm / 'hung.flag').exists():
            (arm / 'hung.flag').write_text('x')
            time.sleep(3600)
        if a.crash_at and step == a.crash_at and (a.crash_always or not (arm / 'crashed.flag').exists()):
            (arm / 'crashed.flag').write_text('x')
            sys.exit(1)
        loss = float('nan') if (a.nan_at and step == a.nan_at) else loss_at(step, a.offset, a.seg2_offset, seg, a.jitter, a.job)
        jp(event='train', step=step, loss=round(loss, 5), lr=(a.seg2_lr if a.seg2_lr and seg >= 2 else 1e-3), elapsed=round(el, 3))
        if not math.isfinite(loss):
            json.dump(dict(status='nonfinite_loss', steps=step), open(arm / 'RESULT.json', 'w'))
            return
        if step % a.ckpt_every == 0:
            (ck / f'step-{step}.pt').write_bytes(b'x')
            (ck / f'step-{step}.json').write_text('{}')
    json.dump(dict(status='ok', steps=step, steps_per_s=1 / a.step_s, train_s=el, peak_mem_mib=8800.0, n_params=4023302), open(arm / 'RESULT.json', 'w'))


if __name__ == '__main__':
    main()
