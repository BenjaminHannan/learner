"""Pure-Python/numpy decoder for the talker's byte-level BPE (ids -> text).

Written by scripts/fable_talker24_data.py. Needs only the standard library (numpy is
optional -- ids may be a list or any numpy integer array). The GPU box has torch+numpy
but no `tokenizers`, so this is the only decoder it needs.

    from decode_numpy import Decoder
    dec = Decoder("shards/tokenizer_vocab.json")
    dec.decode(ids)
    dec.decode(ids, ents=codes, names={7: "Mira"})
"""

import json

SPECIALS = {
    "<pad>": 0, "<bos>": 1, "<eos>": 2, "<unk>": 3, "<ENT>": 4, "<SUBJ>": 5,
    "<OBJ>": 6, "<OLD>": 7, "<TURN>": 8, "<DOC>": 9, "<extra_0>": 10, "<extra_1>": 11,
    "<extra_2>": 12, "<extra_3>": 13, "<extra_4>": 14, "<extra_5>": 15,
}
ENT_NONE = 0xFFFF
_INVISIBLE = {0, 1, 2, 3, 9}          # pad, bos, eos, unk, doc  -> ""
ID_ENT, ID_TURN = 4, 8
COPY_IDS = {5: "<SUBJ>", 6: "<OBJ>", 7: "<OLD>"}


def bytes_to_unicode():
    bs = (list(range(ord("!"), ord("~") + 1))
          + list(range(0xA1, 0xAC + 1)) + list(range(0xAE, 0xFF + 1)))
    cs = bs[:]
    n = 0
    for b in range(256):
        if b not in bs:
            bs.append(b)
            cs.append(256 + n)
            n += 1
    return {b: chr(c) for b, c in zip(bs, cs)}


class Decoder:
    def __init__(self, vocab_path):
        with open(vocab_path, "r", encoding="utf-8") as fh:
            vocab = json.load(fh)
        size = max(vocab.values()) + 1
        self.id_to_piece = [""] * size
        for piece, i in vocab.items():
            self.id_to_piece[i] = piece
        self.byte_decoder = {v: k for k, v in bytes_to_unicode().items()}

    def piece_to_text(self, piece):
        return bytes(self.byte_decoder[c] for c in piece).decode("utf-8", errors="replace")

    def decode(self, ids, ents=None, names=None, copy=None,
               capitalize_sentences=False):
        """ids -> text. `ents[i]` supplies the entity code at an <ENT> position."""
        out = []
        buf = []                     # pending byte-level pieces

        def flush():
            if buf:
                out.append(self.piece_to_text("".join(buf)))
                del buf[:]

        for i, raw in enumerate(ids):
            t = int(raw)
            if t in _INVISIBLE:
                continue
            if t == ID_TURN:
                flush()
                out.append("\n")
                continue
            if t == ID_ENT:
                flush()
                code = int(ents[i]) if ents is not None else ENT_NONE
                if names is not None and code in names:
                    out.append(names[code])
                elif code != ENT_NONE:
                    out.append("<ent:%d>" % code)
                else:
                    out.append("<ENT>")
                continue
            if t in COPY_IDS:
                flush()
                out.append((copy or {}).get(t, COPY_IDS[t]))
                continue
            piece = self.id_to_piece[t] if t < len(self.id_to_piece) else ""
            buf.append(piece)
        flush()
        text = "".join(out)
        if capitalize_sentences:
            text = _capitalize(text)
        return text


def _capitalize(text):
    out = []
    start = True
    for ch in text:
        if start and ch.isalpha():
            out.append(ch.upper())
            start = False
        else:
            out.append(ch)
            if ch in ".!?\n":
                start = True
    return "".join(out)
