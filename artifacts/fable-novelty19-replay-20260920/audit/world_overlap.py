#!/usr/bin/env python3
"""WORLD-level disjointness (spec 6/7 ask for worlds, the builder only checks questions).

Also: the two panel-unit probes that need `registered_cells` active, and the pilot-panel
overlap question.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
WORKTREE = HERE.parent.parent.parent.parent
sys.path.insert(0, str(WORKTREE / 'scripts'))

import fable_dispatcher_v3 as V3                     # noqa: E402
import fable_confirmation_panels as CP               # noqa: E402
import fable_novelty19_data as D                     # noqa: E402

torch = V3.torch
A = V3.A
S = HERE.parent / 'scratch'


def block_world_sigs(path):
    payload = torch.load(path, weights_only=False)
    out = set()
    for b in payload['blocks']:
        for row in b['world_signature'].tolist():
            out.add(bytes(row).hex())
    return out


def panel_world_sigs(folder):
    """World signature of every panel unit, computed HERE from its visible rows."""
    manifest = json.loads((Path(folder) / 'manifest.json').read_text())
    out, per_cell = set(), {}
    for cell in manifest['cell_order']:
        panel = json.loads((Path(folder) / f'{cell}.json').read_text())
        got = set()
        for u in panel['units']:
            for side in ['a'] + (['b'] if panel['kind'] == 'pair' else []):
                rows = [r for i, r in enumerate(u[side]['memory'])
                        if r and i < u[side]['where']]
                got.add(CP.world_signature(CP.fact_tuples(rows)))
        per_cell[cell] = len(got)
        out |= got
    return out, per_cell


def panel_semantic_sigs(folder):
    manifest = json.loads((Path(folder) / 'manifest.json').read_text())
    out = set()
    for cell in manifest['cell_order']:
        panel = json.loads((Path(folder) / f'{cell}.json').read_text())
        for u in panel['units']:
            for side in ['a'] + (['b'] if panel['kind'] == 'pair' else []):
                rows = [r for i, r in enumerate(u[side]['memory'])
                        if r and i < u[side]['where']]
                out.add(A.visible_signature(rows, u[side]['question']))
    return out


def main():
    awake_w = set()
    idx = json.loads((S / 'awake9991' / 'index.json').read_text())
    for entry in idx['chunks']:
        awake_w |= block_world_sigs(S / 'awake9991' / entry['name'])
    mem_w = block_world_sigs(S / 'mem9991' / 'worlds.pt')
    buf_w = {a: block_world_sigs(S / 'buf9991' / f'buffer-{a}.pt') for a in 'RGU'}
    dev_w, dev_per_cell = panel_world_sigs(S / 'dev32')
    dev_sem = panel_semantic_sigs(S / 'dev32')

    pilot = WORKTREE / ('artifacts/fable-dispatcher-pilot-20260920/panels/'
                        'forbidden-semantics.json')
    pilot_sem = set(json.loads(pilot.read_text())) if pilot.exists() else set()

    # what the builder's registered awake stream would carry as question signatures
    awake_sem = set()
    for entry in idx['chunks']:
        payload = torch.load(S / 'awake9991' / entry['name'], weights_only=False)
        for b in payload['blocks']:
            for row in b['signature'].tolist():
                awake_sem.add(bytes(row).hex())
    buf_sem = set()
    for a in 'RGU':
        payload = torch.load(S / 'buf9991' / f'buffer-{a}.pt', weights_only=False)
        for b in payload['blocks']:
            for row in b['signature'].tolist():
                buf_sem.add(bytes(row).hex())

    out = dict(
        counts=dict(awake_worlds=len(awake_w), memory_worlds=len(mem_w),
                    buffer_worlds={a: len(v) for a, v in buf_w.items()},
                    dev_panel_worlds=len(dev_w),
                    dev_panel_worlds_per_cell=dev_per_cell),
        world_level_overlap=dict(
            dev_vs_awake=len(dev_w & awake_w),
            dev_vs_memory=len(dev_w & mem_w),
            dev_vs_buffers={a: len(dev_w & v) for a, v in buf_w.items()},
            memory_subset_of_awake=mem_w.issubset(awake_w),
            buffer_worlds_equal_memory={a: (v == mem_w) for a, v in buf_w.items()}),
        question_level_overlap=dict(
            dev_vs_awake=len(dev_sem & awake_sem),
            dev_vs_buffers=len(dev_sem & buf_sem)),
        pilot_panels=dict(
            count=len(pilot_sem),
            in_registered_union=len(pilot_sem & D.build_exclusion_union()[0]),
            overlap_with_dev_panels=len(pilot_sem & dev_sem),
            overlap_with_awake_stream=len(pilot_sem & awake_sem),
            overlap_with_buffers=len(pilot_sem & buf_sem)),
    )

    # the two probes that need registered_cells active
    with D.registered_cells():
        unit, _ = D.dev_unit('N-c4-p6', 7, namespace=D.NS_DEV)
        a, _ = D.dev_unit('F-c1-r8', 0, namespace=D.NS_DEV)
        b, _ = D.dev_unit('F-c1-r8', 0, namespace=D.NS_CONFIRM)
    import inspect
    src = inspect.getsource(V3.pack_side)
    out['panel_unit'] = dict(
        top_level_keys=sorted(unit),
        side_keys=sorted(unit['a']),
        target_answer=unit['target_answer'], answer=unit['a']['answer'],
        target_equals_answer=(unit['target_answer'] == unit['a']['answer']),
        pack_side_reads_only=[k for k in ('memory', 'question', 'where', 'answer',
                                          'index', 'target_answer', 'chain')
                              if f"'{k}'" in src],
        pack_side_source=src.strip())
    out['dev_vs_confirm_namespace'] = dict(
        same_question=(a['a']['question'] == b['a']['question']),
        same_memory=(a['a']['memory'] == b['a']['memory']),
        both_answer_12=(a['a']['answer'] == b['a']['answer'] == 12))

    # do the frozen trainers see anything outside memory/question/where?
    import fable_baseline_transformer as B1
    out['baseline_pack_batch_reads'] = sorted(
        {k for k in ('owner', 'question', 'chain', 'hops', 'terminal', 'answer',
                     'support', 'where', 'index', 'target_answer', 'signature',
                     'world_signature')
         if f"'{k}'" in inspect.getsource(B1.pack_batch)})
    print(json.dumps(out, indent=2, default=str))


if __name__ == '__main__':
    main()
