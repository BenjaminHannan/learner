"""How far does the short-story lookup rule hold as the story gets much bigger? (2026-09-20)

EVALUATION ONLY. No training, no optimizer, no gradient, no checkpoint is ever written.
Every checkpoint is opened read-only and its sha256 is verified and recorded. Additive:
nothing registered is edited; every artefact goes to
``<worktree>/artifacts/fable-story-size-stress-20260920``.

THE QUESTION. Checkpoints trained ONLY on 16-fact, filler-free stories (the startup
factorial's arm A) score ~99% on ordinary full 6-person stories they never trained on.
How far does that transfer go as the story grows, and where does it break?

THE GRID (paired, nested -- the design owner's two corrections to the old size sweep).

  Worlds. ``WORLDS`` = 64 base worlds are built ONCE in the fresh RNG namespace
  ``fable-size-stress-v1``. Each is a FULL 16-person world: 16 x 3 attribute rows + 16
  LINK rows = 64 fact rows, the most this token vocabulary can hold. A fixed 6-person
  SUBSET of each world carries every question, so the same questions are answerable in
  every cell of the grid.

  Questions, identical in every cell (this is the pairing):
    * 512 one-call ATTRIBUTE questions ``[4, ENT, REL, 5]``, REL in {8, 9, 10}, balanced
      170/171/171 by construction (8 per world, counts 3/3/2 with the short relation
      rotating with the world index);
    * 256 one-call LINK questions ``[4, ENT, 11, 5]`` (4 per world, distinct people);
    * 256 two-hop questions ``[4, ENT, 11, REL, 5]`` for the recursive executor (4 per
      world). Arm-A / arm-D checkpoints never trained on LINK, so their LINK and two-hop
      numbers are reported but are NOT part of their verdict.

  Fact conditions (columns): ``F24`` keeps only the subset's own 24 fact rows;
  ``F64`` keeps all 64, i.e. the subset's 24 plus 40 rows about 10 other people that share
  the same relations and draw values from the same pool -- distractors by construction.

  Filler conditions (rows): 0x, 1x, 3x, 10x, 30x the generator's own filler/gap rows.
  ``1x`` is block 0, the visit's OWN filler-only and gap rows, verbatim. Blocks 1..29 are
  FRESH DRAWS from the SAME grammar (4 distractor rows of ``randint(3, 6)`` filler tokens,
  then gap rows of ``randint(4, 8)`` filler tokens until the row's 128-token gap budget is
  met -- exactly ``premonition.toy_ladder.visit``). Multiple m keeps blocks 0..m-1, so the
  filler sets are NESTED: every smaller cell's rows are a subset of every larger cell's.
  Filler rows are interleaved uniformly at random with the fact rows (one uniform sort key
  per filler row, drawn once for all 30 blocks), so removing filler rows from a large cell
  reproduces a small cell's row order exactly. Fact rows keep the generator's own order.

  Causal eligibility follows the registered one-hop panels: the question sits after every
  story row, so EVERY story row is eligible for every question (``data.pack`` with
  ``question_line = len(rows)``).

PER CELL AND CHECKPOINT (never averaged across seeds):
  accuracy (attribute overall and per relation; LINK separately), mean attention mass on
  the correct supporting row (mean over heads and read steps, measured by the factorial's
  own ``correct_line_mass``) and its ratio to uniform-over-eligible-tokens, rows and tokens
  per story, and the answer-logit margin (gold logit minus the best other logit).
  Two-call execution through ``astra_canonical_operator.execute`` is scored for the
  grow-blind family only, on the same grid.

EXCLUSION. Each question's semantic signature (``A.visible_signature`` over the eligible
visible fact rows) is checked against the registered development panels' forbidden set.
The signature ignores filler and row order, so it is the same for every filler multiple;
only the two fact conditions give distinct signatures. Feasible and run here.

CLI
  manifest   hash the preregistration and every checkpoint; write manifest.json
  geometry   build the grid, write per-cell row/token geometry and the exclusion audit
  score      evaluate one or more checkpoints over the grid; writes raw/<key>.json
  tables     print the report tables from the raw JSON
"""
from __future__ import annotations

import sys
from pathlib import Path

BASE = Path('/Users/ben-hannan/Desktop/projects/beautiful-model')
HERE = Path(__file__).resolve().parent
if HERE != (BASE/'scripts'):
    for entry in (str(BASE), str(BASE/'scripts')):
        while entry in sys.path:
            sys.path.remove(entry)
        sys.path.insert(0, entry)

import argparse
import datetime
import json
import math
import random
import resource
import time

import fable_startup_factorial as FSF
import fable_operator_startup as S
import astra_canonical_operator as A
import astra_canonical_operator_run as R
import astra_canonical_operator_panels as P
import premonition_memnn_compare as C

torch, data, E, T = A.torch, A.data, A.E, A.T
ROOT = R.ROOT
assert ROOT == BASE, (ROOT, BASE)
QUESTION, ANSWER, WORLD, LINK = A.QUESTION, A.ANSWER, A.WORLD, A.LINK
ENTITY_MIN, ENTITY_MAX = A.ENTITY_MIN, A.ENTITY_MAX
ATTRIBUTE_RELATIONS = S.ATTRIBUTE_RELATIONS
_num = FSF._num

OUT = HERE.parent/'artifacts/fable-story-size-stress-20260920'
PREREG = OUT/'PREREGISTRATION.md'
RAW = OUT/'raw'

NAMESPACE = 'fable-size-stress-v1'
PEOPLE = 16                       # a FULL world: 16 people, 64 fact rows
SUBSET_SIZE = 6                   # the fixed people every question is about
WORLDS = 64
ATTR_PER_WORLD = 8                # 64 x 8 = 512 attribute questions
LINK_PER_WORLD = 4                # 64 x 4 = 256 LINK questions
TWO_HOP_PER_WORLD = 4             # 64 x 4 = 256 two-hop questions
FILLER_MULTIPLES = (0, 1, 3, 10, 30)
FACT_CONDITIONS = ('F24', 'F64')
FILLER_BLOCKS = max(FILLER_MULTIPLES)
EXCLUSION = ROOT/('artifacts/astra-canonical-operator-screen-20260920/'
                  'astra_canonical_operator_panels/forbidden-semantics.json')

FACTORIAL = HERE.parent/'artifacts/fable-startup-factorial-20260920'
GROW_BLIND = ROOT/'artifacts/fable-operator-grow-blind-20260920'

# family -> (key -> checkpoint path). Families are reported separately, never pooled.
CHECKPOINTS = {}
for _s in (0, 1, 2):
    CHECKPOINTS[f'factorial-A-seed-{_s}'] = ('factorial-A', FACTORIAL/f'A/seed-{_s}/final.pt')
    CHECKPOINTS[f'factorial-D-seed-{_s}'] = ('factorial-D', FACTORIAL/f'D/seed-{_s}/final.pt')
for _s in range(6):
    CHECKPOINTS[f'grow-blind-seed-{_s}'] = (
        'grow-blind', GROW_BLIND/f'astra_canonical_operator_seed-{_s}/final.pt')
FAMILIES = ('factorial-A', 'grow-blind', 'factorial-D')
# Only grow-blind was trained on LINK, so only it gets the two-call execution axis.
TWO_HOP_FAMILIES = ('grow-blind',)
CHANCE = 1/16.                    # 16 value tokens; also 16 entity tokens for LINK


def cell_name(condition, multiple):
    return f'{condition}-x{multiple}'


CELLS = tuple(cell_name(c, m) for c in FACT_CONDITIONS for m in FILLER_MULTIPLES)


# ===================================================================== world construction

def _spec():
    data.bootstrap()
    from premonition.toy_ladder import LadderSpec
    return LadderSpec(entities=PEOPLE)


def _filler_row(spec, rng, low, high):
    """One filler-only row, drawn exactly as ``toy_ladder.visit`` draws one."""
    from premonition.toy_ladder import NEWLINE
    n = rng.randint(low, high)
    return [WORLD] + [spec.filler(rng.randrange(spec.fillers)) for _ in range(n)] + [NEWLINE]


def filler_block(spec, rng):
    """One extra 1x-equivalent block: the generator's distractor rows plus its gap rows."""
    rows = [_filler_row(spec, rng, 3, 6) for _ in range(spec.distractors)]
    gap = 0
    while gap < spec.gap:
        row = _filler_row(spec, rng, 4, 8)
        rows.append(row)
        gap += len(row)
    return rows


def build_world(index):
    """One base world: a full 16-person story, its 6-person subset and its questions.

    The friend map is redrawn until (a) ``toy_ladder``'s own two-hop drawability condition
    holds and (b) every subset person's friend is ALSO in the subset. (b) is a declared
    deviation from the generator's uniform friend draw; without it a two-hop question about
    a subset person would not be answerable in the F24 cell, and the grid would stop being
    paired. Attribute values, row order, filler and the other ten people are untouched.
    """
    from premonition.batch import N_ENT
    from premonition.toy_ladder import World, visit
    spec = _spec()
    assert spec.vocab_size + N_ENT - 1 == ENTITY_MAX - 1, spec.vocab_size
    rng = random.Random(f'{NAMESPACE}:world:{index}')
    ents = rng.sample(range(N_ENT), spec.entities)
    attr = {(e, r): rng.randrange(spec.values) for e in ents for r in range(spec.relations)}
    subset = ents[:SUBSET_SIZE]
    tries = 0
    while True:
        tries += 1
        friend = {e: rng.choice([x for x in ents if x != e]) for e in ents}
        if not all(any(x not in (a, friend[a]) and friend[x] not in (a, friend[a])
                       for x in ents) for a in ents):
            continue
        if all(friend[e] in subset for e in subset):
            break
    world = World(ents, attr, friend)
    rows, _, _ = visit(spec, rng, training=True, world=world)
    full = [[] if row.question else list(row.tokens) for row in rows]
    fact_ix, other_ix = S._row_classes(full)
    assert len(fact_ix) == 4*PEOPLE, len(fact_ix)
    fact_rows = [full[i] for i in fact_ix]
    subset_tokens = {spec.vocab_size + e for e in subset}
    subset_rows = [r for r in fact_rows if r[1] in subset_tokens]
    assert len(subset_rows) == 4*SUBSET_SIZE, len(subset_rows)

    frng = random.Random(f'{NAMESPACE}:filler:{index}')
    blocks = [[full[i] for i in other_ix]]
    blocks += [filler_block(spec, frng) for _ in range(FILLER_BLOCKS-1)]
    offsets, flat = [0], []
    for block in blocks:
        flat.extend(block)
        offsets.append(len(flat))
    krng = random.Random(f'{NAMESPACE}:order:{index}')
    keys = [krng.random() for _ in flat]

    qrng = random.Random(f'{NAMESPACE}:questions:{index}')
    short = index % 3
    attribute = []
    for r in range(spec.relations):
        for e in qrng.sample(subset, 2 if r == short else 3):
            attribute.append((spec.vocab_size + e, spec.relation(r),
                              spec.value(attr[(e, r)])))
    qrng.shuffle(attribute)
    assert len(attribute) == ATTR_PER_WORLD
    link = [(spec.vocab_size + e, LINK, spec.vocab_size + friend[e])
            for e in qrng.sample(subset, LINK_PER_WORLD)]
    two_hop = []
    for i, e in enumerate(qrng.sample(subset, TWO_HOP_PER_WORLD)):
        r = (index + i) % spec.relations
        two_hop.append((spec.vocab_size + e, spec.relation(r),
                        spec.vocab_size + friend[e], spec.value(attr[(friend[e], r)])))
    return dict(index=index, ents=ents, subset=subset, friend_tries=tries,
                fact_rows=fact_rows, subset_rows=subset_rows, filler=flat,
                filler_offsets=offsets, filler_keys=keys,
                attribute=attribute, link=link, two_hop=two_hop)


def story_rows(world, condition, multiple):
    """This cell's story rows for this world, in order. Nested in ``multiple`` by design."""
    facts = world['subset_rows'] if condition == 'F24' else world['fact_rows']
    stop = world['filler_offsets'][multiple]
    items = [(( j + .5)/len(facts), 0, j, row) for j, row in enumerate(facts)]
    items += [(world['filler_keys'][i], 1, i, row)
              for i, row in enumerate(world['filler'][:stop])]
    items.sort(key=lambda item: item[:3])
    return [item[3] for item in items]


def pack_questions(rows, questions):
    """One visit, its questions after every story row -- so every row is eligible."""
    return data.pack([rows], [list(q) for q in questions], [0]*len(questions),
                     [len(rows)]*len(questions))


def world_cell(world, condition, multiple):
    """Packed one-call inputs, answers and the two-hop program for one (world, cell)."""
    rows = story_rows(world, condition, multiple)
    one_call = [[QUESTION, e, op, ANSWER] for e, op, _ in world['attribute'] + world['link']]
    answers = [a for _, _, a in world['attribute'] + world['link']]
    x = pack_questions(rows, one_call)
    assert [p[-1]['target'] for p in A.truth_paths(x)] == answers, 'answer not derivable'
    two = [[QUESTION, e, LINK, op, ANSWER] for e, op, _, _ in world['two_hop']]
    two_answers = [a for _, _, _, a in world['two_hop']]
    two_mid = [m for _, _, m, _ in world['two_hop']]
    xt = pack_questions(rows, two)
    paths = A.truth_paths(xt)
    assert [p[-1]['target'] for p in paths] == two_answers, 'two-hop answer not derivable'
    assert [p[0]['target'] for p in paths] == two_mid, 'two-hop link not derivable'
    return dict(rows=rows, inputs=x, answers=torch.tensor(answers),
                relations=x.questions[:, 2].clone(),
                two_inputs=xt, two_answers=torch.tensor(two_answers),
                two_mid=torch.tensor(two_mid))


def build_grid(worlds=WORLDS):
    return [build_world(w) for w in range(worlds)]


# ============================================================================== evaluation

def load_checkpoint(path):
    """Read-only. Returns (model, sha256, saved metadata). Nothing is written back."""
    path = Path(path)
    sha = C.sha(path)
    saved = torch.load(path, map_location='cpu', weights_only=False)
    model = A.CanonicalOperator(**saved['architecture'])
    model.load_state_dict(saved['state_dict'], strict=True)
    model.eval()
    return model, sha, dict(updates=saved.get('updates'), seed=saved.get('seed'),
                            arm=saved.get('arm'), architecture=saved['architecture'])


class Accumulator:
    """Per-slice accuracy, correct-line attention, uniform ratio and logit margin."""

    def __init__(self):
        self.n = self.correct = 0
        self.mass = self.uniform = self.ratio = self.margin = 0.
        self.counts = {}

    def add(self, correct, mass, uniform, margin, predictions):
        k = int(correct.numel())
        self.n += k
        self.correct += int(correct.sum())
        self.mass += float(mass.sum())
        self.uniform += float(uniform.sum())
        self.ratio += float((mass.double()/uniform.double()).sum())
        self.margin += float(margin.sum())
        for token in predictions.tolist():
            self.counts[token] = self.counts.get(token, 0) + 1

    def report(self):
        if not self.n:
            return dict(n=0)
        shares = [c/self.n for c in self.counts.values()]
        return dict(n=self.n, correct=self.correct, accuracy=_num(self.correct/self.n),
                    correct_line_mass=_num(self.mass/self.n),
                    uniform_line_mass=_num(self.uniform/self.n),
                    mass_over_uniform=_num(self.ratio/self.n),
                    answer_logit_margin=_num(self.margin/self.n),
                    distinct_predictions=len(self.counts), top1_share=_num(max(shares)))


@torch.no_grad()
def score_cell(model, grid, condition, multiple, two_hop=False, cache=None):
    """One (checkpoint, cell). Pure evaluation: no gradient, no parameter is touched."""
    slices = {'attribute': Accumulator(), 'link': Accumulator()}
    slices.update({f'relation{r}': Accumulator() for r in ATTRIBUTE_RELATIONS})
    rows_per_story, tokens_per_story = [], []
    exec_correct = exec_mid = exec_n = exec_calls = 0
    for w, world in enumerate(grid):
        cell = cache[w] if cache is not None else world_cell(world, condition, multiple)
        if cache is not None and cache[w] is None:
            cell = cache[w] = world_cell(world, condition, multiple)
        x, answers = cell['inputs'], cell['answers']
        rows_per_story.append(int(x.memory.shape[1]))
        tokens_per_story.append(int(x.memory.ne(0).sum()))
        lines = FSF.supporting_lines(x)
        mask = FSF.line_token_mask(x, lines)
        logits, mass = FSF.correct_line_mass(model, x, mask)
        mass = mass.mean((1, 2))                       # mean over read steps and heads
        uniform = FSF.uniform_line_mass(x, lines)
        predictions = logits.argmax(-1)
        correct = predictions == answers
        gold = logits.gather(1, answers[:, None]).squeeze(1)
        other = logits.scatter(1, answers[:, None], -math.inf).max(1).values
        margin = gold - other
        relation = cell['relations']
        for name, pick in (('attribute', relation != LINK), ('link', relation == LINK),
                           *((f'relation{r}', relation == r) for r in ATTRIBUTE_RELATIONS)):
            if bool(pick.any()):
                slices[name].add(correct[pick], mass[pick], uniform[pick], margin[pick],
                                 predictions[pick])
        if two_hop:
            result = A.execute(model, cell['two_inputs'])
            emitted = result['emitted']
            exec_n += len(emitted)
            exec_calls += result['calls']
            exec_correct += sum(int(p == int(a)) for p, a in
                                zip(result['predictions'], cell['two_answers'].tolist()))
            exec_mid += sum(int(e[0] == int(m)) for e, m in
                            zip(emitted, cell['two_mid'].tolist()))
    out = {name: acc.report() for name, acc in slices.items()}
    out['geometry'] = dict(
        worlds=len(grid), rows_per_story=_num(sum(rows_per_story)/len(rows_per_story)),
        tokens_per_story=_num(sum(tokens_per_story)/len(tokens_per_story)),
        min_rows=min(rows_per_story), max_rows=max(rows_per_story),
        min_tokens=min(tokens_per_story), max_tokens=max(tokens_per_story))
    if two_hop:
        out['two_hop_execution'] = dict(
            n=exec_n, correct=exec_correct, accuracy=_num(exec_correct/exec_n),
            link_step_correct=exec_mid, link_step_accuracy=_num(exec_mid/exec_n),
            calls=exec_calls, calls_per_question=_num(exec_calls/exec_n))
    return out


# ================================================================================ commands

def _sha_text(path):
    return C.sha(path)


def manifest(args):
    """Hash the preregistration and every checkpoint BEFORE any evaluation is run."""
    OUT.mkdir(parents=True, exist_ok=True)
    if not PREREG.exists():
        raise RuntimeError(f'write {PREREG} before the manifest')
    rows = {}
    for key, (family, path) in CHECKPOINTS.items():
        if not Path(path).exists():
            raise RuntimeError(f'missing checkpoint: {path}')
        _, sha, meta = load_checkpoint(path)
        rows[key] = dict(family=family, path=str(path), sha256=sha, **meta)
    payload = dict(
        created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        experiment='fable-story-size-stress', evidence='exploratory development',
        namespace=NAMESPACE, preregistration=str(PREREG),
        preregistration_sha256=_sha_text(PREREG),
        script_sha256=_sha_text(Path(__file__).resolve()),
        grid=dict(worlds=WORLDS, people=PEOPLE, subset=SUBSET_SIZE,
                  fact_conditions=list(FACT_CONDITIONS),
                  filler_multiples=list(FILLER_MULTIPLES), cells=list(CELLS),
                  attribute_questions=WORLDS*ATTR_PER_WORLD,
                  link_questions=WORLDS*LINK_PER_WORLD,
                  two_hop_questions=WORLDS*TWO_HOP_PER_WORLD),
        chance=CHANCE, two_hop_families=list(TWO_HOP_FAMILIES),
        exclusion_path=str(EXCLUSION), exclusion_sha256=_sha_text(EXCLUSION),
        checkpoints=rows, training=False)
    C.write_new(OUT/'manifest.json', payload)
    print(json.dumps(dict(prereg_sha256=payload['preregistration_sha256'],
                          checkpoints=len(rows)), indent=2), flush=True)


def geometry(args):
    """Build the grid, record per-cell geometry, audit pairing/nesting and exclusion."""
    started = time.monotonic()
    grid = build_grid(args.worlds)
    forbidden = set(json.loads(EXCLUSION.read_text()))
    cells, signatures, overlaps = {}, set(), 0
    for condition in FACT_CONDITIONS:
        for multiple in FILLER_MULTIPLES:
            rows_per, tokens_per, filler_rows = [], [], []
            for world in grid:
                rows = story_rows(world, condition, multiple)
                rows_per.append(len(rows))
                tokens_per.append(sum(len(r) for r in rows))
                filler_rows.append(sum(1 for r in rows if not S._is_fact(r)))
            cells[cell_name(condition, multiple)] = dict(
                condition=condition, filler_multiple=multiple,
                mean_rows=_num(sum(rows_per)/len(rows_per)),
                mean_tokens=_num(sum(tokens_per)/len(tokens_per)),
                min_rows=min(rows_per), max_rows=max(rows_per),
                min_tokens=min(tokens_per), max_tokens=max(tokens_per),
                mean_filler_rows=_num(sum(filler_rows)/len(filler_rows)),
                fact_rows=24 if condition == 'F24' else 64)
        # The semantic signature ignores filler and order, so one multiple covers them all.
        for world in grid:
            cell = world_cell(world, condition, 1)
            memory = cell['inputs'].memory.tolist()[0]
            for q in cell['inputs'].questions.tolist():
                sig = A.visible_signature(memory, q)
                signatures.add(sig)
                overlaps += int(sig in forbidden)
            for q in cell['two_inputs'].questions.tolist():
                sig = A.visible_signature(memory, q)
                signatures.add(sig)
                overlaps += int(sig in forbidden)
    payload = dict(namespace=NAMESPACE, worlds=args.worlds, cells=cells,
                   exclusion_path=str(EXCLUSION), exclusion_sha256=_sha_text(EXCLUSION),
                   exclusion_entries=len(forbidden),
                   signatures_checked=len(signatures), signature_overlaps=overlaps,
                   seconds=_num(time.monotonic()-started))
    C.write_new(OUT/'geometry.json', payload)
    print(json.dumps(dict(cells={k: (v['mean_rows'], v['mean_tokens'])
                                 for k, v in cells.items()},
                          signatures=len(signatures), overlaps=overlaps), indent=2),
          flush=True)


def score(args):
    """Evaluate the given checkpoints over the whole grid. One process at a time."""
    RAW.mkdir(parents=True, exist_ok=True)
    keys = [k.strip() for k in args.keys.split(',') if k.strip()] if args.keys \
        else list(CHECKPOINTS)
    for key in keys:
        assert key in CHECKPOINTS, key
        if (RAW/f'{key}.json').exists():
            raise RuntimeError(f'already scored: {key}')
    manifest_rows = json.loads((OUT/'manifest.json').read_text())['checkpoints']
    started = time.monotonic()
    models, results = {}, {key: {} for key in keys}
    for key in keys:
        family, path = CHECKPOINTS[key]
        model, sha, meta = load_checkpoint(path)
        assert sha == manifest_rows[key]['sha256'], f'checkpoint changed: {key}'
        models[key] = (family, model, sha, meta, C.fingerprint(model))
    grid = build_grid(args.worlds)
    for condition in FACT_CONDITIONS:
        for multiple in FILLER_MULTIPLES:
            name = cell_name(condition, multiple)
            if args.cells and name not in args.cells.split(','):
                continue
            cache = [None]*len(grid)
            for key in keys:
                family, model, _, _, fingerprint = models[key]
                mark = time.monotonic()
                row = score_cell(model, grid, condition, multiple,
                                 two_hop=family in TWO_HOP_FAMILIES and not args.no_two_hop,
                                 cache=cache)
                row['seconds'] = _num(time.monotonic()-mark)
                assert C.fingerprint(model) == fingerprint, 'the checkpoint must not change'
                results[key][name] = row
                print(json.dumps(dict(
                    key=key, cell=name, attribute=row['attribute']['accuracy'],
                    link=row['link']['accuracy'],
                    mass=row['attribute']['correct_line_mass'],
                    ratio=row['attribute']['mass_over_uniform'],
                    rows=row['geometry']['rows_per_story'],
                    two_hop=row.get('two_hop_execution', {}).get('accuracy'),
                    seconds=row['seconds'])), flush=True)
            del cache
    for key in keys:
        family, _, sha, meta, fingerprint = models[key]
        C.write_new(RAW/f'{key}.json', dict(
            key=key, family=family, checkpoint=str(CHECKPOINTS[key][1]), sha256=sha,
            fingerprint=fingerprint, metadata=meta, namespace=NAMESPACE,
            worlds=args.worlds, training=False, cells=results[key],
            peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            seconds=_num(time.monotonic()-started)))
    print(json.dumps(dict(scored=keys, seconds=_num(time.monotonic()-started),
                          peak_rss_mb=_num(resource.getrusage(
                              resource.RUSAGE_SELF).ru_maxrss/1e6))), flush=True)


def tables(args):
    """Markdown tables for REPORT.md: one per family, per metric."""
    loaded = {}
    for key in CHECKPOINTS:
        path = RAW/f'{key}.json'
        if path.exists():
            loaded[key] = json.loads(path.read_text())
    lines = []
    for family in FAMILIES:
        keys = [k for k in CHECKPOINTS if CHECKPOINTS[k][0] == family and k in loaded]
        if not keys:
            continue
        for metric, label, fmt in (('accuracy', 'attribute accuracy', '{:.3f}'),
                                   ('correct_line_mass', 'correct-row attention', '{:.3f}'),
                                   ('mass_over_uniform', 'attention / uniform', '{:.1f}'),
                                   ('answer_logit_margin', 'answer-logit margin', '{:+.2f}')):
            for slice_name in ('attribute', 'link'):
                lines.append(f'\n**{family} -- {slice_name} {label}**\n')
                head = '| filler | ' + ' | '.join(
                    f'{c} {k.split("seed-")[1]}' for c in FACT_CONDITIONS for k in keys) + ' |'
                lines.append(head)
                lines.append('| --- | ' + ' | '.join(['---:']*(2*len(keys))) + ' |')
                for multiple in FILLER_MULTIPLES:
                    cells = []
                    for condition in FACT_CONDITIONS:
                        for key in keys:
                            row = loaded[key]['cells'].get(cell_name(condition, multiple))
                            value = row[slice_name][metric] if row else None
                            cells.append(fmt.format(value) if value is not None else '-')
                    lines.append(f'| {multiple}x | ' + ' | '.join(cells) + ' |')
    print('\n'.join(lines))


def build_parser():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('command', choices=['manifest', 'geometry', 'score', 'tables'])
    ap.add_argument('--keys', default='')
    ap.add_argument('--cells', default='')
    ap.add_argument('--worlds', type=int, default=WORLDS)
    ap.add_argument('--no-two-hop', action='store_true', default=False)
    return ap


if __name__ == '__main__':
    args = build_parser().parse_args()
    R.configure()
    {'manifest': manifest, 'geometry': geometry, 'score': score,
     'tables': tables}[args.command](args)
