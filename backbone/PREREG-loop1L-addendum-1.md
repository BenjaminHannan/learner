# Loop-1L addendum 1 (2026-10-24 ~12:00Z, before any GPU run)
Budget forced cuts (the full spec was estimated at ~7.7 A100-hours against a $3 cap):
- Each run trains on 25% of train.jsonl (`--train-frac 0.25`, the same chats for every arm and seed, about 56 optimizer steps).
- M_tool is computed on the first 100 of the 200 eval chats (`--eval-n 100`). Pass-1/pass-8 lesions and the zeroed board use the first 50 (`--extra-n 50`).
- Board parameters use lr 1e-3 (LoRA stays 2e-4); `W_in` is zero-initialised, so C starts exactly equal to B.
Marks K1/K2/K3 and the "wrong if" rules are unchanged. Less training makes a null result weaker evidence: a FAIL here means
"no gain after a short fine-tune", not "looping can't help".
