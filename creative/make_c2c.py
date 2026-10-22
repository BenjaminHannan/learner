"""C2c, the fresh sealed test for Bid C (reviews/width-pilot-bid-C-card, sec. 2a (b)). CPU, no model.

  python3 -m creative.make_c2c --out creative/data/c2c            writes OUT/test.jsonl and OUT/MANIFEST.json; refuses to overwrite either
  python3 -m creative.make_c2c --check creative/data/c2c          re-reads a written test: sha256, length check, disjointness from every C2 split (no writing; exits 1 if any overlap or length count is non-zero)

The generator is creative.rules_real.make_questions, the one that built creative/data/c2 (rules_real.build_splits(seed=0), the default; C2's MANIFEST.json does not record its
seed, so SEEDS_USED_BY_C2 names it), on the same five held-out kinds, the same kind rules (representable instances only, 3 examples + 1 query, the examples pin the query) and the
same per-kind counts as the C2 test (read from C2's MANIFEST). Kinds are interleaved in rules_real.HELD_OUT order, as C2's rows are.
SEED 93801 is named in the card before generation. Collision rule: if it equals any seed in C2's MANIFEST (or in SEEDS_USED_BY_C2) the generator uses 93802.
DISJOINT BY PROMPT from every C2 split (warm, dev, pool, test, labelled): a drawn question whose (kind, parameters, examples, query) key is a C2 key is never drawn
(make_questions' `avoid`), and one whose prompt text equals any C2 prompt is DROPPED and redrawn from the same kind with a fresh stream until the count is met; the number is in the manifest.
The usable parameters of each kind come from C2's MANIFEST (rules_real.PARAMS minus `not_shown_representable`, checked against `usable_counts` and the kind seal), so no breadth-first
search runs and the kind rules are C2's. NOTE the current code's search reaches all 52 affine instances (C2's manifest lists (3, 15), (5, 13), (6, 15) as not shown), so a rebuild with
rules_real.write_splits today does NOT reproduce C2; --report-representable runs the search (about 5 minutes) and writes the differences into the manifest instead of using them.
The length check (answers over 8 chars, prompts over 208 chars: the old caps) is printed and written to the manifest; the card expects zeros, as for C2."""
import argparse, hashlib, json, os, re, sys
from creative import rules_real as R

SEED, FALLBACK_SEED = 93801, 93802
SEEDS_USED_BY_C2 = (0,)                  # rules_real.build_splits default; not recorded in C2's MANIFEST.json, confirmed by rebuilding it (sha256 of all five splits equal)
C2_DIR = 'creative/data/c2'
OLD_MAX_ANS, OLD_MAX_PROMPT = 8, 208
PROMPT_RE = re.compile(r'Examples: (.*)\. Now (\d+) -> \?$')


def manifest_seeds(node):
    """Every integer stored under a key called seed / seeds / *_seed anywhere in a manifest."""
    out = set()
    if isinstance(node, dict):
        for k, v in node.items():
            if k == 'seed' or k == 'seeds' or str(k).endswith('_seed'):
                out |= {x for x in (v if isinstance(v, (list, tuple)) else [v]) if isinstance(x, int)}
            out |= manifest_seeds(v)
    elif isinstance(node, list):
        for v in node:
            out |= manifest_seeds(v)
    return out


def resolve_seed(seed, used):
    """The card's rule: 93801, or 93802 if 93801 is a C2 seed. Any other seed (tests) must simply not be one."""
    if seed not in used:
        return seed
    if seed == SEED and FALLBACK_SEED not in used:
        return FALLBACK_SEED
    raise SystemExit(f'REFUSED: seed {seed} is already a C2 seed {sorted(used)}')


def question_key(row):
    """(kind, params, examples, query) as rules_real.make_questions stores it in `avoid`."""
    m = PROMPT_RE.match(row['prompt'])
    xs = tuple(int(p.split(' -> ')[0]) for p in m.group(1).split('; '))
    return (row['kind'], tuple(row['params']), xs, int(m.group(2)))


def load_c2(c2_dir=C2_DIR):
    """-> (manifest, {split: rows}) with every split's sha256 checked."""
    man = json.load(open(os.path.join(c2_dir, 'MANIFEST.json')))
    return man, {name: R.load_split(c2_dir, name) for name in R.SPLITS}


def usable_params(man):
    """{kind: [params]} for the held-out kinds from C2's MANIFEST; asserts they match the manifest's counts and the code's kind seal."""
    spec = man['_spec']
    if spec['kind_seal'] != R.KIND_SEAL:
        raise SystemExit('REFUSED: the kind rules changed since C2 was sealed')
    held = tuple(spec['held_out'])
    if set(held) != set(R.HELD_OUT) or spec['dropped_kinds']:
        raise SystemExit(f'REFUSED: C2 held-out kinds {held} (dropped {spec["dropped_kinds"]}) are not rules_real.HELD_OUT {R.HELD_OUT}')
    use = {}
    for k in held:
        bad = {tuple(p) for p in spec['not_shown_representable'].get(k, [])}
        use[k] = [p for p in R.PARAMS[k] if tuple(p) not in bad]
        if len(use[k]) != spec['usable_counts'][k]:
            raise SystemExit(f'REFUSED: {k} has {len(use[k])} usable parameter sets, C2\'s manifest says {spec["usable_counts"][k]}')
    return use


def length_report(rows):
    return dict(rows=len(rows), max_answer_chars=max(len(r['answer']) for r in rows), answers_over_8_chars=sum(len(r['answer']) > OLD_MAX_ANS for r in rows),
                max_prompt_chars=max(len(r['prompt']) for r in rows), prompts_over_208_chars=sum(len(r['prompt']) > OLD_MAX_PROMPT for r in rows))


def overlap_report(rows, c2):
    """How many C2c rows share a prompt (or a question key) with any C2 split; both must be 0."""
    prompts = {r['prompt'] for rs in c2.values() for r in rs}
    keys = {question_key(r) for rs in c2.values() for r in rs}
    return dict(c2_rows=sum(len(rs) for rs in c2.values()), prompt_overlap=sum(r['prompt'] in prompts for r in rows), key_overlap=sum(question_key(r) in keys for r in rows),
                duplicate_prompts_within=len(rows) - len({r['prompt'] for r in rows}))


def draw(use, counts, seed, c2, max_rounds=60):
    """-> (rows, dropped) : counts {kind: n} in HELD_OUT order, interleaved. dropped = prompt collisions with C2 that were redrawn."""
    banned = {r['prompt'] for rs in c2.values() for r in rs}
    avoid = {question_key(r) for rs in c2.values() for r in rs}
    per, dropped = {}, 0
    for kind in (k for k in R.HELD_OUT if k in counts):
        kept, seen = [], set()
        for rnd in range(max_rounds):
            if len(kept) == counts[kind]:
                break
            for r in R.make_questions((kind,), use, counts[kind] - len(kept), seed, f'c2c:{kind}:{rnd}', avoid):
                if r['prompt'] in banned or r['prompt'] in seen:
                    dropped += 1
                else:
                    kept.append(r)
                    seen.add(r['prompt'])
        if len(kept) != counts[kind]:
            raise SystemExit(f'REFUSED: cannot fill {kind}: {len(kept)} of {counts[kind]}')
        per[kind] = kept
    rows, i = [], 0
    while any(per.values()):
        for kind in per:
            if per[kind]:
                r = per[kind].pop(0)
                rows.append(dict(r, id=f'c2c:test:{i:05d}'))
                i += 1
    return rows, dropped


def make(out_dir, seed=SEED, c2_dir=C2_DIR, report_representable=False, counts=None):
    """counts: per-kind counts; default = C2's test counts (tests pass a small dict)."""
    man, c2 = load_c2(c2_dir)
    used = manifest_seeds(man) | set(SEEDS_USED_BY_C2)
    real_seed = resolve_seed(seed, used)
    paths = [os.path.join(out_dir, f) for f in ('test.jsonl', 'MANIFEST.json')]
    for p in paths:
        if os.path.exists(p):
            raise SystemExit(f'REFUSED: {p} exists; C2c is generated once')
    use = usable_params(man)
    differs = None
    if report_representable:
        got, _, _ = R.representable_params(R.HELD_OUT)
        differs = {k: dict(extra_in_code_now=sorted(set(map(tuple, got.get(k, []))) - set(map(tuple, v))), missing_in_code_now=sorted(set(map(tuple, v)) - set(map(tuple, got.get(k, [])))))
                   for k, v in use.items() if set(map(tuple, got.get(k, []))) != set(map(tuple, v))}
    counts = dict(counts or man['test']['kinds'])
    rows, dropped = draw(use, counts, real_seed, c2)
    lengths, overlap = length_report(rows), overlap_report(rows, c2)
    if overlap['prompt_overlap'] or overlap['key_overlap'] or overlap['duplicate_prompts_within']:
        raise SystemExit(f'REFUSED: the drawn test overlaps C2 or itself, nothing written: {overlap}')
    os.makedirs(out_dir, exist_ok=True)
    with open(paths[0], 'x') as f:
        for r in rows:
            f.write(json.dumps(r, sort_keys=True) + '\n')
    sha = hashlib.sha256(open(paths[0], 'rb').read()).hexdigest()
    out = dict(test=dict(n=len(rows), sha256=sha, kinds={k: sum(r['kind'] == k for r in rows) for k in sorted({r['kind'] for r in rows})}),
               _spec=dict(seed=real_seed, requested_seed=seed, seed_rule=f'{SEED}; {FALLBACK_SEED} if {SEED} is a C2 seed', c2_seeds_checked=sorted(used),
                          generator='creative.rules_real.make_questions (tag c2c:KIND:ROUND, kinds interleaved in rules_real.HELD_OUT order)', salt=R.SALT, held_out=list(R.HELD_OUT),
                          kind_seal=R.KIND_SEAL, usable_counts=man['_spec']['usable_counts'], c2_manifest_sha256=hashlib.sha256(open(os.path.join(c2_dir, 'MANIFEST.json'), 'rb').read()).hexdigest(),
                          c2_split_sha256={k: man[k]['sha256'] for k in R.SPLITS}, per_kind_counts_from='C2 test (MANIFEST.json)' if counts == man['test']['kinds'] else 'override', prompt_collisions_redrawn=dropped, representability_vs_current_code=differs,
                          disjoint_from_c2=overlap, length_check=lengths))
    with open(paths[1], 'x') as f:
        json.dump(out, f, indent=1, sort_keys=True)
    return out


def problems(rep):
    """What a --check report must not contain: any overlap with C2 or inside the test, any answer over 8 / prompt over 208 chars. -> list of strings ([] = clean)."""
    out = [f'{k} = {rep["disjoint_from_c2"][k]}' for k in ('prompt_overlap', 'key_overlap', 'duplicate_prompts_within') if rep['disjoint_from_c2'][k]]
    out += [f'{k} = {rep["length_check"][k]}' for k in ('answers_over_8_chars', 'prompts_over_208_chars') if rep['length_check'][k]]
    return out


def check(out_dir, c2_dir=C2_DIR):
    """Re-read a written C2c: sha256 against its MANIFEST, kinds, lengths, disjointness. -> dict (nothing is written)."""
    man = json.load(open(os.path.join(out_dir, 'MANIFEST.json')))
    rows = R.load_split(out_dir, 'test')
    _, c2 = load_c2(c2_dir)
    rep = dict(sha256=man['test']['sha256'], n=len(rows), kinds={k: sum(r['kind'] == k for r in rows) for k in sorted({r['kind'] for r in rows})}, seed=man['_spec']['seed'],
               length_check=length_report(rows), disjoint_from_c2=overlap_report(rows, c2))
    rep['problems'] = problems(rep)
    return rep


def main(argv=None):
    a = argparse.ArgumentParser()
    a.add_argument('--out', default='creative/data/c2c')
    a.add_argument('--seed', type=int, default=SEED)
    a.add_argument('--c2', default=C2_DIR)
    a.add_argument('--check', metavar='DIR', help='re-check a written C2c instead of generating')
    a.add_argument('--report-representable', action='store_true', help='also run the breadth-first representability search (about 5 min) and record where it differs from the C2 manifest')
    a = a.parse_args(argv)
    if a.check:
        rep = check(a.check, a.c2)
        print(json.dumps(rep, indent=1))
        if rep['problems']:
            print('CHECK FAILED: ' + '; '.join(rep['problems']), file=sys.stderr)
            sys.exit(1)
        return
    man = make(a.out, a.seed, a.c2, a.report_representable)
    print(json.dumps(dict(test=man['test'], seed=man['_spec']['seed'], prompt_collisions_redrawn=man['_spec']['prompt_collisions_redrawn'],
                          disjoint_from_c2=man['_spec']['disjoint_from_c2'], length_check=man['_spec']['length_check']), indent=1))
    lc = man['_spec']['length_check']
    if lc['answers_over_8_chars'] or lc['prompts_over_208_chars']:
        print('WARNING: rows over the old caps; the caps file does not make them inert (card sec. 2b)', file=sys.stderr)


if __name__ == '__main__':
    main()
