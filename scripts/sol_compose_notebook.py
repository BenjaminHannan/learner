"""Raw provenance store and latent-only memory boundary for a joined driver.

Human origin must be attested by the ingest caller, not guessed by the model.
No model-produced facts, templates, answer strings or generated English targets.
The raw store never belongs to an output translator. ByteFactEncoder is an
UNTRAINED compatible thin encoder, not a claim of English understanding.
"""
from __future__ import annotations
import base64
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import torch
from torch import nn


class NotebookStore:
    def __init__(self, path):
        self.path = Path(path)
        self.entries = []
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                entry = json.loads(line)
                payload = base64.b64decode(entry['payload_base64'])
                if hashlib.sha256(payload).hexdigest() != entry['payload_sha256']:
                    raise ValueError('notebook provenance digest mismatch')
                if entry['origin'] not in ('verified_human', 'symbolic_code'):
                    raise ValueError('unauthorized notebook origin')
                self.entries.append(entry)

    def append(self, payload: bytes, *, origin, source_ref, origin_evidence):
        if origin not in ('verified_human', 'symbolic_code') or not source_ref or not origin_evidence:
            raise ValueError('explicit human/code provenance evidence required')
        if not isinstance(payload, bytes):
            raise TypeError('retain exact bytes; encode human text as UTF-8 before ingest')
        digest = hashlib.sha256(payload).hexdigest()
        entry = dict(entry_id=len(self.entries), origin=origin, source_ref=source_ref,
                     origin_evidence=origin_evidence, payload_base64=base64.b64encode(payload).decode(),
                     payload_sha256=digest)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open('a') as f:
            f.write(json.dumps(entry, sort_keys=True) + '\n')
        self.entries.append(entry)
        return entry['entry_id']

    def raw(self, entry_ids):
        # Ingest/input encoder only. Output decoder never receives this store.
        return [base64.b64decode(self.entries[i]['payload_base64']) for i in entry_ids]

    def references(self, entry_ids):
        return [{k: self.entries[i][k] for k in ('entry_id','payload_sha256','source_ref','origin_evidence')}
                for i in entry_ids]


@dataclass(frozen=True)
class NotebookState:
    translated: torch.Tensor  # [B,M,64], supplied by learned input translator
    mask: torch.Tensor        # bool[B,M]; raw bytes and references stay outside

    def __post_init__(self):
        if (self.translated.ndim != 3 or self.translated.shape[-1] != 64 or
                self.mask.shape != self.translated.shape[:2] or self.mask.dtype != torch.bool or
                self.mask.device != self.translated.device):
            raise ValueError('NotebookState requires floating[B,M,64], bool[B,M] on one device')
        if not self.translated.is_floating_point():
            raise TypeError('translated human text must be floating latent vectors')

    @property
    def values(self):
        return self.translated

    @property
    def valid(self):
        return self.mask

    def select(self, ids):
        return NotebookState(self.translated[ids], self.mask[ids])

    def detached(self):
        return NotebookState(self.translated.detach(), self.mask)


class ByteFactEncoder(nn.Module):
    """A shape-compatible raw UTF-8 -> latent encoder, without a solver.

    Intended replacement: the joined model's learned input translator. This
    random byte encoder is not trained by the symbolic experiment and cannot
    support claims about English comprehension or grammatical generation.
    """
    def __init__(self, width=64, max_bytes=512):
        super().__init__()
        self.max_bytes = max_bytes
        self.byte = nn.Embedding(256, width)
        self.position = nn.Embedding(max_bytes, width)
        self.attention = nn.MultiheadAttention(width, 4, batch_first=True)
        self.query = nn.Parameter(torch.randn(1,1,width)*.02)
        self.norm = nn.LayerNorm(width)

    def forward(self, payloads, references):
        if not payloads or len(payloads) != len(references):
            raise ValueError('nonempty payloads with provenance required')
        if any(not 0 < len(x) <= self.max_bytes for x in payloads):
            raise ValueError('split long raw entries before ingest; never silently truncate')
        device = self.byte.weight.device
        n = max(map(len, payloads))
        ids = torch.zeros(len(payloads), n, dtype=torch.long, device=device)
        valid = torch.zeros_like(ids, dtype=torch.bool)
        for i, payload in enumerate(payloads):
            ids[i,:len(payload)] = torch.tensor(list(payload), device=device)
            valid[i,:len(payload)] = True
        x = self.byte(ids) + self.position(torch.arange(n, device=device))[None]
        latent,_ = self.attention(self.query.expand(len(payloads),-1,-1), x,x,
                                 key_padding_mask=~valid, need_weights=False)
        values = self.norm(latent[:,0])[None]
        return NotebookState(values, torch.ones(1,len(payloads),dtype=torch.bool,device=device))


class FinalStateTranslator(nn.Module):
    """Minimal symbolic decoder boundary: only a final state tensor is accepted.

    Replace with a trained state-to-English decoder for a conversational PoC.
    This module has no notebook/raw-text/token-input argument or store pointer.
    """
    def __init__(self, width=64, vocab=125):
        super().__init__(); self.head = nn.Linear(width, vocab)

    def forward(self, final_state):
        if not isinstance(final_state, torch.Tensor) or final_state.ndim != 3:
            raise TypeError('final latent state tensor required')
        return self.head(final_state)
