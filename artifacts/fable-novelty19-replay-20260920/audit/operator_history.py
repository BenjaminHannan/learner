#!/usr/bin/env python3
"""Reconstruct the FROZEN operator's historical training signatures without model
forwards, and measure the disjointness the preregistration (section 7) asks for.

Provenance, from `artifacts/astra-canonical-operator-screen-20260920/`:
  * driver  `scripts/astra_canonical_operator_run.py:worker`
  * stream  `rng = random.Random(1101)`, ONE sequential RNG, model-seed independent
  * loop    6,000 updates x `A.training_batch(rng, 16, forbidden)`
  * batch   16 x `toy_ladder.visit(spec, rng, training=True)` then `rng.randrange(1<<30)`
  * counts  training.json: canonical 576,000 = 6000*16*6, monolithic 192,000 = 6000*16*2

The cheap replay below consumes the SAME rng draws (verified by comparing
`rng.getstate()` against the real `A.training_batch` path), so it reproduces the exact
worlds and questions the operator was trained on.
"""
import hashlib
import json
import random
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve()
WORKTREE = HERE.parent.parent.parent.parent
sys.path.insert(0, str(WORKTREE / 'scripts'))

import fable_dispatcher_v3 as V3                     # noqa: E402
import fable_confirmation_panels as CP               # noqa: E402

A = V3.A
torch = V3.torch
QUESTION, ANSWER, LINK = V3.QUESTION, V3.ANSWER, V3.LINK
ENTITY_MIN, ENTITY_MAX = V3.ENTITY_MIN, V3.ENTITY_MAX
S = HERE.parent / 'scratch'
UPDATES = 6000


def reconstruct(updates=UPDATES):
    A.data.bootstrap()
    from premonition.toy_ladder import LadderSpec, visit
    spec = LadderSpec()
    rng = random.Random(1101)
    worlds, questions = set(), set()
    began = time.time()
    for _step in range(updates):
        for _v in range(16):
            rows, _world, _ = visit(spec, rng, training=True)
            memory = [[] if r.question else list(r.tokens) for r in rows]
            facts = CP.fact_tuples([r for r in memory if r])
            worlds.add(CP.world_signature(facts))
            for j, row in enumerate(rows):
                if not row.question:
                    continue
                q = row.tokens[:row.tokens.index(ANSWER) + 1]
                if row.hops == 1:
                    questions.add(CP.signature_from_facts(facts, q))
                else:
                    link_line, endpoint_line = row.gold
                    entity = rows[link_line].tokens[3]
                    questions.add(CP.signature_from_facts(facts,
                                                          [QUESTION, q[1], LINK, ANSWER]))
                    questions.add(CP.signature_from_facts(facts,
                                                          [QUESTION, entity, q[3], ANSWER]))
                    questions.add(CP.signature_from_facts(facts, q))
        rng.randrange(1 << 30)
    return worlds, questions, time.time() - began


def block_sigs(path):
    payload = torch.load(path, weights_only=False)
    w, q = set(), set()
    for b in payload['blocks']:
        for row in b['world_signature'].tolist():
            w.add(bytes(row).hex())
        for row in b['signature'].tolist():
            q.add(bytes(row).hex())
    return w, q


def panel_sigs(folder):
    manifest = json.loads((Path(folder) / 'manifest.json').read_text())
    w, q = set(), set()
    for cell in manifest['cell_order']:
        panel = json.loads((Path(folder) / f'{cell}.json').read_text())
        for u in panel['units']:
            for side in ['a'] + (['b'] if panel['kind'] == 'pair' else []):
                rows = [r for i, r in enumerate(u[side]['memory'])
                        if r and i < u[side]['where']]
                facts = CP.fact_tuples(rows)
                w.add(CP.world_signature(facts))
                q.add(CP.signature_from_facts(facts, u[side]['question']))
    return w, q


def main():
    updates = int(sys.argv[1]) if len(sys.argv) > 1 else UPDATES
    ow, oq, seconds = reconstruct(updates)
    digest = hashlib.sha256()
    for s in sorted(ow):
        digest.update(s.encode())
    out = dict(updates=updates, seconds=round(seconds, 1),
               distinct_training_worlds=len(ow),
               distinct_training_question_signatures=len(oq),
               world_union_sha256=digest.hexdigest())

    targets = {}
    idx = json.loads((S / 'awake9991' / 'index.json').read_text())
    aw, aq = set(), set()
    for e in idx['chunks']:
        w, q = block_sigs(S / 'awake9991' / e['name'])
        aw |= w
        aq |= q
    targets['awake_stream_seed9991'] = (aw, aq)
    targets['memory_seed9991'] = block_sigs(S / 'mem9991' / 'worlds.pt')
    for arm in 'RGU':
        targets[f'buffer_{arm}_seed9991'] = block_sigs(S / 'buf9991' / f'buffer-{arm}.pt')
    targets['dev_panels_32x64'] = panel_sigs(S / 'dev32')

    out['overlap_with_operator_training'] = {
        name: dict(worlds=len(w & ow), questions=len(q & oq),
                   their_worlds=len(w), their_questions=len(q))
        for name, (w, q) in targets.items()}
    print(json.dumps(out, indent=2))
    (HERE.parent / 'operator-history.json').write_text(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
