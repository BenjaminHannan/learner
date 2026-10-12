"""python3 -m custom_io.tests.test_b3at   (CPU, stub Gemma; OMP_NUM_THREADS=2; about an hour: the toy trains, the B3G2 modules re-run, the speed run does 100 updates)
The ONE module that runs the nine sealed AT-0 checks (architecture/AT-BUILD-SPEC-2026-10-11.md sec. 6; big-run PLAN.md sixth Addendum item (4)) in order, each printing exactly one line
'ok AT-0 (k) <what was shown, with the numbers>' (or 'FAIL AT-0 (k) ...'), then 'ALL OK'. A failing check does not stop the later ones (the run is long): every failure is printed and the
module ends with a non-zero exit and no 'ALL OK'. Nothing here is weakened: each check is the test of the module that owns it, called as written.
  (i)    replies enter only through the reader                     test_b3at_core.test_replies_only_through_read_texts
  (ii)   the talker sees only thoughts                             test_b3at_core.test_talker_sees_only_thoughts
  (iii)  teacher-forced and free runs agree (>= 99% of lines)      test_b3at_toy (a tiny b3at trained on the toy two-call task), plus the machinery tests of the same
                                                                   loop: teacher-forced thinker == free-run thinker, every parameter gets a gradient, call_evals
  (iv)   the lesions work (calculator-off and the reply swap       test_b3at_toy (the same trained toy), plus test_b3at_core's lesion / oracle / scripted-run tests
         each change the toy's outputs)
  (v)    the ST1 hooks keep their signatures                       test_b3at_core.test_st1_hooks (the old ST1 unit tests run under (vi): test_st1)
  (vi)   the pre-PC list that applies on CPU                       every B3G2 module as a subprocess (test_writer, test_b3g2, test_reader_rule, test_b3g2_run, test_st1,
                                                                   test_talk_rounds, test_talker_report) plus test_g2_input and test_g8a; each one's last line is reported
  (vii)  every cap in the turn loop has a counter, all read 0      test_b3at_core.test_counters and test_teacher_forcing_caps_and_keep, plus test_b3at_run.test_train_py
                                                                   (train.py --model b3at end to end: every capcount fault counter 0 on a tiny run)
  (viii) trained count at 3M within 2% of g2c3s                    test_b3at_run.test_3m_count (printed with its breakdown)
  (ix)   seconds per update and peak memory                        custom_io/at0_speed.py, 100 updates at 3M on CPU: REPORTED, NOT GATED
Ben's rules the checks stand on: tool replies reach the model ONLY as text read by the reader (read_texts: Gemma + letter window) [(i)]; the talker reads ONLY the thinker's vectors, for calls
and answers alike [(ii)]; everything inside the model is learned (hand-written code only inside tools the model calls) [(iii), (iv)]; no training target is ever truncated [(vii)].
Dev aids (the sealed run sets neither): AT0_CHECKS=i,ii,... runs only those checks; AT0_SPEED_UPDATES=N sets the number of updates of (ix) (default 100, the sealed number)."""
import contextlib
import io
import os
import re
import subprocess
import sys
import time
import traceback
import torch
from custom_io.tests import test_b3at_core as CORE
from custom_io.tests import test_b3at_run as RUN
from custom_io.tests import test_b3at_toy as TOY

PRE_PC = ('test_writer', 'test_b3g2', 'test_reader_rule', 'test_b3g2_run', 'test_st1', 'test_talk_rounds', 'test_talker_report')       # AT-BUILD-SPEC sec. 6 item 6 (every B3G2 module)
ALSO = ('test_g2_input', 'test_g8a', 'test_no_plug', 'test_b3')       # not in the list, but they read code this build touched (g2 input path; configs / job / caps; the no-plug front; the B3 base)
ROMAN = ('i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix')
TOY_OUT = {}                                            # the one toy run feeds (iii) and (iv)


def called(*fns):
    """Run the given test functions in order with their stdout captured; return (their 'ok ...' lines with the 'ok ' dropped, every other printed line)."""
    oks, rest = [], []
    for f in fns:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            f()
        for ln in buf.getvalue().splitlines():
            (oks if ln.startswith('ok ') else rest).append(ln[3:] if ln.startswith('ok ') else ln.strip())
    return oks, rest


def joined(oks):
    return ' || '.join(re.sub(r'^AT-0 \([a-z]+\):? ', '', x) for x in oks)


def check_i():
    return joined(called(CORE.test_replies_only_through_read_texts)[0])


def check_ii():
    return joined(called(CORE.test_talker_sees_only_thoughts)[0])


def toy_run():
    """One run of the toy test (AT-0 (iii) and (iv) both live in it). It raises at its end when a collected check failed; the printed ok / FAIL lines say which."""
    if TOY_OUT:
        return TOY_OUT
    buf = io.StringIO()
    err = None
    t = time.time()
    try:
        with contextlib.redirect_stdout(buf):
            TOY.test_toy_at0()
    except BaseException as e:                          # noqa: BLE001 (a failed assert is the result; keep the printed lines)
        err = '%s: %s' % (type(e).__name__, str(e)[:600])
    TOY_OUT.update(lines=buf.getvalue().splitlines(), err=err, secs=time.time() - t)
    return TOY_OUT


def toy_pick(tag):
    """The toy test's own lines for AT-0 (iii) / (iv): (ok lines, FAIL lines)."""
    lines = toy_run()['lines']
    return [ln[3:] for ln in lines if ln.startswith('ok AT-0 (%s)' % tag)], [ln[5:] for ln in lines if ln.startswith('FAIL AT-0 (%s)' % tag)]


def check_iii():
    oks, fails = toy_pick('iii')
    t = toy_run()
    if t['err'] and not oks and not fails:
        raise AssertionError('the toy did not reach the agreement check: ' + t['err'])
    extra, _ = called(CORE.test_teacher_forced_thinker_equals_free_run, CORE.test_grads, CORE.test_call_evals_and_names)       # run even when the toy gate failed
    if fails or not oks:
        raise AssertionError(' | '.join(fails) or 'no AT-0 (iii) line from the toy')
    return joined(oks + extra)


def check_iv():
    oks, fails = toy_pick('iv')
    t = toy_run()
    if t['err'] and not oks and not fails:
        raise AssertionError('the toy did not reach the lesion check: ' + t['err'])
    extra, _ = called(CORE.test_paths_and_lesions, CORE.test_scripted_free_run)
    if fails or len(oks) < 2:
        raise AssertionError(' | '.join(fails) or 'the toy printed %d of its 2 AT-0 (iv) lines' % len(oks))
    ext = [ln for ln in t['lines'] if ln.startswith('ok extra_evals')]
    return joined(oks + extra + [e[3:] for e in ext])


def check_v():
    return joined(called(CORE.test_st1_hooks)[0])


def check_vi():
    env = dict(os.environ, OMP_NUM_THREADS='2')
    got, bad = [], []
    for mod in PRE_PC + ALSO:
        t = time.time()
        p = subprocess.run([sys.executable, '-m', 'custom_io.tests.' + mod], env=env, capture_output=True, text=True)
        lines = [ln for ln in (p.stdout + '\n' + p.stderr).splitlines() if ln.strip()]
        last = lines[-1].strip() if lines else '(no output)'
        good = p.returncode == 0 and (last.startswith('ALL OK') or (mod == 'test_g8a' and last.startswith('ok ') and not any(ln.startswith('FAIL') for ln in lines)))       # test_g8a has no ALL OK line: exit code 0 and no FAIL line
        got.append('%s: %s [rc %d, %.0fs]' % (mod, last, p.returncode, time.time() - t))
        if not good:
            bad.append('%s: %s\n%s' % (mod, last, '\n'.join(lines[-12:])))
    if bad:
        raise AssertionError('pre-PC list: ' + '; '.join(got) + '\n' + '\n'.join(bad))
    return '%d modules (the %d B3G2 modules of the list + %s), last lines: ' % (len(PRE_PC + ALSO), len(PRE_PC), ', '.join(ALSO)) + '; '.join(got)


def check_vii():
    return joined(called(CORE.test_counters, CORE.test_teacher_forcing_caps_and_keep, RUN.test_train_py)[0])


def check_viii():
    return joined(called(RUN.test_3m_count)[0])


def check_ix():
    from custom_io import at0_speed
    n = int(os.environ.get('AT0_SPEED_UPDATES', '100'))
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        at0_speed.main(['--updates', str(n), '--threads', '2'])
    last = [ln for ln in buf.getvalue().splitlines() if ln.startswith('AT-0 (ix)')]
    assert last, buf.getvalue()[-400:]
    first = [ln for ln in buf.getvalue().splitlines() if ln.startswith('b3at 3M')]
    return '%d updates; %s%s' % (n, last[-1].replace('AT-0 (ix) ', '', 1), ('; ' + first[0]) if first else '')


CHECKS = dict(zip(ROMAN, (check_i, check_ii, check_iii, check_iv, check_v, check_vi, check_vii, check_viii, check_ix)))


def main():
    torch.set_num_threads(2)
    want = [x.strip() for x in os.environ.get('AT0_CHECKS', ','.join(ROMAN)).split(',')]
    assert all(x in CHECKS for x in want), want
    t0 = time.time()
    failed = []
    for k in ROMAN:
        if k not in want:
            continue
        t = time.time()
        try:
            msg = CHECKS[k]()
            line = 'ok AT-0 (%s) %s' % (k, msg)
        except BaseException as e:                      # noqa: BLE001 (report and carry on to the next check)
            failed.append(k)
            line = 'FAIL AT-0 (%s) %s: %s' % (k, type(e).__name__, str(e).replace('\n', ' // '))
            sys.stderr.write(traceback.format_exc())
        print(re.sub(r'\s+', ' ', line) + ' [%.0fs]' % (time.time() - t), flush=True)
    if failed:
        print('FAILED AT-0 checks: %s (%.0fs)' % (', '.join(failed), time.time() - t0))
        sys.exit(1)
    print('ALL OK (%.0fs)' % (time.time() - t0))


if __name__ == '__main__':
    main()
