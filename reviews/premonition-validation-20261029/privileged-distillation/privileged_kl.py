"""Paper-inspired, default-unused context distillation primitive.

No models, sampling, optimizer, or application integration. This is not the full
Sleep framework, LTI, RL, expert routing, or a retention guarantee.
"""
from dataclasses import dataclass

import torch
import torch.nn.functional as F


@dataclass(frozen=True)
class Limits:
    max_batch: int = 8
    max_sequence_tokens: int = 4096
    max_answer_tokens: int = 256
    max_total_bytes: int = 64 * 1024 * 1024
    max_vocab_size: int = 256000


def answer_kl(
    *,
    teacher_logits: torch.Tensor,
    student_logits: torch.Tensor,
    teacher_ids: torch.Tensor,
    student_ids: torch.Tensor,
    teacher_mask: torch.Tensor,
    student_mask: torch.Tensor,
    teacher_prefix_lengths: torch.Tensor,
    student_prefix_lengths: torch.Tensor,
    answer_lengths: torch.Tensor,
    teacher_vocab_id: str,
    student_vocab_id: str,
    limits: Limits = Limits(),
) -> torch.Tensor:
    """Return mean KL(teacher || student) over sampled answer tokens.

    Logits are [batch, sequence, vocabulary], with ordinary causal alignment:
    position i predicts token i+1. IDs/masks cover the SAME sequence positions
    as each corresponding logits tensor. Prefix lengths exclude padding and
    include every prompt/BOS/generation-prefix token. Masks must describe one
    contiguous valid sequence per row, allowing left and/or right padding.
    answer_lengths explicitly exclude padding and may include a sampled EOS.

    Teacher and student have different prefixes but identical sampled answers.
    The caller supplies a pinned tokenizer/vocabulary identity, not a label for
    the checkpoint. Equal vocabulary dimensions alone do not prove equal IDs.

    Samples/teacher targets are detached; no gradient flows through sampling.
    Student logits retain their graph. Full-vocabulary KL is used; no top-k or
    sampled-token approximation is silently substituted.
    """
    tensors = [teacher_logits, student_logits, teacher_ids, student_ids,
               teacher_mask, student_mask, teacher_prefix_lengths,
               student_prefix_lengths, answer_lengths]
    if not all(isinstance(x, torch.Tensor) for x in tensors):
        raise ValueError("all array arguments must be tensors")
    cap_values = vars(limits).values()
    if any(type(v) is not int or v <= 0 for v in cap_values):
        raise ValueError("limits must be positive integers")
    if sum(x.numel() * x.element_size() for x in tensors) > limits.max_total_bytes:
        raise ValueError("sample exceeds input byte limit")
    if (not isinstance(teacher_vocab_id, str) or not teacher_vocab_id
            or not isinstance(student_vocab_id, str)
            or teacher_vocab_id != student_vocab_id):
        raise ValueError("tokenizer/vocabulary identities differ or are empty")
    if teacher_logits.ndim != 3 or student_logits.ndim != 3:
        raise ValueError("logits must have shape [batch, sequence, vocab]")
    b, _, v = teacher_logits.shape
    if b < 1 or b > limits.max_batch or v < 2 or v > limits.max_vocab_size:
        raise ValueError("empty or oversized batch/vocabulary")
    if student_logits.shape[0] != b or student_logits.shape[2] != v:
        raise ValueError("batch/vocabulary dimensions differ")
    if teacher_logits.device != student_logits.device:
        raise ValueError("logits must share a device")
    if any(not x.is_floating_point() for x in [teacher_logits, student_logits]):
        raise ValueError("logits must be floating point")
    for x in [teacher_prefix_lengths, student_prefix_lengths, answer_lengths]:
        if x.shape != (b,) or x.dtype not in (torch.int32, torch.int64):
            raise ValueError("lengths must be integer [batch] tensors")
    # Integer samples are constant conditioning data, never differentiable
    # samples or soft token embeddings.
    lengths = answer_lengths.detach().cpu().tolist()
    if any(n < 1 or n > limits.max_answer_tokens for n in lengths):
        raise ValueError("empty or oversized answer")

    def select(logits, ids, mask, prefixes):
        if logits.shape[1] < 1 or logits.shape[1] > limits.max_sequence_tokens:
            raise ValueError("empty or oversized sequence")
        if ids.shape != logits.shape[:2] or mask.shape != ids.shape:
            raise ValueError("IDs/mask must cover each logits position")
        if ids.dtype not in (torch.int32, torch.int64) or mask.dtype != torch.bool:
            raise ValueError("IDs must be integer and masks boolean")
        if ids.device != logits.device or mask.device != logits.device:
            raise ValueError("IDs/mask/logits must share a device")
        if not bool(torch.isfinite(logits).all()):
            raise ValueError("non-finite logits")
        rows, sampled = [], []
        # Small bounded batches make explicit validation preferable to silent
        # clipping. This synchronization is deliberate in this reference helper.
        for r, (p, n) in enumerate(zip(prefixes.detach().cpu().tolist(), lengths)):
            valid = mask[r].detach().nonzero(as_tuple=False).flatten()
            if valid.numel() == 0:
                raise ValueError("empty sequence mask")
            start, end = int(valid[0]), int(valid[-1]) + 1
            if valid.numel() != end - start:
                raise ValueError("interior padding is unsupported")
            if p < 1 or p + n > valid.numel():
                raise ValueError("prefix/answer exceeds valid sequence bounds")
            valid_ids = ids[r, start:end].detach()
            if bool(((valid_ids < 0) | (valid_ids >= v)).any()):
                raise ValueError("valid token ID outside vocabulary")
            answer_start = start + p
            sampled.append(ids[r, answer_start:answer_start + n].detach())
            # Answer token j is predicted by prefix_len - 1 + j, NOT by
            # prefix_len + j. Offset accounts for left padding.
            rows.append(logits[r, answer_start - 1:answer_start + n - 1])
        return torch.cat(rows, dim=0), torch.cat(sampled, dim=0)

    teacher_rows, teacher_answers = select(
        teacher_logits.detach(), teacher_ids, teacher_mask, teacher_prefix_lengths)
    student_rows, student_answers = select(
        student_logits, student_ids, student_mask, student_prefix_lengths)
    if not torch.equal(teacher_answers, student_answers):
        raise ValueError("teacher/student sampled answer IDs differ")
    # Preserve double precision for numerical tests, otherwise accumulate in
    # float32 even when a future caller supplies BF16/FP16 logits.
    dtype = torch.float64 if torch.float64 in (
        teacher_rows.dtype, student_rows.dtype) else torch.float32
    teacher_logp = F.log_softmax(teacher_rows.to(dtype), dim=-1).detach()
    student_logp = F.log_softmax(student_rows.to(dtype), dim=-1)
    loss = F.kl_div(student_logp, teacher_logp,
                    log_target=True, reduction="sum") / sum(lengths)
    if not bool(torch.isfinite(loss)):
        raise ValueError("non-finite KL")
    return loss
