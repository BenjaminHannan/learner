# rsn-294 speed fix (before any registered run)

rsn-294-train (builder, 20:50 UTC) stopped at the pilot with TOO-SLOW: the practice phase took
about 2.3 s per step on a whole 5090 (full plan ≈ 16 GPU-hours). No model was trained, no panel
item was read, $0.40 spent. Cause: the practice scorer read each of the 8 × 128 tries from the GPU
one element at a time. Fix: in rl_loss, the tries and the "cited facts exactly right" test are
moved to the CPU in one go, then scored in Python (scoring now ≈ 1 ms per step on CPU).
Nothing else changed: the same reward, maths, steps, sizes, seeds and marks. PASSMARKS.md stands
as sealed. SEAL-code-v2.sha256.txt replaces SEAL-code.sha256.txt for the code files.
