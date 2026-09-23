"""Address-keyed evidence selection (milestone-3 continuation 3 diagnostic; DEFAULT OFF, NOT promoted).

Motivation (reviews/opus-milestone-03-probe-binding.md): in the pooled and direct answer-only models the decoder
chooses among supplied cards by the value word a card holds, not by whether its person and relation match the
question. In D the decoder's cross-attention computes the KEY and the VALUE of a card row from the same vector
(value(pooled line) + age + type), so selection can be driven by the value word.

This variant separates them for the inserted evidence (card) rows only:
    selection key  k = W_addr LN([embed(line token 1); embed(line token 2)])     (new: W_addr, 2d x d + d)
    answer value   the decoder's ordinary value projection of the ordinary pooled card row (unchanged)
Every other decoder row (question rows, entity slots, registers) and every other computation is unchanged. The query
side is the decoder's own learned cross-attention query (it has read the question prefix), so the match between the
question and each card's address is learned: score = q(question) . W_addr [person; relation].

EXPLICIT STRUCTURAL HELP given to the model (declared; the pooled and direct controls do not get it):
  1. A parse of the synthetic line layout: for every inserted line the variant reads token 1 (the subject person)
     and token 2 (the relation, or LINK) of that line. This is format knowledge about the toy's visible input,
     applied identically to every supplied line.
  2. The address uses non-contextual input embeddings of those two tokens, so it is exactly the (person, relation)
     identity of the line, and candidate value words (line token 3 onward) cannot enter the selection key.
  3. A hard constraint: card selection keys come ONLY from the address.
NOT used for selection: gold-card identities, answer labels, triplet roles or any intervention metadata (the address
is computed from visible line tokens of whatever cards are inserted; supplied evidence is the same privileged set
the controls receive).

Decode-only (nothink): Think passes are refused (the address rows appended to the episode are not think rows). With
no cards inserted the decode is identical to the pooled baseline's. Address rows live on the episode, never on the
module (read-only evaluation). A NULL card (never supplied here) would get the all-zero address.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import torch
from torch import nn
import torch.nn.functional as F

from premonition.model import _norm, rope
from premonition.ovn_qread import QReadMini

VERSION = 1
VARIANT = "nothink+qread+addresskeys"
PERSON_OFFSET, RELATION_OFFSET = 1, 2        # synthetic line layout: [WORLD, subject, relation-or-LINK, object, ...]
ADDRESS_INIT_SEED = 7000                     # + model seed: dedicated generator (the global stream is untouched)


def addressed_decoder(dec, x, memory, valid, card_keys=None, card_base: int = 0):
    """premonition.model.Decoder.forward, except that the cross-attention keys of the card rows
    [card_base, card_base + C) are replaced by `card_keys` [n, C, d] when given (values unchanged)."""
    n, length, width = x.shape
    heads = dec.heads
    q, k, v = dec.qkv(dec.norm1(x)).view(n, length, 3, heads, -1).permute(2, 0, 3, 1, 4)
    positions = torch.arange(length, device=x.device)
    q, k = rope(q, positions, dec.base), rope(k, positions, dec.base)
    attended = F.scaled_dot_product_attention(q, k, v, is_causal=True)
    x = x + dec.proj(attended.transpose(1, 2).reshape(n, length, width))
    q = dec.cross_q(dec.norm2(x)).view(n, length, heads, -1).transpose(1, 2)
    k, v = dec.cross_kv(_norm(memory)).view(n, memory.shape[1], 2, heads, -1).permute(2, 0, 3, 1, 4)
    if card_keys is not None:
        count = card_keys.shape[1]
        keys = card_keys.view(n, count, heads, -1).transpose(1, 2).to(k.dtype)
        k = torch.cat([k[:, :, :card_base], keys, k[:, :, card_base + count:]], dim=2)
    attended = F.scaled_dot_product_attention(q, k, v, attn_mask=valid[:, None, None, :])
    x = x + dec.cross_proj(attended.transpose(1, 2).reshape(n, length, width))
    x = x + dec.mlp(dec.norm3(x))
    return dec.norm(x)


class AddressKeyedQReadMini(QReadMini):
    """nothink+qread whose card rows are SELECTED by learned address keys (see module docstring)."""

    variant_name = "D+qread+addresskeys"
    address_keys = True

    def __init__(self, config) -> None:
        super().__init__(config)
        with torch.random.fork_rng(devices=[]):          # construction must not consume the global stream
            self.address = nn.Linear(2 * config.d_model, config.d_model)
        self.reset_address(0)

    def reset_address(self, seed: int) -> None:
        generator = torch.Generator().manual_seed(ADDRESS_INIT_SEED + seed)
        with torch.no_grad():
            self.address.weight.normal_(0.0, 0.02, generator=generator)
            self.address.bias.zero_()

    @property
    def _address_base(self) -> int:
        return self.config.rows

    def _start(self, batch, hidden, store, mentions):
        episode = super()._start(batch, hidden, store, mentions)
        count, _, d = episode.x.shape
        extra = 2 * self.config.cards                      # person rows, then relation rows, one per card slot
        episode.x = torch.cat([episode.x, episode.x.new_zeros(count, extra, d)], dim=1)
        episode.valid = torch.cat([episode.valid, torch.zeros(count, extra, dtype=torch.bool,
                                                              device=episode.valid.device)], dim=1)
        episode.address_tokens = batch.tokens            # visible (label-free) input tokens only
        return episode

    def _step(self, episode, index, step, store):
        raise NotImplementedError("the address-key diagnostic is decode-only (nothink); Think passes are refused")

    def _insert(self, episode, store, index, cards):
        real = cards >= 0
        if not bool(real.any()):
            return
        before = episode.count[index].clone()
        super()._insert(episode, store, index, cards)    # ordinary pooled card rows, slots, count, fetched
        config = self.config
        _, _, lines = store.gather(cards, episode.q_visit[index])
        visit = episode.q_visit[index].unsqueeze(1).expand_as(lines)
        ok = real & (lines >= 0)
        start = store.line_start[visit, lines.clamp_min(0)]
        if bool((ok & ((start < 0) | (store.line_len[visit, lines.clamp_min(0)] <= RELATION_OFFSET))).any()):
            raise ValueError("an inserted line is too short for the declared address layout")
        tokens = episode.address_tokens
        subject = tokens[visit, (start + PERSON_OFFSET).clamp_min(0)]
        if bool((ok & (subject < config.vocab_size)).any()):
            raise ValueError("line token 1 of an inserted line is not a person (layout assumption violated)")
        person = self.embed(subject)
        relation = self.embed(tokens[visit, (start + RELATION_OFFSET).clamp_min(0)])
        zero = torch.zeros_like(person)
        person, relation = torch.where(ok.unsqueeze(-1), person, zero), torch.where(ok.unsqueeze(-1), relation, zero)
        slot = (before.unsqueeze(1) + real.long().cumsum(1) - 1) % config.card_rows     # = the card row's FIFO slot
        who = index.unsqueeze(1).expand_as(cards)
        base = self._address_base
        episode.x = episode.x.index_put((who[real], base + slot[real]), person[real].to(episode.x.dtype))
        episode.x = episode.x.index_put((who[real], base + config.cards + slot[real]),
                                        relation[real].to(episode.x.dtype))

    def address_keys_of(self, rows: torch.Tensor) -> torch.Tensor:
        """[n, C, d] selection keys of the card slots from the episode's address rows."""
        base, count = self._address_base, self.config.cards
        person, relation = rows[:, base:base + count], rows[:, base + count:base + 2 * count]
        return self.address(_norm(torch.cat([person, relation], dim=-1)))

    def _decode_logits(self, rows, valid, inputs):
        base = self._address_base
        if rows.shape[1] != base + 2 * self.config.cards:
            raise ValueError("episode rows do not carry the address region")
        return addressed_decoder(self.decoder, self.embed(inputs), rows[:, :base], valid[:, :base],
                                 self.address_keys_of(rows), self._card_base)


def identity(config) -> dict:
    return {"variant": VARIANT, "class": "AddressKeyedQReadMini", "module": "premonition/address_reader.py",
            "version": VERSION, "sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "new_parameters": 2 * config.d_model * config.d_model + config.d_model,
            "address": "LN([embed(line token 1); embed(line token 2)]) -> Linear; card-row keys only",
            "structural_help": ["synthetic line-layout parse (token 1 subject, token 2 relation/LINK)",
                                "non-contextual embeddings: value words cannot enter selection keys",
                                "card selection keys come only from the address"],
            "not_used_for_selection": ["gold-card identities", "answer labels", "intervention metadata"],
            "address_init": f"normal(0, 0.02) from Generator({ADDRESS_INIT_SEED} + seed); bias 0",
            "default": False, "purpose": "diagnostic"}


__all__ = ["ADDRESS_INIT_SEED", "AddressKeyedQReadMini", "VARIANT", "VERSION", "addressed_decoder", "identity"]
