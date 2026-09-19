"""Persistent-learning research prototype with GRU and recurrent-transformer backbones."""

from .model import MainNetwork
from .transformer_model import RecurrentTransformerLearner

__all__ = ["MainNetwork", "RecurrentTransformerLearner"]
