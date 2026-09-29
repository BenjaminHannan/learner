"""Pond arm z: lambda = 0.0 (see claude_dir_pond_stop.py). Harness use: --plugin claude_dir_pond_z"""
import claude_dir_pond_stop as _P
from claude_dir_pond_stop import *  # noqa: F401,F403  (Net, ARMS, tensors, ... the harness reads these)

LAMBDA = 0.0
Learner = _P.make_learner(LAMBDA)
