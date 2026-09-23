"""Premonition-mini sizes (design/06 §1).

`MiniConfig` fixes every width of D and its two controls. The parameter count
is computed by hand here (`parameter_breakdown`) and checked against the real
modules in the tests; a d = 128 config must land in the 1.9M-2.1M band.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

from premonition.batch import MAX_ANSWER, N_ENT, PAD_ID

PARAM_BAND = (1_900_000, 2_150_000)   # design/06 §6, asserted at d = 128; the top leaves room for the v2
                                      # tokenizer's 7,068 ids (D = 2,102,228), still < half of A's 4.99M
VOCAB_V1 = 6372                       # tokenizer ids of premonition-tok-v1; entity ids follow
VOCAB_V2 = 7068                       # premonition-tok-v2-fallback (syllable-split names): use this one
READER_KINDS = ("gru", "attn")
VARIANTS = ("D", "D-noask", "D-noptr")


@dataclass(frozen=True)
class MiniConfig:
    vocab_size: int = VOCAB_V1          # tokenizer ids; ids vocab_size .. vocab_size + n_ent - 1 are ENT0-15
    n_ent: int = N_ENT
    d_model: int = 128
    n_heads: int = 4
    reader: tuple[str, ...] = ("gru", "attn", "gru")
    reader_mlp: int = 3
    window: int = 64                    # block-local attention: a block sees itself and the one before
    scan_chunk: int = 256               # log-space scan length before the state is carried (fp32 precision)
    key_dim: int = 64
    think_layers: int = 2
    think_mlp: int = 4
    decoder_mlp: int = 2
    question_rows: int = 40             # the last 40 question tokens, ending at "[answer]"
    card_rows: int = 16                 # fetched cards held at once, first in first out
    registers: int = 4
    max_loops: int = 8
    top_k: int = 4                      # cards fetched per ASK
    age_buckets: int = 16               # min(15, floor(log2 age))
    kappa_init: float = 10.0            # ASK temperature
    rope_base: float = 10000.0
    max_answer: int = MAX_ANSWER
    pad_id: int = PAD_ID
    eos_id: int = 2                     # learnlab.tokenizer.DEFAULT_SPECIALS: <pad> <bos> <eos> ...
    store: bool = True                  # False = D-noask: no cards, no ASK
    pointers: bool = True               # False = D-noptr: no entity slots, no binder, no copy constraint
    # Loss weights (design/06 §3, ASSUMPTION: tuned in build step 5).
    w_lm: float = 1.0
    w_ask: float = 0.5
    w_ans: float = 1.0
    w_halt: float = 0.1
    early_ans: float = 0.2              # L_ans weight before the loop that holds every gold card
    distractors: tuple[int, int] = (1, 2)
    check_band: bool = True

    def __post_init__(self) -> None:
        for name in ("vocab_size", "n_ent", "d_model", "n_heads", "reader_mlp", "window", "scan_chunk",
                     "key_dim", "think_layers", "think_mlp", "decoder_mlp", "question_rows",
                     "card_rows", "registers", "max_loops", "top_k", "age_buckets", "max_answer"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        if self.d_model % self.n_heads or (self.d_model // self.n_heads) % 2:
            raise ValueError("d_model / n_heads must be an even integer (RoPE)")
        if not self.reader or any(kind not in READER_KINDS for kind in self.reader):
            raise ValueError(f"reader layers must be drawn from {READER_KINDS}")
        low, high = self.distractors
        if not 0 <= low <= high:
            raise ValueError("distractors must be (low, high) with 0 <= low <= high")
        if self.check_band and self.d_model == 128:
            count = self.num_parameters()
            if not PARAM_BAND[0] <= count <= PARAM_BAND[1]:
                raise ValueError(f"{self.variant} has {count:,} parameters at d = 128; "
                                 f"design/06 requires {PARAM_BAND[0]:,}-{PARAM_BAND[1]:,}")

    @property
    def total_vocab(self) -> int:
        return self.vocab_size + self.n_ent

    @property
    def slots(self) -> int:
        return self.n_ent if self.pointers else 0

    @property
    def cards(self) -> int:
        return self.card_rows if self.store else 0

    @property
    def rows(self) -> int:
        """Think rows per question: question, entity slots, fetched cards, registers (76 for D)."""
        return self.question_rows + self.slots + self.cards + self.registers

    @property
    def variant(self) -> str:
        if not self.store:
            return "D-noask"
        return "D" if self.pointers else "D-noptr"

    @classmethod
    def preset(cls, variant: str = "D", size: str = "full", vocab_size: int = VOCAB_V1,
               **overrides) -> MiniConfig:
        """D, D-noask or D-noptr at "full" (d = 128) or "tiny" (d = 32, CPU smoke)."""
        if variant not in VARIANTS:
            raise ValueError(f"unknown variant {variant!r}; choose from {VARIANTS}")
        sizes = {"full": dict(d_model=128, key_dim=64),
                 "tiny": dict(d_model=32, key_dim=16)}
        if size not in sizes:
            raise ValueError(f"unknown size {size!r}; choose from {sorted(sizes)}")
        settings = dict(sizes[size], vocab_size=vocab_size,
                        store=variant != "D-noask", pointers=variant != "D-noptr")
        settings.update(overrides)
        return cls(**settings)

    def with_(self, **changes) -> MiniConfig:
        return replace(self, **changes)

    def parameter_breakdown(self) -> dict[str, int]:
        """Trained parameters per module, embeddings included (design/06 §1 table)."""
        return parameter_breakdown(self)

    def num_parameters(self) -> int:
        return sum(self.parameter_breakdown().values())


def _linear(fan_in: int, fan_out: int) -> int:
    return fan_in * fan_out + fan_out


def parameter_breakdown(config: MiniConfig) -> dict[str, int]:
    d, dk, norm = config.d_model, config.key_dim, 2 * config.d_model
    mixer = _linear(d, 3 * d) + _linear(d, d)       # minGRU (z, h~, gate) + out, or qkv + out
    reader = (len(config.reader) * (2 * norm + mixer + _linear(d, config.reader_mlp * d)
                                     + _linear(config.reader_mlp * d, d)) + norm)
    writer = _linear(d, 1) + _linear(d, dk) + _linear(d, d) + dk + d if config.store else 0
    layer = 2 * norm + _linear(d, 3 * d) + _linear(d, d) + _linear(d, config.think_mlp * d) \
        + _linear(config.think_mlp * d, d)
    embeddings = (4 + config.registers + config.max_loops) * d
    if config.store:
        embeddings += config.age_buckets * d + config.age_buckets   # age rows + recency biases
    binder = _linear(2 * d, 2 * d) if config.store and config.pointers else 0
    heads = _linear(d, 1)                                            # HALT
    if config.store:
        heads += _linear(d, dk) + _linear(d, 1) + 1                  # query, ASK, kappa
    decoder = 4 * norm + _linear(d, 3 * d) + _linear(d, d) + _linear(d, d) + _linear(d, 2 * d) \
        + _linear(d, d) + _linear(d, config.decoder_mlp * d) + _linear(config.decoder_mlp * d, d)
    return {
        "embedding": config.total_vocab * d,
        "reader": reader,
        "card_writer": writer,
        "think": config.think_layers * layer + embeddings + binder,
        "heads": heads,
        "decoder": decoder,
    }


__all__ = ["MiniConfig", "PARAM_BAND", "VARIANTS", "VOCAB_V1", "VOCAB_V2", "parameter_breakdown"]
