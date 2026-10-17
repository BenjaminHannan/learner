"""prof_launch.py: prof_train.py with the launch-bound study's new arms registered. A thin runner: it changes NOTHING in prof_train.py; it adds variants to prof_train's registries
(VARIANTS, SETUP_ORDER, AB_CPU_RULE, AB_ARM_ORDER) and calls prof_train.main(argv) with your arguments, so the existing sections (abequiv, abbench, profiler, syncs, breakdown, bench ...)
run the new arms with the same code and the same options as the old ones.

  python prof_launch.py --arm B3G2 --rung 3M --accum 4 --data $POOL --pkg-root $S --caps $S/custom_io/g8a/caps_b3g2.json --sections abequiv --ab-variants defer --out out/ab_equiv_defer.json
  python prof_launch.py <same> --sections abbench --ab-variants defer --ab-accums '' --dph 0.46 --ab-equiv-json out/ab_equiv_defer.json --out out/ab_bench_defer.json
  python prof_launch.py <same> --variant defer --sections profiler,syncs --out out/defer_profile.json

New arms (all of them go through prof_train's own machinery; none edits custom_io):
  same          the do-nothing arm (baseline under another name) for the A-A noise control.
  defer         defer.py: the deferred batched writer (attack A). NUMERICS-CHANGING ('near').

--deterministic  sets CUBLAS_WORKSPACE_CONFIG=:4096:8 before torch is imported and torch.use_deterministic_algorithms(True, warn_only=True) (kvcat's exactness check).
Every abbench run record gains started_utc / ended_utc / timed_start_utc / timed_end_utc and rounds_seq; every run writes <out>.launch.json (host CPU model, versions, switch).
  <the classes of exact_arms.NEW_VARIANTS>   if a file exact_arms.py sits in this folder (another agent writes it): `import exact_arms`, then every Variant class in its list NEW_VARIANTS is
                registered under its `name`. A class may set `ab_cpu_rule` ('bit_exact', 'equal_to_rounding' or 'bar_only'; default 'bar_only', the weakest) for mark 6's CPU clause.
                A failing import is printed loudly and skipped (the other arms still run).

How a registered arm is wired:
  VARIANTS[name] = class; SETUP_ORDER: after 'nosync' (before 'baseline', so it patches the model before the pad / sort / front variants; a class may name another anchor in `setup_after`);
  AB_CPU_RULE[name] = the class's ab_cpu_rule; AB_ARM_ORDER: after 'unfused', before the accum rows, so `--ab-variants` and `--ab-accums` defaults now run the new arms too (the cheap wins first,
  the accum rows last; pass --ab-variants to choose).

CPU rule of defer (mark 6, Amendment 1's CPU fp32 clause): 'equal_to_rounding' (relative loss difference and relative gradient L2 difference both <= prof_train.AB_ROUND_REL = 1e-6), the same
rule pad64 and pad64p have. Reason: the arm is numerics-changing by construction (batched GEMMs, another padded call width, one-shot gradient reductions), so 'bit_exact' is false, but on the
CPU in fp32 it meets the rounding rule by more than 10x (test_defer.py: loss rel diff 0 to 1e-7, gradient rel L2 7e-8 to 1.1e-7), so the weaker 'bar_only' would only let a real semantics bug of up
to 1e-4 loss / 0.9999 cosine through on the CPU. The clause is used only on a CPU fp32 run (ab_mark6 never applies it on a GPU run: there the bar alone decides, in bf16, and says so).
"""
import datetime, importlib, json, os, platform, socket, sys, time, traceback

# --deterministic (GPU-RUN-4 condition 3): must act BEFORE torch is imported (CUBLAS_WORKSPACE_CONFIG is read when CUDA/cuBLAS starts), so it is taken off argv here, first.
DETERMINISTIC = '--deterministic' in sys.argv[1:]
if DETERMINISTIC:
    sys.argv = [sys.argv[0]] + [a for a in sys.argv[1:] if a != '--deterministic']
    os.environ['CUBLAS_WORKSPACE_CONFIG'] = ':4096:8'

HERE = os.path.dirname(os.path.abspath(__file__))
PROFDIR = os.path.normpath(os.path.join(HERE, '..', 'prof'))
for p in (PROFDIR, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)
import prof_train as prof                                                    # noqa: E402
import defer                                                                  # noqa: E402

CPU_RULES = ('bit_exact', 'equal_to_rounding', 'bar_only')
EXPLICIT_RULE = dict(defer='equal_to_rounding', same='bit_exact')

if DETERMINISTIC:
    import torch                                                             # noqa: E402  (already imported by prof_train, after the env var was set)
    torch.use_deterministic_algorithms(True, warn_only=True)


class Same(prof.Variant):
    """The do-nothing arm (GPU-RUN-4 condition 3): exactly the baseline under another name, so the A-A noise control runs through abbench (prof_train refuses the name 'baseline' as a B
    arm). setup / teardown / every hook are the base class's no-ops: B runs the same code as A, the same rows, the same seed."""
    name, doc = 'same', 'baseline under another name: the A-A noise control (does nothing)'
    ab_cpu_rule = 'bit_exact'


# ---- bench records: wall-clock start / end and the rounds of every micro-batch, per run (condition 3; mark 4 needs the sequence, mark 3 the clock times) ----
_LAST_AUX = {}
_orig_free_run, _orig_ab_run = prof.free_run, prof.ab_run


def _utc(t):
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')


def free_run(tr, n, chunk):
    """prof_train.free_run, then keep the (rows, rounds) of every timed micro-batch, in order, and the clock time of every chunk end."""
    t0 = time.time()
    per = _orig_free_run(tr, n, chunk)
    _LAST_AUX['seq'] = [None if r is None else float(r) for _, r in list(getattr(tr, 'aux_log', []) or [])]
    _LAST_AUX['timed_start'], _LAST_AUX['timed_end'] = t0, time.time()
    return per


def ab_run(world, args, names, accum):
    """prof_train.ab_run plus: started_utc / ended_utc (the whole run, warm-up included), timed_start_utc / timed_end_utc (the 40 timed updates), rounds_seq (thinker rounds of every timed
    micro-batch, in order: A and B rounds must match exactly, mark 4), host / pid."""
    _LAST_AUX.clear()
    t0 = time.time()
    rec = _orig_ab_run(world, args, names, accum)
    t1 = time.time()
    rec.update(started_utc=_utc(t0), ended_utc=_utc(t1), t_start=t0, t_end=t1, host=socket.gethostname(), pid=os.getpid(), arm_names=list(names), accum=accum)
    if 'seq' in _LAST_AUX:
        rec.update(rounds_seq=_LAST_AUX['seq'], timed_start_utc=_utc(_LAST_AUX['timed_start']), timed_end_utc=_utc(_LAST_AUX['timed_end']),
                   t_timed_start=_LAST_AUX['timed_start'], t_timed_end=_LAST_AUX['timed_end'])
    return rec


prof.free_run, prof.ab_run = free_run, ab_run          # sec_abbench / sec_throughput look these names up in prof_train's globals at call time


def host_info():
    """What GPU-RUN-4 records about the box (condition 6): host CPU model, cores, torch / CUDA / driver versions, the deterministic switch."""
    import torch
    cpu = None
    try:
        for line in open('/proc/cpuinfo'):
            if line.lower().startswith('model name'):
                cpu = line.split(':', 1)[1].strip()
                break
    except OSError:
        cpu = platform.processor() or None
    info = dict(host=socket.gethostname(), cpu_model=cpu, logical_cpus=os.cpu_count(), python=platform.python_version(), torch=torch.__version__, cuda=torch.version.cuda,
                cudnn=torch.backends.cudnn.version() if torch.backends.cudnn.is_available() else None, gpu=torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
                deterministic=DETERMINISTIC, cublas_workspace_config=os.environ.get('CUBLAS_WORKSPACE_CONFIG'), deterministic_algorithms=torch.are_deterministic_algorithms_enabled(),
                argv=sys.argv[1:], started_utc=_utc(time.time()))
    return info


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


def load_exact_arms(say=print, module='exact_arms'):
    """`import exact_arms` from this folder -> its NEW_VARIANTS (a list of Variant classes), or [] when there is no such module. An import that fails for any other reason is printed, not fatal.
    `module` is the module name (default 'exact_arms'; the tests pass another name so that they never depend on what sits in this folder)."""
    try:
        mod = importlib.import_module(module)
    except ModuleNotFoundError as e:
        if e.name == module:
            return []
        say(f'!!!!!! prof_launch: {module}.py exists but could not be imported ({e!r}); its arms are NOT registered')
        return []
    except Exception as e:                                                   # noqa: BLE001
        say(f'!!!!!! prof_launch: {module}.py raised on import ({e!r}); its arms are NOT registered\n' + traceback.format_exc())
        return []
    arms = list(getattr(mod, 'NEW_VARIANTS', []))
    if not arms:
        say(f'prof_launch: {module} imported but NEW_VARIANTS is empty or missing')
    return arms


def register_all(say=print, exact_module='exact_arms'):
    names = register([Same], say)
    names += register(defer.NEW_VARIANTS, say)
    names += register(load_exact_arms(say, exact_module), say)
    return names


def _out_path(argv):
    a = list(sys.argv[1:] if argv is None else argv)
    for i, x in enumerate(a):
        if x == '--out' and i + 1 < len(a):
            return a[i + 1]
        if x.startswith('--out='):
            return x.split('=', 1)[1]
    return None


def main(argv=None):
    names = register_all()
    print(f'prof_launch: registered {names}; setup order {prof.SETUP_ORDER}; ab arm order {prof.AB_ARM_ORDER}', flush=True)
    info = host_info()
    print('prof_launch: host ' + json.dumps(info), flush=True)
    out = _out_path(argv)
    side = (os.path.splitext(out)[0] + '.launch.json') if out else None
    if side:                                                             # a sidecar beside prof_train's json: host, versions, switch, clock (prof_train's own json is not edited)
        os.makedirs(os.path.dirname(side) or '.', exist_ok=True)
        json.dump(info, open(side, 'w'), indent=1)
    try:
        return prof.main(argv)
    finally:
        if side:
            info['ended_utc'] = _utc(time.time())
            json.dump(info, open(side, 'w'), indent=1)


if __name__ == '__main__':
    main()
