"""Run configuration for TC-1 (spec section 8). No hidden-score imports here."""
from dataclasses import dataclass, asdict, replace


@dataclass
class Config:
    # day / night loop
    requests: int = 512
    tries: int = 8
    days: int = 6
    temp: float = 1.0
    night_visits: int = 16
    night_kept: int = 32
    night_replay: int = 32
    night_lr: float = 3e-4
    # day-0 pretraining
    pretrain_programs: int = 200_000
    pretrain_epochs: int = 2
    pretrain_batch: int = 256
    pretrain_lr: float = 1e-3
    pretrain_lr_min: float = 1e-4
    pool: int = 20_000
    prior: str = "clutter"       # day-0 programs: "clutter" (TC-1) or "touching" (TC-1b)
    heldout: int = 2_000
    weight_decay: float = 0.01
    grad_clip: float = 1.0
    # critic
    critic_steps: int = 300
    critic_batch: int = 128
    critic_lr: float = 1e-3
    r1_weight: float = 1.0
    # evaluation
    eval_samples: int = 1000
    small: bool = False

    def to_dict(self):
        return asdict(self)


def make_config(small=False, days=None, **over):
    cfg = Config()
    if small:
        cfg = replace(cfg, requests=64, days=2, pretrain_programs=8000, pretrain_batch=64,
                      pool=2000, heldout=200, critic_steps=50, eval_samples=200, small=True)
    if days is not None:
        cfg = replace(cfg, days=days)
    over = {k: v for k, v in over.items() if v is not None}
    return replace(cfg, **over)
