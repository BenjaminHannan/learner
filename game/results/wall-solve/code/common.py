"""Shared constants for Z7 / Z8 (WALL-SOLVE-PREREG.md). Run with PYTHONPATH=/home/user/benjaminhannan/learner, cwd the same."""
import os

SP = '/tmp/claude-0/-home-user/a1ebb63a-25ce-579d-bded-94d555e1f95e/scratchpad'
Z = f'{SP}/z78'
GL = f'{SP}/glprobe'
HELD = f'{GL}/data64k/heldout.jsonl'
# model seed -> practice run seed
RUN_SEED = {200: 398, 201: 399}
A23 = {200: 0.624, 201: 0.648}   # A23 held-out S top-1, rounded to 0.1 point as quoted in the pre-registration
DAYS = (0, 1, 2, 3)


def ckpt(seed):
    return f'{GL}/s{seed}/n64000/checkpoint.pt'


def eval_json(seed):
    return f'{GL}/s{seed}/n64000/eval.json'


def outdir(seed, root=Z):
    d = f'{root}/s{RUN_SEED[seed]}'
    os.makedirs(d, exist_ok=True)
    return d
