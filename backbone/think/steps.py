"""Written steps and the step decoder (codi-plan P1 and P2b; used by think1.py arms ws, wsham, tsd, tsd1).

Written format (arms ws / wsham): the prompt ends with STEPS_TAIL instead of " [answer]" (the cue that asks for steps; the direct format keeps
" [answer]"), and the target is " Step 1: <line>. Step 2: <line>. The answer is: X" + EOS, or " The answer is: X" for a row without steps.
wsham: the part before " The answer is:" is replaced by the same number of filler tokens (" ." repeated, dot by dot).
Step decoder (arms tsd / tsd1): see StepDecoder.
"""
from __future__ import annotations

import contextlib

import torch
import torch.nn as nn

import board as B
from xent import fixed_cross_entropy

STEPS_TAIL = " [steps]"
ANSWER_MARK = "The answer is:"
FILL = " ."
SD_LAPS = 4  # decoder passes per row (= laps scored); lap k decodes step k, later laps the answer


def clean(line):
    """A step line as written in a target: stripped, with a final full stop if it has no sentence end."""
    line = line.strip()
    return line if line[-1:] in (".", "!", "?") else line + "."


def steps_of(row):
    return list(row.get("steps") or ())


def gold_text(steps):
    """" Step 1: <line> Step 2: <line> ..." (empty for no steps). The lines carry their own full stops."""
    return "".join(f" Step {i}: {clean(s)}" for i, s in enumerate(steps, 1))


def filler(enc, n):
    """n filler tokens: the ids of FILL repeated and cut to exactly n."""
    base = enc.ids(FILL)
    return (base * -(-n // len(base)))[:n]


def written_target(enc, row, sham=False):
    """(steps_ids, answer_ids) of a row's written target. steps_ids is empty for a row without steps; with sham it is filler of the same length.
    answer_ids = " The answer is: X" + EOS."""
    ids = enc.ids(gold_text(steps_of(row))) if steps_of(row) else []
    return (filler(enc, len(ids)) if sham else ids), enc.ids(" " + ANSWER_MARK) + enc.ids(" " + row["answer"]) + [enc.eos]


def written_example(enc, row, sham=False):
    """(prompt ids, target ids) for training the written format; the prompt is the direct prompt with STEPS_TAIL."""
    st, an = written_target(enc, row, sham)
    tgt = st + an
    return enc.prompt(row, reserve=len(tgt), tail=STEPS_TAIL)[0], tgt


def cut_for_target(enc, row, sham=False):
    """True if the written example's prompt had to be cut (context dropped from the left) to make room for its longer target, while the direct example's was not."""
    st, an = written_target(enc, row, sham)
    return enc.prompt(row, reserve=len(st) + len(an), tail=STEPS_TAIL)[1] and not enc.prompt(row, reserve=len(enc.ids(" " + row["answer"])) + 1)[1]


def gold_prompt(enc, row, sham=False):
    """The format check's input: the steps prompt + the gold steps (filler for sham) + " The answer is:"; the model writes the answer."""
    st, _ = written_target(enc, row, sham)
    tail = st + enc.ids(" " + ANSWER_MARK)
    return enc.prompt(row, reserve=len(tail), tail=STEPS_TAIL)[0] + tail


def parse_answer(text):
    """What follows the last "The answer is:" in generated text, or None if the marker is missing."""
    i = text.rfind(ANSWER_MARK)
    return None if i < 0 else text[i + len(ANSWER_MARK):]


def decoder_targets(enc, row, laps=SD_LAPS):
    """Per lap k = 1..laps: (prefix ids, target ids, is_step). Lap k <= n_steps: prefix "Step k:", target the step text. Later laps: no prefix,
    target "The answer is: X". The loss and the accuracy are on target ids only."""
    steps, out = steps_of(row), []
    for k in range(1, laps + 1):
        if k <= len(steps):
            out.append((enc.ids(f"Step {k}:"), enc.ids(" " + clean(steps[k - 1])), True))
        else:
            out.append(([], enc.ids(ANSWER_MARK) + enc.ids(" " + row["answer"]), False))
    return out


# ---------------------------------------------------------------- step decoder

@contextlib.contextmanager
def lora_adapter(pm, name, restore="default"):
    """Make `name` the only active LoRA adapter for the passes inside, then `restore`. Sets the layers' active list directly: peft's set_adapter would
    also switch requires_grad off for the other adapter (and recomputation of checkpointed passes happens in backward, when `restore` is active again)."""
    def use(n):
        for m in pm.modules():
            if hasattr(m, "lora_A") and hasattr(m, "_active_adapter"):
                m._active_adapter = [n]
    use(name)
    try:
        yield
    finally:
        use(restore)


def check_adapter_switch():
    """Guard against peft version drift: lora_adapter() relies on the LoRA layers' private `_active_adapter` list. On a tiny module with two adapters, check that
    switching changes the output, that leaving the context restores the main adapter, and that requires_grad is not touched. Runs at import."""
    try:
        from peft import LoraConfig, get_peft_model
    except ImportError:
        return
    class M(nn.Module):
        def __init__(self):
            super().__init__()
            self.lin = nn.Linear(4, 4)

        def forward(self, x):
            return self.lin(x)

    cfg = lambda: LoraConfig(r=2, lora_alpha=4, target_modules=["lin"], init_lora_weights=False)
    pm = get_peft_model(M(), cfg())
    pm.add_adapter("dec", cfg())
    for q in pm.parameters():
        if q.dtype.is_floating_point and "lora_" in next(n for n, p_ in pm.named_parameters() if p_ is q):
            q.requires_grad_(True)
    x, flags = torch.randn(3, 4), [q.requires_grad for q in pm.parameters()]
    with torch.no_grad():
        main = pm(x)
        with lora_adapter(pm, "dec"):
            dec = pm(x)
        after = pm(x)
    ok = (not torch.allclose(main, dec)) and torch.equal(main, after) and flags == [q.requires_grad for q in pm.parameters()]
    if not ok:
        import peft
        raise RuntimeError(f"peft {peft.__version__}: steps.lora_adapter no longer switches LoRA adapters (output unchanged by the switch, not restored, or requires_grad touched)")


class StepDecoder(nn.Module):
    """Reads only the notes. The frozen base model with its own LoRA adapter "dec" (the main adapter is off during the pass), the notes mapped by one
    Linear(note_dim -> hidden) to inputs_embeds at positions 0..K-1, then the prefix and target tokens; causal mask, ordinary positions. It never sees
    the story or the question. proj starts as the identity (notes live in input-embedding space) when the sizes agree."""

    def __init__(self, note_dim, hidden):
        super().__init__()
        self.proj = nn.Linear(note_dim, hidden)
        with torch.no_grad():
            if note_dim == hidden:
                self.proj.weight.copy_(torch.eye(hidden))
            self.proj.bias.zero_()

    def logits(self, pm, runner, notes, seqs):
        """notes [N, K, note_dim]; seqs: N (prefix ids, target ids). Returns (logits [M, V] fp32 at the target positions, targets [M], row of each)."""
        dev, N, K = notes.device, len(seqs), notes.shape[1]
        n = max(len(p) + len(t) for p, t in seqs)
        ids, rm = torch.zeros(N, n, dtype=torch.long), torch.zeros(N, K + n, dtype=torch.long)
        rm[:, :K] = 1
        for b, (p, t) in enumerate(seqs):
            ids[b, :len(p) + len(t)] = torch.tensor(list(p) + list(t))
            rm[b, K:K + len(p) + len(t)] = 1
        ids, rm = ids.to(dev), rm.to(dev)
        emb = runner.lm.model.embed_tokens
        x = torch.cat([self.proj(notes.float()).to(emb.weight.dtype), emb(ids)], 1)
        pos = torch.arange(K + n, device=dev)[None].expand(N, -1)
        with lora_adapter(pm, "dec"):
            h, _ = B.run_layers(runner, x, rm, pos)
        sb = torch.tensor([b for b, (p, t) in enumerate(seqs) for _ in t], device=dev)
        st = torch.tensor([K + len(p) + i - 1 for p, t in seqs for i in range(len(t))], device=dev)
        tgt = torch.tensor([x_ for p, t in seqs for x_ in t], device=dev)
        return B.f32(runner.logits(h[sb, st])), tgt, sb

    def step_ce(self, pm, runner, notes, seqs):
        """(summed fixed CE over the target tokens, their count)."""
        lg, tgt, _ = self.logits(pm, runner, notes, seqs)
        return fixed_cross_entropy(lg, tgt, reduction="sum"), len(tgt)

    @torch.no_grad()
    def token_hits(self, pm, runner, notes, seqs):
        """(correct argmax tokens, count) over the target tokens (teacher-forced)."""
        lg, tgt, _ = self.logits(pm, runner, notes, seqs)
        return int((lg.argmax(-1) == tgt).sum()), len(tgt)


def lap_notes(e, lmax, laps=SD_LAPS):
    """The notes each decoder pass reads, from B.think's boards e = [e_0, e_1, ..., e_lmax]: lap k reads e_k (arm tsd, lmax = laps); with lmax = 1
    (arm tsd1) the lap-1 notes feed every pass."""
    return [e[min(k, lmax)] for k in range(1, laps + 1)]


check_adapter_switch()
