#!/usr/bin/env python3
"""python3 run_all.py   (Linux, no GPU, stdlib only, about 6 minutes): builds a scratch copy of the pack, puts the DRAFT files over it, runs every test that can run here and saves the logs.

  scratch = copy of results/8a-g/pc-job-cards/g2fa4 (nothing in the pack is modified)
          + drafts/g2fa4_supervisor.py, drafts/install_g2fa4.py, drafts/rejudge_probe.py
          + drafts/tests/*.py (the pack's fake_runner / test_supervisor / test_addjob copied unchanged, test_probe changed (sidecar fixture), the new test_gatefix.py)
  runs   tests/test_supervisor.py   (the pack's whole suite; at its end it runs test_probe.py and test_addjob.py)
         tests/test_gatefix.py      (the new tests A-D)
  logs   drafts/tests/logs/test_supervisor_drafted.log, test_gatefix.log
Not run here (need torch and the real custom_io tree): test_noise_logic.py, test_supervisor_real.py, check_queue_a8.py, the overlay tests (the overlay is not changed)."""
import os, shutil, subprocess, sys, tempfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
DRAFTS = HERE.parent
PACK = Path(os.environ.get('G2FA4_ORIG_PACK') or DRAFTS.parent.parent / 'pc-job-cards' / 'g2fa4')
LOGS = HERE / 'logs'


def main():
    LOGS.mkdir(exist_ok=True)
    only = sys.argv[1:]
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp) / 'g2fa4'
        shutil.copytree(PACK, scratch, ignore=shutil.ignore_patterns('__pycache__', 'logs'))
        for f in ('g2fa4_supervisor.py', 'install_g2fa4.py', 'rejudge_probe.py'):
            shutil.copy2(DRAFTS / f, scratch / f)
        for f in HERE.glob('*.py'):
            if f.name != 'run_all.py':
                shutil.copy2(f, scratch / 'tests' / f.name)
        env = dict(os.environ, G2FA4_ORIG_PACK=str(PACK), PYTHONDONTWRITEBYTECODE='1')
        bad = 0
        for name, script in (('test_gatefix', 'tests/test_gatefix.py'), ('test_supervisor_drafted', 'tests/test_supervisor.py')):
            if only and name not in only:
                continue
            t0 = time.time()
            r = subprocess.run([sys.executable, script], cwd=str(scratch), env=env, capture_output=True, text=True)
            log = r.stdout + (('\n--- stderr ---\n' + r.stderr) if r.stderr.strip() else '')
            (LOGS / f'{name}.log').write_text(log.replace(str(scratch), '<scratch-pack>'), encoding='utf-8')
            tail = (r.stdout.strip().splitlines() or ['(no output)'])[-1]
            print(f'{name}: rc={r.returncode} in {time.time() - t0:.0f} s; last line: {tail[:150]}')
            bad += r.returncode != 0
        return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
