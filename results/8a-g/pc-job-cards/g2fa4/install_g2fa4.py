#!/usr/bin/env python3
"""install_g2fa4.py: puts the G2f-a4 pack on BensPC. Run it with the PC's own python from the folder the Mac copied (C:\\Users\\benja\\custom-io\\in-g2fa4):

    C:\\Users\\benja\\AppData\\Local\\Programs\\Python\\Python310\\python.exe install_g2fa4.py [--check] [--skip-tests] [--register]

It starts no training job and changes nothing that already exists (a folder or file it replaces is renamed .aside-<stamp>). Steps:
 1. refuses if a custom_io job is running (it would compete for the CPU and the GPU) and checks the pinned hashes of src-b3g2 (the code G2f ran: custom_io at 74d6e92c75);
 2. src-b3g2ck = a copy of src-b3g2 with ONE changed file, custom_io/train.py (the checkpoint / resume overlay of the AT run) and the new tests; src-b3g2 stays untouched;
 3. the two queue files; WORK\\g2fa4\\ with the supervisor and plan.json (its pins are the hashes of what was just checked);
 4. CPU tests of the overlay on the b3g2 model (tiny; the test also runs the Windows file handling: os.replace over a file, fsync): flags off == the unmodified train.py,
    a kill in the middle of a checkpoint interval + --resume == the uninterrupted run, bit for bit;
 5. with --register: three scheduled tasks (boot as SYSTEM, logon as this user, selftest as SYSTEM). They do nothing until the supervisor is armed (`arm`).
--check only does step 1 and reports. Exit 0 = installed (or checked) fine."""
import argparse, hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path

IN = Path(__file__).resolve().parent
CIO = Path(os.environ.get('G2FA4_CIO', r'C:\Users\benja\custom-io'))         # the env overrides are for the test on a Linux box only
WORK = CIO / 'work'
SRC0, SRC = CIO / 'src-b3g2', CIO / 'src-b3g2ck'
STATE = WORK / 'g2fa4'
PY = os.environ.get('G2FA4_PY', r'C:\Users\benja\AppData\Local\Programs\Python\Python310\python.exe')
BUSY = os.environ.get('G2FA4_BUSY', r'C:\Users\benja\GPU-BUSY.txt')
EGPATH = os.environ.get('G2FA4_EGPATH', r'C:\Users\benja\eg_site;C:\Users\benja\lis300\venv\Lib\site-packages')
COMMIT = '74d6e92c75'
STAMP = time.strftime('%Y%m%d-%H%M%S')

# SHA-256 of the files of custom_io at COMMIT that the job and the overlay depend on (the same hashes install_rr.ps1 pinned on 10-12 for the files it lists).
PINS0 = {
    'models/b3g2.py': 'a4c61f0b567ec7e62b3233549be63eca7bca2a3f35a934dfc217fa49390868ce',
    'models/writer.py': 'f3a40ad58749bbc24a964942dc650c79864d6a74442628aac7d752730e73309e',
    'g8a/caps.py': '32862ae2d4e6e401fcad5bb6c5e54b0b8845019202dea73e2cb4c7efe5eea03e',
    'g8a/caps_b3g2.json': 'ee551d3aacbf9ec02d2ac7f5e7e6e12f44e15aba2c39f5f38c3f1e3ec12d7ed4',
    'g8a/job.py': 'a590e3f176159f531571b1e5ae95bd48d2160238cb999add5eb6be7734fe6a1a',
    'g8a/configs.py': '31287a25a6ad9cbf48973520f1174c788a3db5ce61f607265aa5ec8fa99bd5da',
    'local_runner.py': '0562a4bb065a02f6c048d919d68bb6d445f36e357518dc8826d9d545323db4ef',
    'train.py': 'e05762ecca1af18f6260f09e5974e03b884e2f5ff5c21a4b801eed913d16793d',        # the UNMODIFIED train.py
}
OVERLAY_TRAIN = 'e75e45fa43c6a6422c0a0e4222e05d8afc27580ec6551100680ed8f9ecdc5015'
CAPS_B3G2_WORK = 'ee551d3aacbf9ec02d2ac7f5e7e6e12f44e15aba2c39f5f38c3f1e3ec12d7ed4'          # WORK\b3-inputs\caps_b3g2.json


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


ok_all = True


def row(good, what, detail=''):
    global ok_all
    ok_all = ok_all and good
    print(f'[{"ok" if good else "FIX"}] {what} {detail}', flush=True)
    return good


def aside(p):
    p = Path(p)
    if p.exists():
        q = p.with_name(p.name + '.aside-' + STAMP)
        os.replace(p, q)
        print(f'      moved aside: {q}')


def procs():
    if os.name != 'nt':
        sys.path.insert(0, str(IN))
        import g2fa4_supervisor as S
        return [(str(p), c) for p, c in S.list_procs()]
    ps = ("Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' } | ForEach-Object { '{0}|{1}' -f $_.ProcessId, $_.CommandLine }")
    r = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', ps], capture_output=True, text=True, timeout=120)
    return [ln.partition('|')[::2] for ln in r.stdout.splitlines() if '|' in ln]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--skip-tests', action='store_true')
    ap.add_argument('--register', action='store_true')
    a = ap.parse_args()
    print(f'install_g2fa4 {STAMP} from {IN}')
    # 1. nothing running, pins of src-b3g2
    busy = [(p, c[:100]) for p, c in procs() if 'custom_io' in c and 'install_g2fa4' not in c]
    row(not busy, 'no custom_io job is running', str(busy))
    sf = SRC0 / 'G2-SETUP-OK.txt'
    print('      src-b3g2\\G2-SETUP-OK.txt:', sf.read_text(errors='replace').replace('\n', ' | ')[:300] if sf.exists() else 'MISSING', '(information; the hashes below decide)')
    for rel, want in PINS0.items():
        p = SRC0 / 'custom_io' / rel
        h = sha(p) if p.exists() else None
        row(h == want, f'src-b3g2 {rel}', (h or 'MISSING')[:12])
    cb = WORK / 'b3-inputs' / 'caps_b3g2.json'
    row(cb.exists() and sha(cb) == CAPS_B3G2_WORK, 'WORK\\b3-inputs\\caps_b3g2.json', (sha(cb)[:12] if cb.exists() else 'MISSING'))
    for rel in ('overlay/train.py', 'overlay/tests/test_ckpt.py', 'overlay-tests/test_ckpt_b3g2.py', 'queue/8aB3G2A4-pc.txt', 'queue/8aB3G2A4b32-pc.txt', 'g2fa4_supervisor.py'):
        row((IN / rel).exists(), f'pack file {rel}')
    row((IN / 'overlay' / 'train.py').exists() and sha(IN / 'overlay' / 'train.py') == OVERLAY_TRAIN, 'overlay train.py hash', OVERLAY_TRAIN[:12])
    row(Path(PY).exists(), 'python', PY)
    du = shutil.disk_usage(str(WORK))
    row(du.free > float(os.environ.get('G2FA4_MINFREE_GB', 30)) * 2 ** 30, 'disk', f'{du.free / 2 ** 30:.0f} GB free')
    if a.check or not ok_all:
        print('CHECK ONLY' if a.check else 'NOT INSTALLED: fix the [FIX] lines first')
        return 0 if ok_all else 1

    # 2. src-b3g2ck
    done = SRC / 'G2FA4-SETUP-OK.txt'
    if done.exists() and OVERLAY_TRAIN in done.read_text(errors='replace') and sha(SRC / 'custom_io' / 'train.py') == OVERLAY_TRAIN:
        print('src-b3g2ck is already installed with this overlay; kept')
    else:
        aside(SRC)
        shutil.copytree(SRC0, SRC, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        shutil.copy2(IN / 'overlay' / 'train.py', SRC / 'custom_io' / 'train.py')
        for f in (IN / 'overlay' / 'tests' / 'test_ckpt.py', IN / 'overlay-tests' / 'test_ckpt_b3g2.py'):
            shutil.copy2(f, SRC / 'custom_io' / 'tests' / f.name)
        print(f'copied {SRC0} -> {SRC}; train.py replaced by the overlay; two tests added')
    for rel, want in PINS0.items():
        if rel != 'train.py':
            row(sha(SRC / 'custom_io' / rel) == want, f'src-b3g2ck {rel}')
    row(sha(SRC / 'custom_io' / 'train.py') == OVERLAY_TRAIN, 'src-b3g2ck train.py = overlay')
    # 3. queue files + WORK\g2fa4
    ql = SRC / 'custom_io' / 'queue_local'
    ql.mkdir(exist_ok=True)
    for q in ('8aB3G2A4-pc.txt', '8aB3G2A4b32-pc.txt'):
        dst = ql / q
        if dst.exists() and sha(dst) != sha(IN / 'queue' / q):
            aside(dst)
        shutil.copy2(IN / 'queue' / q, dst)
    STATE.mkdir(parents=True, exist_ok=True)
    sup = STATE / 'g2fa4_supervisor.py'
    if sup.exists() and sha(sup) != sha(IN / 'g2fa4_supervisor.py'):
        aside(sup)
    shutil.copy2(IN / 'g2fa4_supervisor.py', sup)
    pins = {str(SRC / 'custom_io' / rel.replace('/', os.sep)): h for rel, h in PINS0.items() if rel != 'train.py'}
    pins[str(SRC / 'custom_io' / 'train.py')] = OVERLAY_TRAIN
    pins[str(cb)] = CAPS_B3G2_WORK
    plan = dict(
        version=1, work=str(WORK), busy=BUSY, python=PY, state_dir=str(STATE), poll_s=15, max_no_progress=3, gpu=dict(need_free_mib=9500), pins=pins,
        jobs=[dict(id='g2fa4', title='G2f-a4 (B3G2 3M seed 400, accum 4)', src=str(SRC), queue='8aB3G2A4-pc', job='8aB3G2A4-3M-s400', arm='B3G2', steps=24000, accum=4, kill_resume_at=150,
                   trace_a=dict(upto=300, peak_limit_mib=12288, first_n=50, last_n=50, resume_first_diff=0.01, resume_mean_abs=0.02, resume_max_abs=0.10),
                   compare=dict(upto=300, last_n=50, diff_mean_pass=0.03, diff_mean_fail=0.06, last_n_pass=0.05, last_n_fail=0.10, report_from=101),
                   baseline=dict(queue='8aB3G2A4b32-pc', job='8aB3G2A4b32-3M-s400', upto=300, need_free_mib=4000))])
    pp = STATE / 'plan.json'
    if pp.exists() and json.loads(pp.read_text()) != plan:
        aside(pp)
    pp.write_text(json.dumps(plan, indent=1))
    print(f'wrote {pp}')
    # 4. CPU tests of the overlay on b3g2 (also the Windows file handling)
    if not a.skip_tests:
        env = dict(os.environ, PYTHONPATH=EGPATH, BASE_TREE=str(SRC0), OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', PYTHONUTF8='1')
        t0 = time.time()
        r = subprocess.run([PY, '-m', 'custom_io.tests.test_ckpt_b3g2'], cwd=str(SRC), env=env, capture_output=True, text=True, timeout=3600)
        (STATE / f'install-test-{STAMP}.txt').write_text(r.stdout + '\n--- stderr ---\n' + r.stderr[-6000:], encoding='utf-8')
        row(r.returncode == 0 and 'ALL OK' in r.stdout, f'CPU test of the checkpoint overlay on b3g2 ({time.time() - t0:.0f} s)', r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-300:])
        if r.returncode != 0:
            print(r.stdout[-1500:], r.stderr[-1500:])
    done.write_text(f'{STAMP} installed: src-b3g2 ({COMMIT}) + overlay train.py {OVERLAY_TRAIN}; tests {"skipped" if a.skip_tests else "passed" if ok_all else "FAILED"}\n', encoding='ascii')
    # 5. scheduled tasks
    if a.register and ok_all:
        run = f'"{PY}" "{sup}" --plan "{pp}" run'
        st = f'"{PY}" "{sup}" --plan "{pp}" selftest'
        for name, extra, tr in (('G2FA4-SUPERVISOR', ['/SC', 'ONSTART', '/RU', 'SYSTEM', '/RL', 'HIGHEST'], run), ('G2FA4-SUPERVISOR-LOGON', ['/SC', 'ONLOGON'], run),
                                ('G2FA4-SELFTEST', ['/SC', 'ONCE', '/ST', '00:00', '/RU', 'SYSTEM', '/RL', 'HIGHEST'], st)):
            r = subprocess.run(['schtasks', '/Create', '/TN', name, '/TR', tr, '/F'] + extra, capture_output=True, text=True)
            row(r.returncode == 0, f'scheduled task {name}', (r.stdout + r.stderr).strip()[:200])
    print('G2FA4 INSTALL DONE' if ok_all else 'G2FA4 INSTALL FINISHED WITH [FIX] LINES')
    return 0 if ok_all else 1


if __name__ == '__main__':
    sys.exit(main())
