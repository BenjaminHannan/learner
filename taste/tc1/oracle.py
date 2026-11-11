"""Arm O's pick support (the only night-path module besides eval.py that imports hidden_score)."""
import numpy as np
from . import hidden_score


def scores(grids):
    grids = np.asarray(grids)
    return np.array([hidden_score.score_grid(g)[0] for g in grids], dtype=np.float64)
