"""DRAFT pending coordinator confirmation (GW-LS). The one sealed read of GW-LS (game/WALL-SOLVE-RESULT.md section 3) and its sealed marks. NOT to be run before round 8 exists.

  python -m game.gwls_final [--dry-run] [--analyze-only] [--selftest] [--root DIR] [--arm-c DIR] [--persist-dir DIR]

Scores DIR/s<seed>/checkpoint-iter8.pt on the 100 sealed maps ONCE per seed, both seeds in parallel (2 threads each), by exactly
    python -m game.score --arm model --ckpt <ckpt> --picker sample --temp 1.0 --out DIR/s<seed>/score-sample.json --threads 2
(the output is a per-world file in the format of arm C's score-sample.json). Before it plays anything it REFUSES (all problems are listed) unless:
  * round 8 is complete on both seeds: iter-8.json and checkpoint-iter8.pt exist AND state.pt (written last, atomically, by game.imitate) says k == 8,
    run seed 398 / 399 and day offset 4 (a run that is still training is not read); and training has STOPPED (k == 8 alone is not proof): no
    iter-k.json / play-k-*.json.gz / checkpoint-iterk.pt for any k > 8 in the seed folder, no live process whose command line contains 'imitate' (any launch form) and refers to
    the seed folder (absolute / real path, a relative path resolved from the process's cwd; an unresolvable cwd counts as a match), state.pt not older than iter-8.json and checkpoint-iter8.pt. A check that cannot be evaluated (no /proc and no pgrep, an
    unreadable folder) is a refusal;
  * the round-4 leading indicator is not STOP: gwls_report.indicator is recomputed from the iter-*.json and play files of rounds 3 and 4 under the
    reading fixed in the start record (a seed trips if ratio_w <= 0.5 or non-habit <= ref - 0.5, over rounds 3-4; STOP only if both seeds trip). A STOP
    run gets no sealed read, and an unfinished round 3 / 4 gives no read either;
  * arm C's file is the one on record: sha256 equal to the committed file's (constants below), picker sample, T 1.0, 100 worlds, checkpoint the n64000
    one of that seed, and its means equal the record (total 6.50 / 7.10, non-habit 5.46 / 5.85, stone 40 / 43%);
  * no result file for either checkpoint exists, and no score-started.lock of an earlier attempt is there (a crashed attempt is not silently
    re-played; delete the lock by hand only on a decision). The lock is taken ATOMICALLY (O_CREAT|O_EXCL) for both seeds BEFORE these checks, so two
    concurrent invocations cannot both pass; a failed acquisition refuses, and a refusal releases only the locks this invocation created.
Also refused: a record of a previous sealed read (an s200/ or s201/ score-sample.json or a final.json in --persist-dir, a final.json or read-record.json in --root);
game/constants.json episode_cap (play.load_constants) different from arm C's 1000. Identity of a result (play and --analyze-only) goes beyond its metadata: cap 1000 and
gate None as arm C's, and <root>/read-record.json (written atomically after the locks and before the scorers start: per seed sha256 + mtime_ns of
checkpoint-iter8.pt and the start time; completed with each result's sha256 after the scorers exit 0 and persisted with the results) must be complete and match:
checkpoint sha256 and mtime_ns as recorded, result sha256 as recorded, result mtime not before the recorded start. The locks are removed only at the very end (identity
passed, record complete, results and final.json persisted); a failed identity check leaves them, the attempt stays unresolved.
--analyze-only never plays, but goes through the SAME gate, round-8 completeness (with the training-stopped proof), arm C checks and lock rule
(any score-started.lock = an unresolved attempt = refuse), and checks each result's identity: ckpt is (realpath) this root's s<seed>/checkpoint-iter8.pt,
arm model, picker sample, T 1.0, 100 worlds with the sealed seeds 7,000,000-7,000,099 once each. The play path applies the same identity check to the
fresh result before the marks. Any failure is a refusal string and final.json is not written. --dry-run prints the plan, arm C's numbers and every refusal
reason, and plays nothing (exit status 1 if it would refuse).
Straight after the sealed read the score files, and after the analysis final.json, are copied to --persist-dir (default game/results/gwls/; no git
operation: the session lead commits).

Then, per seed, paired by world seed against arm C (glprobe/s<seed>/n64000/score-sample.json) with game.analyze.boot_diff (2000 draws, seed 0):
total unlocks diff and 95% CI, NON-HABIT unlocks diff and 95% CI (unlocks whose name is not collect_sapling, place_plant, eat_plant, wake_up),
stone maps (collect_stone share) diff in points. Sealed marks, applied verbatim:
  PASS (screen) iff on both seeds: non-habit diff >= +0.3 with CI low > 0, total diff >= +0.5, stone diff >= +10 points.
  PROVED WRONG iff on both seeds non-habit diff <= -0.5, OR stone diff <= -15 points on both seeds.
  else NO VERDICT (no extension without new marks).
"""
import argparse
import contextlib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

from game import analyze, gwls_report

SCRATCH = '/tmp/claude-0/-home-user/a1ebb63a-25ce-579d-bded-94d555e1f95e/scratchpad'
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PERSIST_DIR = os.path.join(REPO_ROOT, 'game', 'results', 'gwls')
HABIT = {'collect_sapling', 'place_plant', 'eat_plant', 'wake_up'}
SEEDS = (200, 201)
SEALED_SEEDS = list(range(7000000, 7000100))
RUN_SEED = {200: 398, 201: 399}
DAY_OFFSET = 4
PASS_NH, PASS_TOTAL, PASS_STONE = 0.3, 0.5, 10.0
WRONG_NH, WRONG_STONE = -0.5, -15.0
# Arm C as on record: the committed files origin/claude/project-thread-yha868:results/game-world/glprobe-run/s20X/n64000/score-sample.json
ARM_C_SHA256 = {200: '516f7329d74486d74075243217ee4e62559b92316efed9fad47a0c470ab631dc',
                201: '4ec56fd9b260d04d38c3a9dd57c25c9c679e7b11167936caf9e6da7e6522f7f1'}
ARM_C_CAP = 1000                                         # arm C's episode cap on record (its score-sample.json: cap 1000, gate None)
ARM_C_RECORD = {200: dict(total=6.50, nonhabit=5.46, stone=40.0), 201: dict(total=7.10, nonhabit=5.85, stone=43.0)}


def nonhabit(w):
    return float(sum(1 for _, n in w['unlocks'] if n not in HABIT))


def stone(w):
    return 100.0 * w['ach_rate']['collect_stone']


def compare(model_res, base_res):
    """-> the per-seed paired numbers (model minus arm C), paired by world seed."""
    mw, bw = model_res['per_world'], base_res['per_world']
    assert [w['seed'] for w in mw] == [w['seed'] for w in bw], 'arms are on different worlds'
    tot = analyze.boot_diff([w['n_unlocks'] for w in mw], [w['n_unlocks'] for w in bw], 2000, 0)
    nh = analyze.boot_diff([nonhabit(w) for w in mw], [nonhabit(w) for w in bw], 2000, 0)
    st = sum(stone(w) for w in mw) / len(mw) - sum(stone(w) for w in bw) / len(bw)
    return dict(total=dict(diff=tot[0], lo=tot[1], hi=tot[2]), nonhabit=dict(diff=nh[0], lo=nh[1], hi=nh[2]), stone_points=st,
                mean_total=[sum(w['n_unlocks'] for w in mw) / len(mw), sum(w['n_unlocks'] for w in bw) / len(bw)],
                mean_nonhabit=[sum(map(nonhabit, mw)) / len(mw), sum(map(nonhabit, bw)) / len(bw)],
                stone_pct=[sum(map(stone, mw)) / len(mw), sum(map(stone, bw)) / len(bw)])


def verdict(per_seed):
    """per_seed: {seed: compare(...)} -> 'PASS' | 'PROVED WRONG' | 'NO VERDICT', the sealed marks verbatim."""
    r = lambda x: round(x, 6)
    ps = list(per_seed.values())
    assert len(ps) == 2
    if all(r(p['nonhabit']['diff']) >= PASS_NH and r(p['nonhabit']['lo']) > 0 and r(p['total']['diff']) >= PASS_TOTAL
           and r(p['stone_points']) >= PASS_STONE for p in ps):
        return 'PASS'
    if all(r(p['nonhabit']['diff']) <= WRONG_NH for p in ps) or all(r(p['stone_points']) <= WRONG_STONE for p in ps):
        return 'PROVED WRONG'
    return 'NO VERDICT'


def paths(root, arm_c, seed):
    """Every path is absolute (the scorer child runs with cwd=REPO_ROOT, so a relative --root would point at other files there)."""
    root, arm_c = os.path.abspath(root), os.path.abspath(arm_c)
    d = os.path.join(root, f's{seed}')
    return dict(dir=d, ckpt=os.path.join(d, 'checkpoint-iter8.pt'), out=os.path.join(d, 'score-sample.json'), lock=os.path.join(d, 'score-started.lock'), record=os.path.join(root, 'read-record.json'),
                iter8=os.path.join(d, 'iter-8.json'), state=os.path.join(d, 'state.pt'), base=os.path.join(arm_c, f's{seed}', 'n64000', 'score-sample.json'))


def command(p):
    return [sys.executable, '-m', 'game.score', '--arm', 'model', '--ckpt', p['ckpt'], '--picker', 'sample', '--temp', '1.0',
            '--out', p['out'], '--threads', '2']


# ---------- the refusals ----------

def arm_c_problems(seed, raw, b, check_hash=True):
    """Problems (strings) with arm C's file for `seed`: raw = its bytes, b = the parsed JSON. [] when it is the one on record."""
    bad = []
    if check_hash and hashlib.sha256(raw).hexdigest() != ARM_C_SHA256[seed]:
        bad.append(f'arm C seed {seed}: sha256 {hashlib.sha256(raw).hexdigest()[:16]}... is not the committed file ({ARM_C_SHA256[seed][:16]}...)')
    if b.get('arm') != 'model':
        bad.append(f'arm C seed {seed}: arm is {b.get("arm")!r}, not model')
    if b.get('picker') != 'sample':
        bad.append(f'arm C seed {seed}: picker is {b.get("picker")!r}, not sample')
    if b.get('temp') != 1.0:
        bad.append(f'arm C seed {seed}: temp is {b.get("temp")!r}, not 1.0')
    pw = b.get('per_world') or []
    if not (b.get('worlds') == len(pw) == 100):
        bad.append(f'arm C seed {seed}: worlds {b.get("worlds")} / per_world {len(pw)}, not 100')
    if b.get('cap') != ARM_C_CAP or type(b.get('cap')) is bool:
        bad.append(f'arm C seed {seed}: cap is {b.get("cap")!r}, not {ARM_C_CAP}')
    if b.get('gate') is not None:
        bad.append(f'arm C seed {seed}: gate is {b.get("gate")!r}, not None')
    tail = ['s%d' % seed, 'n64000', 'checkpoint.pt']
    if os.path.normpath(str(b.get('ckpt'))).split(os.sep)[-3:] != tail:
        bad.append(f'arm C seed {seed}: ckpt {b.get("ckpt")!r} does not end with {"/".join(tail)} (the GW-L 64k checkpoint)')
    if pw and len(pw) == 100:
        rec = ARM_C_RECORD[seed]
        got = dict(total=round(float(b.get('mean_unlocks', -1)), 2), nonhabit=round(sum(map(nonhabit, pw)) / 100, 2), stone=round(sum(map(stone, pw)) / 100, 1))
        if any(abs(got[k] - rec[k]) > 1e-9 for k in rec):
            bad.append(f'arm C seed {seed}: means {got} differ from the record {rec}')
    return bad


def load_arm_c(p, seed):
    """-> (parsed arm C file or None, [problems])."""
    if not os.path.exists(p['base']):
        return None, [f'arm C file missing: {p["base"]}']
    try:
        with open(p['base'], 'rb') as f:
            raw = f.read()
        b = json.loads(raw)
        return b, arm_c_problems(seed, raw, b)
    except gwls_report.READ_ERRORS as e:
        return None, [f'arm C seed {seed}: {p["base"]} cannot be read: {type(e).__name__}: {e}']


def read_state(path):
    import torch
    return torch.load(path, map_location='cpu', weights_only=False)


LAST_ROUND = 8
FILE_ROUND = [re.compile(r'iter-(\d+)\.json$'), re.compile(r'play-(\d+)-\d+\.json\.gz$'), re.compile(r'checkpoint-iter(\d+)\.pt$')]


def inside(cwd, arg, real):
    """True if the command-line argument `arg`, resolved from `cwd`, is the folder `real` or something inside it."""
    if not arg or arg.startswith('-'):
        return False
    full = os.path.realpath(os.path.join(cwd, arg))
    return full == real or full.startswith(real + os.sep)


def references_folder(args, cwd, folder, real):
    """N5: does a process with this argv (list) and cwd (None = unreadable) refer to the seed folder, in any launch form? Fails closed: an unresolvable cwd is a match."""
    if any(n in a for a in args for n in (folder, real)):                       # the absolute / real path anywhere in any argument (also inside a -c program)
        return True
    if cwd is None:                                                              # cannot resolve a relative reference: cannot rule it out
        return True
    if inside(cwd, '.', real):                                                   # the process works from inside the folder
        return True
    for a in args:                                                               # relative references: the argument, its --opt=value part, and the words of a -c program
        for t in [a, a.split('=', 1)[-1]] + [x for x in re.split(r'[\s\'"(),;=\[\]{}]+', a) if x]:
            try:
                if inside(cwd, t, real):
                    return True
            except (OSError, ValueError):                                        # a word that cannot even be resolved as a path: cannot rule it out
                return True
    return False


def training_processes(folder):
    """-> pids of live processes whose command line (joined) contains 'imitate' (game.imitate, game/imitate.py, 'from game import imitate', ...) and that
    refer to this seed folder (its absolute or real path anywhere in the argv, or a relative reference that resolves into it from that process's cwd);
    an 'imitate' process whose cwd cannot be read counts as a match (fail closed). Without /proc: every other process matching pgrep -f 'imitate' counts.
    Raises when it cannot be evaluated (no /proc and no pgrep): the caller treats that as a refusal."""
    folder = os.path.abspath(folder)
    real = os.path.realpath(folder)
    me = os.getpid()
    if os.path.isdir('/proc/self'):
        hits = []
        for e in os.listdir('/proc'):
            if not e.isdigit() or int(e) == me:
                continue
            try:
                with open(f'/proc/{e}/cmdline', 'rb') as f:
                    args = [a.decode('utf-8', 'replace') for a in f.read().split(b'\0') if a]
            except (FileNotFoundError, ProcessLookupError):                       # the process ended while we looked: not running
                continue
            except OSError as ex:                                                 # a process whose argv cannot be read cannot be ruled out: the probe fails
                raise RuntimeError(f'/proc/{e}/cmdline cannot be read: {type(ex).__name__}: {ex}')
            if 'imitate' not in ' '.join(args):
                continue
            try:
                cwd = os.readlink(f'/proc/{e}/cwd')
            except (FileNotFoundError, ProcessLookupError):
                if not os.path.exists(f'/proc/{e}'):                              # ended meanwhile
                    continue
                cwd = None
            except OSError:
                cwd = None
            if references_folder(args, cwd, folder, real):
                hits.append(int(e))
        return hits
    if shutil.which('pgrep'):
        r = subprocess.run(['pgrep', '-f', 'imitate'], capture_output=True, text=True)
        if r.returncode not in (0, 1):
            raise RuntimeError(f'pgrep failed with status {r.returncode}: {r.stderr.strip()}')
        return sorted({int(x) for x in r.stdout.split()} - {me})
    raise RuntimeError('neither /proc nor pgrep is available to look for a live imitate process')


def training_stopped_problems(seed, p):
    """Proof (beyond state.pt k == 8) that training has stopped, failing closed: [] only if every check was evaluated and held."""
    bad = []
    try:
        names = os.listdir(p['dir'])
    except OSError as e:
        return [f'seed {seed}: training-stopped proof cannot be evaluated, {p["dir"]} cannot be listed: {type(e).__name__}: {e}']
    later = sorted(n for n in names for rx in FILE_ROUND if (m := rx.match(n)) and int(m.group(1)) > LAST_ROUND)
    if later:
        bad.append(f'seed {seed}: files of a round after {LAST_ROUND} exist, training has not stopped: {later[:6]}')
    try:
        pids = training_processes(p['dir'])
    except Exception as e:                                                       # the probe cannot run: refuse (never assume nothing is running)
        bad.append(f'seed {seed}: the live-process probe cannot be evaluated ({type(e).__name__}: {e}); training is not proved stopped')
    else:
        if pids:
            bad.append(f'seed {seed}: a live game.imitate process works in {p["dir"]} (pid {pids}); training has not stopped')
    try:
        mt = {n: os.stat(p[n]).st_mtime_ns for n in ('state', 'iter8', 'ckpt')} if all(os.path.exists(p[n]) for n in ('state', 'iter8', 'ckpt')) else None
    except OSError as e:
        bad.append(f'seed {seed}: file times cannot be read: {type(e).__name__}: {e}')
    else:                                                                        # a missing file is already a round8_problems reason
        if mt is not None and (mt['state'] < mt['iter8'] or mt['state'] < mt['ckpt']):
            bad.append(f'seed {seed}: state.pt is older than iter-8.json / checkpoint-iter8.pt (state.pt is written last), so it is not the final state of round 8')
    return bad


def round8_problems(seed, p):
    bad = []
    for name in ('iter8', 'ckpt', 'state'):
        if not os.path.exists(p[name]):
            bad.append(f'seed {seed}: round 8 is not complete, {p[name]} missing')
    st = None
    if os.path.exists(p['state']):
        try:
            st = read_state(p['state'])
            st.get('k')
        except Exception as e:                                       # a torn / corrupt / non-dict state.pt is a refusal reason, not a crash
            st = None
            bad.append(f'seed {seed}: {p["state"]} cannot be read: {type(e).__name__}: {e}')
    if st is not None:
        if st.get('k') != 8:
            bad.append(f'seed {seed}: state.pt says k = {st.get("k")}, not 8 (training has not finished; state.pt is written last)')
        if (st.get('run_seed'), st.get('day_offset')) != (RUN_SEED[seed], DAY_OFFSET):
            bad.append(f'seed {seed}: state.pt is run seed {st.get("run_seed")} / day offset {st.get("day_offset")}, not {RUN_SEED[seed]} / {DAY_OFFSET}')
        if os.path.normpath(str(st.get('parent'))).split(os.sep)[-3:] != ['s%d' % seed, 'n64000', 'checkpoint.pt']:
            bad.append(f'seed {seed}: state.pt parent {st.get("parent")!r} is not the n64000 checkpoint of this seed')
    return bad + training_stopped_problems(seed, p)


def gate(root):
    """-> (problems, indicator). The round-4 leading indicator recomputed from rounds 3 and 4 of both seeds (no cache); STOP or unfinished refuses.

    Every read failure (gwls_report.READ_ERRORS) and every round-3/4 row whose ratio_ok is False (or None where the indicator uses the ratio, see
    gwls_report.ratio_problems) is a listed refusal string, never a crash and never read past."""
    errors = []
    rows = gwls_report.build_rows(root, SEEDS, rounds=(3, 4), errors=errors)        # unreadable / inconsistent rounds become strings, all of them listed
    try:
        ratio_bad = gwls_report.ratio_problems(rows)
    except gwls_report.READ_ERRORS as e:
        ratio_bad = [f'ratio_w cross-check cannot be evaluated: {type(e).__name__}: {e}']
    try:
        ind = gwls_report.indicator(rows, gwls_report.REF)
    except gwls_report.READ_ERRORS as e:
        errors.append(f'round-4 leading indicator cannot be computed: {type(e).__name__}: {e}')
        ind = None
    if errors:
        allbad = errors + ratio_bad
        return [f'round-4 leading indicator: {x}' for x in allbad], dict(branch=None, note='; '.join(allbad))
    if ratio_bad:                                                                    # readable, but a row's ratio cannot be trusted: refuse, keep the branch for display
        return [f'round-4 leading indicator: {x}' for x in ratio_bad], ind
    if ind['branch'] is None:
        return [f'round-4 leading indicator cannot be read: {ind["note"]}'], ind
    if ind['branch'] != 'CONTINUE':
        return [f'round-4 leading indicator is {ind["branch"]} (per-seed reading of the start record): {json.dumps(ind["per_seed"])}; no sealed read for a stopped run'], ind
    return [], ind


def exists_strict(path):
    """True/False for present/absent; any other failure to look (permissions, I/O) raises, so the caller refuses (fail closed)."""
    try:
        os.stat(path)
        return True
    except FileNotFoundError:
        return False


def previous_read_problems(P, root, persist_dir):
    """N1: a record of a previous sealed read (a score-sample.json or final.json in the persist dir, a final.json or read-record.json in the root; the
    root's own score-sample.json is checked with the other results) refuses a new play. Unreadable locations are refusals too."""
    bad = []
    cands = [os.path.join(root, 'final.json'), P[SEEDS[0]]['record']]
    cands += [os.path.join(persist_dir, 'final.json')] + [os.path.join(persist_dir, f's{s}', 'score-sample.json') for s in SEEDS]
    for c in cands:
        try:
            if exists_strict(c):
                bad.append(f'a record of a previous sealed read exists: {c}; no second read')
        except OSError as e:
            bad.append(f'{c} cannot be examined for a previous sealed read: {type(e).__name__}: {e}')
    return bad


def cap_problems():
    """N3: before playing, the episode cap the scorer will use (game/constants.json, via play.load_constants) must be arm C's."""
    try:
        from game import play
        cap = play.load_constants()[0]['episode_cap']
    except Exception as e:
        return [f'game/constants.json episode_cap cannot be read: {type(e).__name__}: {e}']
    if cap != ARM_C_CAP or type(cap) is bool:
        return [f'game/constants.json episode_cap is {cap!r}, arm C was played with {ARM_C_CAP}; the scorer would not make a like-for-like read']
    return []


def play_problems(P, root, arm_c_bad, check_locks=True, persist_dir=None):
    """check_locks=False only on the play path, which by then holds the locks itself (acquire_locks) and so has already refused on any earlier one.
    persist_dir=None means the default PERSIST_DIR (never skipped)."""
    bad = list(arm_c_bad)
    bad += previous_read_problems(P, root, PERSIST_DIR if persist_dir is None else persist_dir)
    bad += cap_problems()
    for s, p in P.items():
        bad += round8_problems(s, p)
        if os.path.exists(p['out']):
            bad.append(f'seed {s}: a sealed result already exists: {p["out"]}')
        if check_locks and os.path.exists(p['lock']):
            bad.append(f'seed {s}: an earlier scoring attempt left {p["lock"]}')
    g, ind = gate(root)
    return bad + g, ind


def acquire_locks(P):
    """Atomically create each seed's score-started.lock (O_CREAT|O_EXCL). -> (held, problems). If any acquisition fails, the locks this call created are
    released again (only those) and the problems say why; the caller then plays nothing. A lock that already exists (an earlier or a concurrent
    attempt) is never taken over."""
    held, bad = [], []
    for s, p in P.items():
        try:
            fd = os.open(p['lock'], os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            bad.append(f'seed {s}: {p["lock"]} already exists (an earlier or a concurrent scoring attempt); nothing is played, the lock is left as it is')
            continue
        except OSError as e:
            bad.append(f'seed {s}: the lock {p["lock"]} cannot be created: {type(e).__name__}: {e}')
            continue
        try:
            os.write(fd, f'sealed scoring started by pid {os.getpid()}; delete only on a decision\n'.encode())
        finally:
            os.close(fd)
        held.append(p['lock'])
    if bad:
        release_locks(held)
        held = []
    return held, bad


def release_locks(held):
    for path in held:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


def result_identity_problems(seed, p, m):
    """Problems (strings) unless `m`, the parsed result file of `seed`, is the sealed read of exactly this root's checkpoint-iter8.pt on the 100 sealed worlds."""
    if not isinstance(m, dict):
        return [f'seed {seed}: the result file is not a JSON object']
    bad = []
    ck = m.get('ckpt')
    try:
        same = isinstance(ck, str) and os.path.realpath(ck) == os.path.realpath(p['ckpt'])
    except (OSError, ValueError):
        same = False
    if not same:
        bad.append(f'seed {seed}: result ckpt {ck!r} is not (realpath) {os.path.realpath(p["ckpt"])}')
    for key, want in (('arm', 'model'), ('picker', 'sample'), ('temp', 1.0), ('worlds', 100)):
        if m.get(key) != want or type(m.get(key)) is bool:
            bad.append(f'seed {seed}: result {key} is {m.get(key)!r}, not {want!r}')
    if m.get('cap') != ARM_C_CAP or type(m.get('cap')) is bool:
        bad.append(f'seed {seed}: result cap is {m.get("cap")!r}, not arm C\'s {ARM_C_CAP}')
    if m.get('gate') is not None:
        bad.append(f'seed {seed}: result gate is {m.get("gate")!r}, not arm C\'s None')
    pw = m.get('per_world')
    if not isinstance(pw, list) or len(pw) != 100:
        bad.append(f'seed {seed}: result has {len(pw) if isinstance(pw, list) else pw!r} per_world entries, not 100')
    else:
        seeds = [w.get('seed') if isinstance(w, dict) else None for w in pw]
        if any(type(x) is not int for x in seeds) or sorted(seeds) != SEALED_SEEDS:
            bad.append(f'seed {seed}: result per_world seeds are not the sealed seeds {SEALED_SEEDS[0]}-{SEALED_SEEDS[-1]} exactly once each')
    return bad


SHA_RX = re.compile(r'^[0-9a-f]{64}$')


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def write_json_atomic(path, obj):
    tmp = f'{path}.{os.getpid()}.tmp'
    with open(tmp, 'w') as f:
        json.dump(obj, f, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def fs_now_ns(directory):
    """The file system's own clock now (the mtime of a file made now): result mtimes are compared with it, so a coarse kernel timestamp cannot read as 'earlier'."""
    fd, tmp = tempfile.mkstemp(dir=directory, prefix='.clock-')
    try:
        return os.fstat(fd).st_mtime_ns
    finally:
        os.close(fd)
        os.remove(tmp)


def write_start_record(P):
    """N4: called with the locks held, before the scorers start: per seed the sha256 and mtime_ns of checkpoint-iter8.pt, and the start time. Atomic."""
    path = P[SEEDS[0]]['record']
    rec = dict(version=1, start_ns=fs_now_ns(os.path.dirname(path)), started_wall_ns=time.time_ns(), pid=os.getpid(), seeds={})
    for s, p in P.items():
        rec['seeds'][str(s)] = dict(ckpt=os.path.realpath(p['ckpt']), ckpt_sha256=sha256_file(p['ckpt']), ckpt_mtime_ns=os.stat(p['ckpt']).st_mtime_ns)
    write_json_atomic(path, rec)
    return rec


def complete_record(P):
    """N4: after the scorers exited 0: add each result file's sha256 to the record (atomic). Raises OSError / ValueError when it cannot be done."""
    path = P[SEEDS[0]]['record']
    with open(path) as f:
        rec = json.load(f)
    for s, p in P.items():
        rec['seeds'][str(s)]['result_sha256'] = sha256_file(p['out'])
    write_json_atomic(path, rec)
    return rec


def record_problems(seed, p, result_sha, result_mtime_ns):
    """N4: the identity of the result beyond its own metadata. Needs a complete read-record.json that matches the checkpoint on disk now and the result."""
    path = p['record']
    if not os.path.exists(path):
        return [f'seed {seed}: no read-record.json ({path}); the result cannot be tied to a sealed read of this checkpoint']
    try:
        with open(path) as f:
            rec = json.load(f)
    except gwls_report.READ_ERRORS as e:
        return [f'seed {seed}: {path} cannot be read: {type(e).__name__}: {e}']
    isint = lambda x: type(x) is int
    e = rec.get('seeds', {}).get(str(seed)) if isinstance(rec, dict) and isinstance(rec.get('seeds'), dict) else None
    if not (isinstance(e, dict) and isint(rec.get('start_ns')) and isint(e.get('ckpt_mtime_ns'))
            and all(isinstance(e.get(k), str) and SHA_RX.match(e.get(k)) for k in ('ckpt_sha256', 'result_sha256'))):
        return [f'seed {seed}: read-record.json is incomplete (needs start_ns and, for seed {seed}, ckpt_sha256, ckpt_mtime_ns, result_sha256)']
    bad = []
    try:
        if sha256_file(p['ckpt']) != e['ckpt_sha256']:
            bad.append(f'seed {seed}: checkpoint-iter8.pt sha256 differs from the one recorded when the sealed read started')
        if os.stat(p['ckpt']).st_mtime_ns != e['ckpt_mtime_ns']:
            bad.append(f'seed {seed}: checkpoint-iter8.pt mtime differs from the one recorded when the sealed read started')
    except OSError as ex:
        bad.append(f'seed {seed}: checkpoint cannot be checked against the read record: {type(ex).__name__}: {ex}')
    if result_sha != e['result_sha256']:
        bad.append(f'seed {seed}: the result file sha256 differs from the one recorded when the scorer exited (the file was changed)')
    if result_mtime_ns < rec['start_ns']:
        bad.append(f'seed {seed}: the result file is older than the start of the sealed read (not written by it)')
    return bad


def load_result(seed, p):
    """-> (parsed result file or None, [problems]) incl. its identity (metadata and read record); every read failure is a string."""
    if not os.path.exists(p['out']):
        return None, [f'seed {seed}: no result file {p["out"]}']
    try:
        with open(p['out'], 'rb') as f:
            raw = f.read()
        mt = os.stat(p['out']).st_mtime_ns
        m = json.loads(raw)
    except gwls_report.READ_ERRORS as e:
        return None, [f'seed {seed}: the result file {p["out"]} cannot be read: {type(e).__name__}: {e}']
    bad = result_identity_problems(seed, p, m) + record_problems(seed, p, hashlib.sha256(raw).hexdigest(), mt)
    return (None if bad else m), bad


def analyze_problems(P, root, arm_c_bad):
    """--analyze-only: the same gate, round-8 completeness (+ training-stopped proof), arm C checks and lock rule as playing, plus each result's identity.
    -> (problems, results {seed: parsed})."""
    bad = list(arm_c_bad)
    results = {}
    for s, p in P.items():
        bad += round8_problems(s, p)
        if os.path.exists(p['lock']):
            bad.append(f'seed {s}: {p["lock"]} exists (an unresolved scoring attempt); not analysed')
        results[s], b = load_result(s, p)
        bad += b
    g, _ = gate(root)
    return bad + g, results


def persist(files, root, persist_dir):
    for src in files:
        dst = os.path.join(persist_dir, os.path.relpath(src, root))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        print('persisted', dst)


# ---------- selftest ----------

def synthetic_arm_c(seed):
    """A per-world arm C dict (100 worlds) with exactly the recorded means of `seed`; for the selftest and the tests."""
    rec = ARM_C_RECORD[seed]
    n_nh, n_tot = round(rec['nonhabit'] * 100), round(rec['total'] * 100)
    n_stone = round(rec['stone'])
    base, extra = divmod(n_nh, 100)                      # extra worlds get one more non-habit unlock
    names = ['collect_wood', 'place_table', 'collect_drink', 'eat_cow', 'defeat_zombie', 'make_wood_pickaxe', 'make_wood_sword', 'collect_coal']
    habit_total = n_tot - n_nh
    worlds = []
    for i in range(100):
        k = base + (1 if i < extra else 0)
        h = habit_total // 100 + (1 if i < habit_total % 100 else 0)
        unlocks = [[j, names[j % len(names)] if j < len(names) else f'x{j}'] for j in range(k)] + [[50 + j, 'wake_up'] for j in range(h)]
        worlds.append(dict(seed=7000000 + i, unlocks=unlocks, n_unlocks=float(len(unlocks)), ach_rate=dict(collect_stone=1.0 if i < n_stone else 0.0)))
    return dict(arm='model', ckpt=f'/x/glprobe/run/s{seed}/n64000/checkpoint.pt', gate=None, picker='sample', ppo_picker=None, temp=1.0, worlds=100, cap=1000,
                per_world=worlds, mean_unlocks=round(sum(w['n_unlocks'] for w in worlds) / 100, 3))


def selftest():
    def fake(nh, tot, st):
        return dict(nonhabit=dict(diff=nh[0], lo=nh[1], hi=nh[1] + 1), total=dict(diff=tot, lo=0, hi=0), stone_points=st)
    good = fake((0.3, 0.01), 0.5, 10.0)
    assert verdict({200: good, 201: good}) == 'PASS'
    assert verdict({200: good, 201: fake((0.3, 0.0), 0.5, 10.0)}) == 'NO VERDICT'           # CI low must be > 0
    assert verdict({200: good, 201: fake((0.29, 0.1), 0.5, 10.0)}) == 'NO VERDICT'
    assert verdict({200: good, 201: fake((0.3, 0.01), 0.49, 10.0)}) == 'NO VERDICT'
    assert verdict({200: good, 201: fake((0.3, 0.01), 0.5, 9.9)}) == 'NO VERDICT'
    bad = fake((-0.5, -1), -1, 0.0)
    assert verdict({200: bad, 201: bad}) == 'PROVED WRONG'
    assert verdict({200: bad, 201: fake((0.0, -1), 0, 0.0)}) == 'NO VERDICT'
    assert verdict({200: fake((0, -1), 0, -15.0), 201: fake((0.2, -1), 0, -20.0)}) == 'PROVED WRONG'
    assert verdict({200: fake((0, -1), 0, -15.0), 201: fake((0.2, -1), 0, -14.0)}) == 'NO VERDICT'
    assert verdict({200: bad, 201: fake((0, 0), 0, -15.0)}) == 'NO VERDICT'                  # one seed by non-habit, one by stone: neither "on both"
    # arm C checks: the synthetic file has the recorded means, so only the hash differs; each tamper is caught on its own
    for s in SEEDS:
        b = synthetic_arm_c(s)
        raw = json.dumps(b).encode()
        assert arm_c_problems(s, raw, b, check_hash=False) == [], arm_c_problems(s, raw, b, check_hash=False)
        assert len(arm_c_problems(s, raw, b)) == 1 and 'sha256' in arm_c_problems(s, raw, b)[0]
        for key, val, word in (('picker', 'top', 'picker'), ('temp', 0.5, 'temp'), ('ckpt', f'/x/s{s}/n32000/checkpoint.pt', 'ckpt'),
                               ('ckpt', f'/x/s{1000 - s}/n64000/checkpoint.pt', 'ckpt'), ('arm', 'random', 'arm'), ('worlds', 99, 'worlds')):
            t = dict(b, **{key: val})
            probs = arm_c_problems(s, raw, t, check_hash=False)
            assert len(probs) >= 1 and any(word in x for x in probs), (key, probs)
        w0 = b['per_world'][0]                                                                  # one world's unlocks changed: the means move off the record
        t = dict(b, per_world=[dict(w0, unlocks=w0['unlocks'] + [[99, 'collect_diamond']], n_unlocks=w0['n_unlocks'] + 1)] + b['per_world'][1:])
        assert any('means' in x for x in arm_c_problems(s, raw, t, check_hash=False))
    assert any('means' in x for x in arm_c_problems(200, b'', dict(synthetic_arm_c(200), mean_unlocks=6.6), check_hash=False))
    # the round-4 gate: STOP and unfinished both refuse; CONTINUE passes (indicator itself is exercised in game/tests/test_gwls.py)
    row = lambda r, nh, ratio: dict(round=r, games=400, nonhabit_sum=nh, ratio_w_exact=ratio)
    ok = {200: [row(3, 2300, 2.0), row(4, 2300, 2.0)], 201: [row(3, 2300, 2.0), row(4, 2300, 2.0)]}
    assert gwls_report.indicator(ok, gwls_report.REF)['branch'] == 'CONTINUE'
    stop = {200: [row(3, 2300, 0.4), row(4, 2300, 0.5)], 201: [row(3, 2300, 0.4), row(4, 2300, 0.4)]}
    assert gwls_report.indicator(stop, gwls_report.REF)['branch'] == gwls_report.STOP
    # every path handed to the scorer child (cwd = REPO_ROOT) is absolute, whatever the cwd and a relative --root
    pp = paths('some/rel/root', 'rel/armc', 200)
    assert all(os.path.isabs(v) for v in pp.values()) and all(os.path.isabs(x) for x in (command(pp)[command(pp).index('--ckpt') + 1], command(pp)[command(pp).index('--out') + 1]))
    print('selftest ok')


def parse_args(argv=None):
    """The command line, with --root / --arm-c / --persist-dir made absolute here, once, so nothing later depends on the cwd."""
    ap = argparse.ArgumentParser(description='GW-LS: the one sealed read at round 8 and the sealed marks.')
    ap.add_argument('--root', default=os.path.join(SCRATCH, 'gwls'))
    ap.add_argument('--arm-c', default=os.path.join(SCRATCH, 'glprobe'))
    ap.add_argument('--persist-dir', default=PERSIST_DIR, help='where the score files and final.json are copied (no git operation)')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--analyze-only', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    a = ap.parse_args(argv)
    a.root, a.arm_c, a.persist_dir = (os.path.abspath(x) for x in (a.root, a.arm_c, a.persist_dir))
    return a


def main(argv=None):
    a = parse_args(argv)
    if a.selftest:
        return selftest()
    P = {s: paths(a.root, a.arm_c, s) for s in SEEDS}
    arm_c, arm_c_bad = {}, []
    for s, p in P.items():
        arm_c[s], bad = load_arm_c(p, s)
        arm_c_bad += bad
    if a.dry_run:
        for s, p in P.items():
            print(s, 'ckpt', p['ckpt'], 'exists' if os.path.exists(p['ckpt']) else 'MISSING', '| result', 'EXISTS (would refuse)' if os.path.exists(p['out']) else 'absent',
                  '| lock', 'EXISTS (would refuse)' if os.path.exists(p['lock']) else 'absent')
            print('  would run:', ' '.join(command(p)))
            b = arm_c[s]
            if b is not None:
                try:
                    print('  arm C: total', round(b['mean_unlocks'], 3), 'non-habit', round(sum(map(nonhabit, b['per_world'])) / b['worlds'], 3),
                          'stone %', round(sum(map(stone, b['per_world'])) / b['worlds'], 1))
                except gwls_report.READ_ERRORS as e:                              # a malformed arm C file is a listed problem, not a traceback
                    arm_c_bad.append(f'arm C seed {s}: {p["base"]} numbers cannot be printed: {type(e).__name__}: {e}')
        bad, ind = play_problems(P, a.root, arm_c_bad, persist_dir=a.persist_dir)
        print('round-4 branch:', ind['branch'] if ind['branch'] else f'unavailable ({ind["note"]})')
        if bad:
            print('DRY RUN: WOULD REFUSE to play, %d problem(s):' % len(bad))
            for x in bad:
                print('  -', x)
            sys.exit(1)
        print('DRY RUN: all preconditions hold; it would play.')
        return
    if a.analyze_only:
        bad, results = analyze_problems(P, a.root, arm_c_bad)
        if bad:
            sys.exit('refusing to analyse, %d problem(s):\n  - ' % len(bad) + '\n  - '.join(bad))
    else:
        held, bad = acquire_locks(P)                                                       # atomic, BEFORE any check of an existing result / lock
        if bad:
            sys.exit('refusing to play the sealed worlds, %d problem(s):\n  - ' % len(bad) + '\n  - '.join(bad))
        try:
            bad, _ = play_problems(P, a.root, arm_c_bad, check_locks=False, persist_dir=a.persist_dir)
        except BaseException:
            release_locks(held)                                                            # nothing played yet
            raise
        if bad:
            release_locks(held)                                                            # only the locks this invocation created; nothing was played
            sys.exit('refusing to play the sealed worlds, %d problem(s):\n  - ' % len(bad) + '\n  - '.join(bad))
        try:
            write_start_record(P)                                                          # N4: checkpoint sha256 / mtime_ns and the start time, before anything is played
        except BaseException as e:
            release_locks(held)                                                            # nothing played yet
            sys.exit(f'the read record cannot be written, nothing is played: {type(e).__name__}: {e}')
        env = dict(os.environ, PYTHONPATH=REPO_ROOT)
        procs = []
        try:
            for p in P.values():
                procs.append(subprocess.Popen(command(p), env=env, cwd=REPO_ROOT))
        except BaseException as e:
            if not procs:
                release_locks(held)                                                        # the first scorer never started: nothing was played
                with contextlib.suppress(FileNotFoundError):
                    os.remove(P[SEEDS[0]]['record'])                                       # ... so the start record is void too
            for pr in procs:
                pr.wait()
            sys.exit(f'game.score could not be started: {type(e).__name__}: {e}' + (' (locks kept: a scorer is running)' if procs else ''))
        codes = [pr.wait() for pr in procs]
        assert codes == [0, 0], f'game.score failed: {codes} (locks kept: no re-play without a decision)'
        try:
            complete_record(P)                                                             # N4: each result's sha256, atomically
            persist([p['out'] for p in P.values()] + [P[SEEDS[0]]['record']], a.root, a.persist_dir)      # straight after the sealed read
        except (OSError, ValueError) as e:
            sys.exit(f'the sealed read was played, but its record cannot be completed / persisted ({type(e).__name__}: {e}); locks kept, unresolved')
        results, bad = {}, []
        for s, p in P.items():
            results[s], b = load_result(s, p)                                              # the same identity check on the fresh result
            bad += b
        if bad:                                                                            # N2: the locks stay, the attempt is unresolved
            sys.exit('the sealed read was played, but its result fails the identity check, no marks computed, locks kept (unresolved), %d problem(s):\n  - ' % len(bad) + '\n  - '.join(bad))
    per_seed = {}
    for s, p in P.items():
        try:
            per_seed[s] = compare(results[s], arm_c[s])
        except gwls_report.READ_ERRORS as e:                                                 # a malformed per_world entry: a clear exit, not a traceback
            sys.exit(f'seed {s}: the result cannot be compared with arm C: {type(e).__name__}: {e}')
        c = per_seed[s]
        print(f'seed {s}: total {c["mean_total"][0]:.3f} vs C {c["mean_total"][1]:.3f} diff {c["total"]["diff"]:+.3f} [{c["total"]["lo"]:+.3f}, {c["total"]["hi"]:+.3f}] | '
              f'non-habit {c["mean_nonhabit"][0]:.3f} vs {c["mean_nonhabit"][1]:.3f} diff {c["nonhabit"]["diff"]:+.3f} [{c["nonhabit"]["lo"]:+.3f}, {c["nonhabit"]["hi"]:+.3f}] | '
              f'stone {c["stone_pct"][0]:.1f}% vs {c["stone_pct"][1]:.1f}% diff {c["stone_points"]:+.1f} points')
    v = verdict(per_seed)
    print('VERDICT:', v)
    fpath = os.path.join(a.root, 'final.json')
    with open(fpath, 'w') as f:
        json.dump(dict(per_seed={str(k): x for k, x in per_seed.items()}, verdict=v), f, indent=1)
    persist([fpath] + [p['out'] for p in P.values()], a.root, a.persist_dir)
    if not a.analyze_only:
        release_locks(held)                                                                # N2: only now - identity passed, record complete, results and final.json persisted


if __name__ == '__main__':
    main()
