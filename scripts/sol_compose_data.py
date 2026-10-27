"""Symbolic TRAIN/dev only. No natural-language templates or final holdout API.

A table is a permutation of ten numeric keys; expressions apply two primitives.
Table records: [120, key atom (75+k), digit key (2+k), digit value (2+v)].
Query record: [first opcode, second opcode, digit argument, 1 (answer hole)].
118 = increment modulo 10, 119 = table lookup. Opcodes are input syntax, not
model routing labels. Labels and oracle intermediates never enter InputBatch.
"""
from __future__ import annotations
import hashlib
import json
import random
from collections import Counter
from dataclasses import dataclass
import torch

TRAIN_STRUCTURES = ((10,), (5, 5))
DEV_STRUCTURES = ((7, 3), (6, 4))
ROWS, PORTS = 11, 4


def cycle_structure(table):
    seen, lengths = set(), []
    for start in range(10):
        if start in seen:
            continue
        cur, length = start, 0
        while cur not in seen:
            seen.add(cur); length += 1; cur = table[cur]
        lengths.append(length)
    return tuple(sorted(lengths, reverse=True))


def permutation(rng, lengths):
    keys = list(range(10)); rng.shuffle(keys)
    table, offset = [0] * 10, 0
    for length in lengths:
        cycle = keys[offset:offset + length]; offset += length
        for a, b in zip(cycle, cycle[1:] + cycle[:1]):
            table[a] = b
    return table


def oracle(table, start, order):
    """Generator/contract only; model and inference do not import this function."""
    value = start
    for opcode in order:
        if opcode == 118:
            value = (value + 1) % 10
        elif opcode == 119:
            value = table[value]
        elif opcode == 117:
            pass  # symbolic identity; not a model instruction/routing rule
        else:
            raise ValueError('unknown symbolic primitive')
    return value


@dataclass(frozen=True)
class InputBatch:
    tokens: torch.Tensor
    slots: torch.Tensor
    valid: torch.Tensor

    def to(self, device):
        return InputBatch(*(x.to(device) for x in (self.tokens, self.slots, self.valid)))

    def select(self, ids):
        return InputBatch(*(x[ids] for x in (self.tokens, self.slots, self.valid)))


@dataclass(frozen=True)
class Dataset:
    inputs: InputBatch
    targets: torch.Tensor  # Full row labels; 0 except query row, NEVER model input.
    structures: tuple
    table_hashes: tuple
    expression_keys: tuple
    audit: dict

    def select(self, ids):
        return self.inputs.select(ids), self.targets[ids]


def generate(split, seed, n, *, excluded_tables=()):
    if split not in ('TRAIN', 'TRAIN_primitives', 'dev_order', 'dev_structure'):
        raise ValueError('TRAIN/dev only; there is no final test generator')
    if n < 1:
        raise ValueError('positive count required')
    rng = random.Random(seed)
    structures = TRAIN_STRUCTURES if split.startswith('TRAIN') else DEV_STRUCTURES
    order = (119, 118) if split != 'dev_order' else (118, 119)
    excluded, used = set(excluded_tables), set()
    tokens, targets, shape_keys, table_hashes, expression_keys = [], [], [], [], []
    attempts = 0
    while len(tokens) < n:
        attempts += 1
        if attempts > n * 10000:
            raise RuntimeError('cannot fill distinct permutation pool')
        family = structures[(len(tokens)//10) % len(structures)]
        table = permutation(rng, family)
        digest = hashlib.sha256(bytes(table)).hexdigest()
        if digest in excluded or digest in used:
            continue
        start = rng.randrange(10)
        # Both orders must give different answers. This rejects commuting
        # examples rather than allowing a reverse-order dev test to be trivial.
        forward = oracle(table, start, (119, 118))
        reverse = oracle(table, start, (118, 119))
        if forward == reverse:
            continue
        if split == 'TRAIN_primitives':
            order = ((118,117),(117,118),(119,117),(117,119))[(len(tokens)//10)%4]
            answer = oracle(table,start,order)
        else:
            answer = forward if order == (119, 118) else reverse
        # Uniform final labels, with no class/order/family correlation.
        if answer != len(tokens) % 10:
            continue
        used.add(digest)
        records = [[120, 75 + key, 2 + key, 2 + table[key]] for key in range(10)]
        records.append([*order, 2 + start, 1])
        rng.shuffle(records)
        label = [2 + answer if row[-1] == 1 else 0 for row in records]
        tokens.append(records); targets.append(label)
        shape_keys.append(family); table_hashes.append(digest)
        expression_keys.append(f'{digest}:{start}:{order}')
    tok = torch.tensor(tokens, dtype=torch.long)
    slots = tok.eq(1)
    valid = torch.ones_like(slots)
    y = torch.tensor(targets, dtype=torch.long)
    raw = tok.numpy().tobytes() + slots.numpy().tobytes() + y.numpy().tobytes()
    audit = dict(split=split, seed=seed, n=n, unique_tables=len(used),
                 order=[list(x) for x in ((118,117),(117,118),(119,117),(117,119))] if split=='TRAIN_primitives' else list(order), cycle_structures=[list(x) for x in structures],
                 sha256=hashlib.sha256(raw).hexdigest(),
                 table_set_sha256=hashlib.sha256(''.join(sorted(used)).encode()).hexdigest(),
                 label_counts=dict(Counter(y[slots.any(-1)].tolist())),
                 noncommuting_only=split!='TRAIN_primitives', source='symbolic code-generated integers only',
                 input_bytes=tok.numel()*8 + slots.numel() + valid.numel(),
                 label_bytes=y.numel()*8, final_holdout=False)
    return Dataset(InputBatch(tok, slots, valid), y, tuple(shape_keys),
                   tuple(table_hashes), tuple(expression_keys), audit)


def build_pools(seed, train_n=640, dev_n=200):
    train = generate('TRAIN', 903000 + seed, train_n)
    primitives = generate('TRAIN_primitives', 903500 + seed, train_n, excluded_tables=train.table_hashes)
    structure = generate('dev_structure', 904000 + seed, dev_n)
    order = generate('dev_order', 905000 + seed, dev_n,
                     excluded_tables=structure.table_hashes)
    assert not set(train.table_hashes) & (set(order.table_hashes) | set(structure.table_hashes))
    assert not set(order.table_hashes) & set(structure.table_hashes)
    return {'TRAIN': train, 'TRAIN_primitives':primitives, 'dev_structure': structure, 'dev_order': order}
