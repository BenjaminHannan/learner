# TTT for ARC: what others found (Haiku search sweep, 2026-10-25 ~22:35Z; mostly snippets, verify before citing)

- Akyurek et al. 2024 (arXiv 2411.07279). Shown: Llama-3 8B / 3.2 1B-3B, all first fine-tuned on ReARC. FT-only 5 -> FT+TTT 29 on 80 dev tasks; 39.3 -> 47.1 on full validation. LoRA r128, lr 5e-5 to 1e-4, 2 epochs, up to 250 examples per task, leave-one-out. Augmentations: geometric, color, order. Hierarchical voting over invertible transforms. No ablation without the ARC fine-tune.
- ARC Prize 2024/2025. Shown: TTT plus augmentation underpins the top scores. ARChitects (per a replication): per-task LoRA r64, augmentation-stability answer selection. ARC-AGI-2 private 2025: NVARC 24.0, ARChitects 16.5, MindsAI 12.6.
- No-pretraining: CompressARC (76K params, per-puzzle training from scratch) 20% on ARC-AGI-1 (sources disagree, 20-34). No number found for a general 1-8B chat model with TTT and no ARC training.
- Cheap upgrades (untested for us): voting over the 8 symmetries at inference, color-permutation augmentation, 2-4 passes.
