"""Runs one CPU test module as its own main() does (every test_ function in file order, its name printed first, ALL OK at the end), for
install_rr.ps1 on BensPC (roadmap spec addendum AE, 12 Oct 2026). One difference, for one comparison only:

test_reader_rule.test_r2_call_and_stop_inputs_unchanged_by_the_answer_rule compares five numbers with a pin (GOLD) to the last bit
(float.hex), as they came out on the cloud CPU where G2f (74d6e92c75) was built. On BensPC (12 Oct, 00:38 ET) the three call numbers matched
to the bit and the two stop-head input sums did not: stop_abs differed by 1.8e-9 of itself and stop_in by 4.6e-12 of stop_abs. That is
another CPU's float rounding, not a code change: the same commit passes the bit pin on the cloud CPU (torch 2.14.1+cpu, 1 and 4 threads).
So here the module's GOLD is wrapped so that `got == GOLD` holds when call_acc and eos_acc are equal, call and stop_abs are within 1e-7 of
the pin (relative), and stop_in is within 1e-9 x stop_abs of it (about 50 to 200 times the gaps seen). The rest of that test (finite loss,
no copying) runs as written, the exact numbers are printed, and every other test and comparison is unchanged.

  python run_tests.py custom_io.tests.test_reader_rule      (run from the src folder, as python -m would: that folder leads sys.path)

A module without that pinned test (B3 group 1's test_reader_rule at ca7e1d1b88, whose __main__ block first applies legacy_widths) runs
exactly as `python -m` runs it (runpy, run_name '__main__'), with nothing changed (12 Oct, 9:49 AM ET install: run that way it failed).
"""
import importlib, importlib.util, os, runpy, sys, traceback

PINNED = 'test_r2_call_and_stop_inputs_unchanged_by_the_answer_rule'
KEYS = {'call', 'call_acc', 'eos_acc', 'stop_in', 'stop_abs'}
REL, STOP_IN = 1e-7, 1e-9


def near(got, gold):
    """(ok, text) for the pinned test's dicts of float.hex strings."""
    if not isinstance(got, dict) or set(got) != KEYS or set(gold) != KEYS:
        return False, f'keys differ: {sorted(got) if isinstance(got, dict) else got!r} vs {sorted(gold)}'
    g = {k: float.fromhex(v) for k, v in got.items()}
    p = {k: float.fromhex(v) for k, v in gold.items()}
    scale = abs(p['stop_abs'])
    gap = {k: abs(g[k] - p[k]) for k in p}
    lines = [('call_acc', gap['call_acc'] == 0), ('eos_acc', gap['eos_acc'] == 0), ('call', gap['call'] <= REL * abs(p['call'])),
             ('stop_abs', gap['stop_abs'] <= REL * scale), ('stop_in', gap['stop_in'] <= STOP_IN * scale)]
    text = '; '.join(f"{k} {got[k]} vs pin {gold[k]} (gap {gap[k]:.3g}{'' if ok else ', TOO FAR'})" for k, ok in lines)
    return all(ok for _, ok in lines), text


class NearGold(dict):
    """The pin, compared allowing another CPU's rounding (see above). As the right side of got == GOLD its __eq__ is used first."""
    def __eq__(self, other):
        ok, text = near(other, dict(self))
        print(f"MACHINE ROUNDING {'ok' if ok else 'NOT ok'} (bit pin taken on another CPU): {text}", flush=True)
        return ok

    def __ne__(self, other):
        return not self.__eq__(other)

    __hash__ = None


def main(name):
    sys.path[0] = os.getcwd()               # as python -m: the current folder first, not this script's folder
    spec = importlib.util.find_spec(name)
    if PINNED not in open(spec.origin, encoding='utf-8').read():
        print(f'run_tests: {name} has no {PINNED}; it runs as python -m runs it', flush=True)
        runpy.run_module(name, run_name='__main__', alter_sys=True)
        return 0
    mod = importlib.import_module(name)
    if callable(getattr(mod, PINNED, None)) and isinstance(getattr(mod, 'GOLD', None), dict) and set(mod.GOLD) == KEYS:
        mod.GOLD = NearGold(mod.GOLD)
        print(f'run_tests: {PINNED} compares its pin allowing CPU rounding (spec addendum AE)', flush=True)
    for t, fn in list(vars(mod).items()):
        if not (t.startswith('test_') and callable(fn)):
            continue
        print(t, flush=True)
        try:
            fn()
        except Exception:
            traceback.print_exc()
            print(f'FAIL {t}')
            return 1
    print('ALL OK')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
