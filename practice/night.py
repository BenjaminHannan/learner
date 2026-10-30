"""Night training for Practice-1. Fresh LoRA on the base model each night, trained on lessons drawn from ALL tries gathered so far (expert iteration).
Arm P (checker): SFT on solved tries + DPO pairs (solved, failed) on the same puzzle. Arm C (no checker): same counts, drawn from all tries uniformly,
pairs are two random tries of the same puzzle in random order. Fixed size every night: N_SFT x EPOCHS sft items + up to N_PAIRS pairs (DPO beta 0.1,
weight 0.2), the same number of optimizer steps in both arms. Loss only on assistant turns (tool outputs and prompts are masked)."""
import random

from sleep2.askonce.config import LR
from sleep2.askonce.train_core import LoRATrainer

from .lessons import (DPO_W, EPOCHS, MAX_TRAIN_TOKENS, N_PAIRS, N_SFT, N_STEPS, build_lessons, segments, steps_for,  # noqa: F401  (re-exported)
                      transcript_len)

class MultiTurnTrainer(LoRATrainer):
    """LoRATrainer whose items may carry whole transcripts: sft target / pair chosen / rejected = a message list (prompt is then ignored)."""

    def encode(self, prompt, target):
        if not isinstance(target, (list, dict)):  # dict = an OpenCode try (lessons.target_of: {"segs": [(text, trained?)]})
            return super().encode(prompt, target)
        ids, mask = [], []
        for text, trained in segments(target, self.tok.bos_token or ""):
            t = self.tok(text, add_special_tokens=False).input_ids
            ids += t
            mask += [1 if trained else 0] * len(t)
        return {"ids": ids, "mask": mask}


def train_night(model, tok, arm, store, seed, night, dev, use_scaler, anchors, n_steps=N_STEPS, n_sft=N_SFT, epochs=EPOCHS, n_pairs=N_PAIRS, lr=LR, log=print, dedup=False,
                max_tokens=MAX_TRAIN_TOKENS):
    """Fresh adapter on the clean base `model`. Returns (trainer or None, stats). Trainer.pm is the adapted model for the next day; call trainer.release() before the
    next night. With no lessons the adapter stays at its zero init (= the base model)."""
    items, st = build_lessons(arm, store, tok, seed, night, n_sft, epochs, n_pairs, max_tokens=max_tokens, dedup=dedup)
    if n_steps is None:  # Practice-2: scaled to the lesson count
        n_steps = steps_for(len(items))
    st["steps"] = n_steps
    trainer = MultiTurnTrainer(model, tok, seed, dev, use_scaler)
    if not items:
        st.update(skipped="no lessons")
        return trainer, st
    tr = trainer.run_night(items, anchors, n_steps, lr, night, log, dpo_w=DPO_W)
    st.update(train=tr)
    return trainer, st
