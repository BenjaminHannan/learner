import ast, json, os, subprocess, sys
import numpy as np
import pytest
import torch

from tc1 import paint, houses, hidden_score, copyguard, night, run as run_mod
from tc1.config import make_config
from tc1.paint import R, T, D, END, NUM0, parse, render


def tok(*cmds):
    out = []
    for c in cmds:
        out += [c[0]] + [NUM0 + v for v in c[1:]]
    return out + [END]


@pytest.fixture(scope="module")
def data():
    return houses.make_data(1)


def test_all_houses_score_one(data):
    for name in ("critic", "heldback", "novel"):
        for g in getattr(data, name):
            assert hidden_score.score_grid(g)[0] == 1.0, name
    assert len(data.critic) == 200 and len(data.heldback) == 100 and len(data.novel) == 100
    # no held-back / novel house at copy distance 0 from a critic example
    assert copyguard.CopyGuard(data.critic).distances(data.heldback).min() >= 1
    assert copyguard.CopyGuard(data.critic).distances(data.novel).min() >= 1


def test_lone_rectangle_and_roof_and_below():
    g = render(parse(tok((R, 6, 3, 4, 6, 1))))          # centred body cols 3..8
    assert hidden_score.score_grid(g)[0] == pytest.approx(0.2)
    g = render(parse(tok((R, 6, 3, 4, 6, 1), (T, 5, 3, 6, 2))))   # roof base cols 3..8 directly above
    assert hidden_score.score_grid(g)[0] == pytest.approx(0.8)
    assert hidden_score.score_grid(g)[1] == (True, True, False, True, True)
    g = render(parse(tok((R, 2, 3, 4, 6, 1), (T, 7, 3, 6, 2))))   # roof below the body
    assert hidden_score.score_grid(g)[0] < 1
    g = render(parse(tok((R, 6, 3, 4, 6, 1), (T, 5, 3, 6, 2), (D, 0, 0, 3))))  # stray dot: not clean
    assert hidden_score.score_grid(g)[1][4] is False


def test_renderer_hand_drawn_house():
    # body 5x3 colour 1 at rows 6..8 cols 3..7; roof colour 2 base row 5 cols 3..7; door colour 3 at col 5 rows 7..8
    cmds = parse(tok((R, 6, 3, 3, 5, 1), (T, 5, 3, 5, 2), (R, 7, 5, 2, 1, 3)))
    g = render(cmds)
    exp = np.zeros((12, 12), dtype=np.int8)
    exp[6:9, 3:8] = 1
    exp[5, 3:8] = 2; exp[4, 4:7] = 2; exp[3, 5] = 2
    exp[7:9, 5] = 3
    assert np.array_equal(g, exp)
    assert hidden_score.score_grid(g)[0] == 1.0
    # clipping and paint-over
    g = render(parse(tok((R, 10, 10, 5, 5, 1), (D, 11, 11, 4))))
    assert g[10, 10] == 1 and g[11, 11] == 4 and g.sum() == 1 * 4 - 1 + 4


def test_parse_rejects_bad_programs():
    good = tok((R, 1, 1, 2, 2, 1))
    assert parse(good) is not None
    assert parse(good[:-1]) is None                                    # missing END
    assert parse([R, NUM0 + 1, NUM0 + 1, NUM0 + 2, END]) is None       # wrong arity
    assert parse(tok((R, 1, 1, 0, 2, 1))) is None                      # h = 0 out of range
    assert parse(tok((R, 1, 1, 2, 2, 5))) is None                      # colour 5
    assert parse(tok((D, 12, 0, 1))) is None                           # row 12
    assert parse(tok(*[(D, 0, 0, 1)] * 7)) is None                     # 7 commands
    assert parse(tok(*[(D, 0, 0, 1)] * 6)) is not None
    assert parse(good + [NUM0]) is None                                # junk after END
    assert parse([paint.PAD, END]) is None
    assert parse([R, END]) is None


def test_copy_distance_shift_and_mirror(data):
    y = data.critic[:5]
    guard = copyguard.CopyGuard(y)
    x = np.zeros((12, 12), dtype=np.int8)
    x[1:, 1:] = y[0][:-1, :-1]                                          # shifted copy
    assert guard.distances(x)[0] == 0
    assert guard.distances(y[2][:, ::-1])[0] == 0                       # mirror
    assert copyguard.distance(y[3], y) == 0
    other = data.heldback[0]
    assert copyguard.distance(other, y) >= 1
    k = copyguard.calibrate_k(data.heldback, data.critic)
    assert k >= 0


def test_night_does_not_import_hidden_score():
    src = open(night.__file__).read()
    tree = ast.parse(src)
    mods = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            mods |= {(n.module or "") + "." + a.name for a in n.names} | {n.module or ""}
    assert not any("hidden_score" in m or "oracle" in m or m.endswith("eval") or ".eval" in m for m in mods), mods
    # nor transitively, as seen by a fresh interpreter
    code = "import sys, tc1.night; bad=[m for m in sys.modules if m in ('tc1.hidden_score','tc1.oracle','tc1.eval')]; print(bad)"
    root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    out = subprocess.run([sys.executable, "-c", code], cwd=root, capture_output=True, text=True).stdout.strip()
    assert out == "[]", out


@pytest.fixture(scope="module")
def ctx(tmp_path_factory):
    cfg = make_config(True, pretrain_programs=3000, pretrain_batch=64, pool=500, heldout=100,
                      requests=32, days=1, critic_steps=10, eval_samples=50)
    torch.set_num_threads(2)
    d = tmp_path_factory.mktemp("ck")
    return cfg, str(d), run_mod.prepare(1, cfg, str(d), log=lambda *a: None)


def test_perturbed_hidden_score_leaves_kept_rows_unchanged(ctx, monkeypatch):
    cfg, ck, c = ctx
    base = {}
    for arm in ("C", "R", "B", "H"):
        r, kept = run_mod.run_one(arm, 1, cfg, ck, log=lambda *a: None, ctx=c)
        assert sum(d["passes"] for d in r["days"]) > 0 and len(kept[0]) == cfg.requests
        base[arm] = kept
    rng = np.random.default_rng(123)
    monkeypatch.setattr(hidden_score, "score_grid",
                        lambda g: (float(rng.random()), tuple(bool(b) for b in rng.random(5) < .5)))
    for arm in ("C", "R", "B", "H"):
        r, kept = run_mod.run_one(arm, 1, cfg, ck, log=lambda *a: None, ctx=c)
        assert kept == base[arm], arm


def test_same_seed_same_request_streams(ctx):
    cfg, ck, c = ctx
    a, b = night.request_noise(1, 1, 32), night.request_noise(1, 1, 32)
    assert np.array_equal(a.u_tok, b.u_tok) and np.array_equal(a.u_pick, b.u_pick)
    assert not np.array_equal(a.u_tok, night.request_noise(1, 2, 32).u_tok)
    assert not np.array_equal(a.u_tok, night.request_noise(2, 1, 32).u_tok)
    from tc1.maker import Maker
    from tc1.copyguard import CopyGuard
    m = Maker(); m.load_state_dict(c.state); m.eval()
    g = CopyGuard(c.data.critic, c.k)
    t1 = night.make_tries(m, 1, 1, 32, 8, 1.0, g)
    t2 = night.make_tries(m, 1, 1, 32, 8, 1.0, g)
    assert t1.tokens == t2.tokens
    # arms C and R both start day 1 from the same weights and so see identical tries
    t16 = night.make_tries(m, 1, 1, 32, 16, 1.0, g)
    assert t16.tokens[0:8] == t1.tokens[0:8]


def test_mean_hidden_score_of_random_programs():
    rng = np.random.default_rng(0)
    s = []
    for _ in range(2000):
        g = render(parse(paint.random_program(rng)))
        s.append(hidden_score.score_grid(g)[0])
    m = float(np.mean(s))
    print(f"\nMEAN HIDDEN SCORE OF 2000 RANDOM DAY-0 PROGRAMS: {m:.4f}")
    assert 0.0 <= m < 0.5
