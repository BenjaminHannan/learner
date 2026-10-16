"""prof_launch.py: prof_train.py with the launch-bound study's new arms registered. A thin runner: it changes NOTHING in prof_train.py; it adds variants to prof_train's registries
(VARIANTS, SETUP_ORDER, AB_CPU_RULE, AB_ARM_ORDER) and calls prof_train.main(argv) with your arguments, so the existing sections (abequiv, abbench, profiler, syncs, breakdown, bench ...)
run the new arms with the same code and the same options as the old ones.

  python prof_launch.py --arm B3G2 --rung 3M --accum 4 --data $POOL --pkg-root $S --caps $S/custom_io/g8a/caps_b3g2.json --sections abequiv --ab-variants defer --out out/ab_equiv_defer.json
  python prof_launch.py <same> --sections abbench --ab-variants defer --ab-accums '' --dph 0.46 --ab-equiv-json out/ab_equiv_defer.json --out out/ab_bench_defer.json
  python prof_launch.py <same> --variant defer --sections profiler,syncs --out out/defer_profile.json

New arms (all of them go through prof_train's own machinery; none edits custom_io):
  defer         defer.py: the deferred batched writer (attack A). NUMERICS-CHANGING ('near').
  <the classes of exact_arms.NEW_VARIANTS>   if a file exact_arms.py sits in this folder (another agent writes it): `import exact_arms`, then every Variant class in its list NEW_VARIANTS is
                registered under its `name`. A class may set `ab_cpu_rule` ('bit_exact', 'equal_to_rounding' or 'bar_only'; default 'bar_only', the weakest) for mark 6's CPU clause.
                A failing import is printed loudly and skipped (the other arms still run).

How a registered arm is wired:
  VARIANTS[name] = class; SETUP_ORDER: after 'nosync' (before 'baseline', so it patches the model before the pad / sort / front variants; a class may name another anchor in `setup_after`);
  AB_CPU_RULE[name] = the class's ab_cpu_rule; AB_ARM_ORDER: after 'unfused', before the accum rows, so `--ab-variants` and `--ab-accums` defaults now run the new arms too (the cheap wins first,
  the accum rows last; pass --ab-variants to choose).

CPU rule of defer (mark 6, Amendment 1's CPU fp32 clause): 'bar_only'. Reason: the arm is numerics-changing by construction (batched GEMMs, another padded call width, one-shot gradient
reductions), so 'bit_exact' is false and 'equal_to_rounding' (relative gradient and loss difference <= 1e-6) is a claim about rounding that only a CPU fp32 measurement can make; test_defer.py T1
measures it (shown: loss rel diff and gradient relative L2 are reported there). The registered clause is therefore the bar alone (loss rel diff <= 1e-4 and gradient cosine >= 0.9999), read in
bf16 on the box where it is run; the CPU fp32 numbers are shown for information beside it.
"""
import importlib, os, sys, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
PROFDIR = os.path.normpath(os.path.join(HERE, '..', 'prof'))
for p in (PROFDIR, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)
import prof_train as prof                                                    # noqa: E402
import defer                                                                  # noqa: E402

CPU_RULES = ('bit_exact', 'equal_to_rounding', 'bar_only')
EXPLICIT_RULE = dict(defer='bar_only')


def _insert_after(seq, name, anchor):
    seq = tuple(seq)
    if name in seq:
        return seq
    if anchor in seq:
        i = seq.index(anchor) + 1
        return seq[:i] + (name,) + seq[i:]
    return seq + (name,)


def register(classes, say=print):
    """Add Variant classes to prof_train's registries (idempotent). A different class under a name already taken is an error (SystemExit), the same class again is a no-op."""
    done = []
    for cls in classes:
        n = cls.name
        old = prof.VARIANTS.get(n)
        if old is not None and old is not cls and getattr(old, '__qualname__', None) != cls.__qualname__:
            raise SystemExit(f'prof_launch: variant name {n!r} is already registered by {old!r}; {cls!r} cannot take it')
        prof.VARIANTS[n] = cls
        prof.SETUP_ORDER = _insert_after(prof.SETUP_ORDER, n, getattr(cls, 'setup_after', 'nosync'))
        rule = EXPLICIT_RULE.get(n) or getattr(cls, 'ab_cpu_rule', None) or 'bar_only'
        if rule not in CPU_RULES:
            raise SystemExit(f'prof_launch: {n}: ab_cpu_rule {rule!r} is not one of {CPU_RULES}')
        prof.AB_CPU_RULE[n] = rule
        prof.AB_ARM_ORDER = _insert_after(prof.AB_ARM_ORDER, n, 'unfused')
        done.append(n)
    return done


def load_exact_arms(say=print):
    """`import exact_arms` from this folder -> its NEW_VARIANTS (a list of Variant classes), or [] when there is no such module. An import that fails for any other reason is printed, not fatal."""
    try:
        mod = importlib.import_module('exact_arms')
    except ModuleNotFoundError as e:
        if e.name == 'exact_arms':
            return []
        say(f'!!!!!! prof_launch: exact_arms.py exists but could not be imported ({e!r}); its arms are NOT registered')
        return []
    except Exception as e:                                                   # noqa: BLE001
        say(f'!!!!!! prof_launch: exact_arms.py raised on import ({e!r}); its arms are NOT registered\n' + traceback.format_exc())
        return []
    arms = list(getattr(mod, 'NEW_VARIANTS', []))
    if not arms:
        say('prof_launch: exact_arms imported but NEW_VARIANTS is empty or missing')
    return arms


def register_all(say=print):
    names = register(defer.NEW_VARIANTS, say)
    names += register(load_exact_arms(say), say)
    return names


def main(argv=None):
    names = register_all()
    print(f'prof_launch: registered {names}; setup order {prof.SETUP_ORDER}; ab arm order {prof.AB_ARM_ORDER}', flush=True)
    return prof.main(argv)


if __name__ == '__main__':
    main()
