# bridgelab/real : count handoff on the real models (D village reader -> creative Ledger B2)

Does a per-question bridge carry question-specific information? An item is a village visit ending in a Q5 count question (answer c) plus a creative rule prompt with the
query number hidden (`Examples: 4 -> 20; 5 -> 24; 16 -> 68. Now @ -> ?`, target f(c)). The creative model cannot know c; D can. Pass marks: `PREREG.md` (fixed before any scored run).
This directory is separate from the small card experiments in `bridgelab/` (task.py, models.py, ...).

| file | what |
|---|---|
| `data.py` | village items (Q5 `q.count_at` / `q.count_held`, knowable, number-word answer), c statistics + prior baseline, creative prompt generator (`creative/rules_real` rules, teacher-forced reference programs), smoke data root |
| `dmsg.py` | load frozen D (`D-final.pt` / `random`), read each item's visit, keep D's register rows at the final think loop `[4,128]`, register 0, D's decoded answer + correctness; `python -m bridgelab.real.dmsg` = smoke-only D pretrain on counts |
| `bridge.py` | `D2C` (none / ema_const / pooled / xattn), the count head (CE on true c), `SlotLedger` (injects the count as the value of the query slot `@`), `Wire`, ablations (`real/off/shuffle/mean`) |
| `train.py` | train one bridge type, score every arm + ablation + probes, write `results/<bridge>-s<seed>.json` |
| `verdict.py` | apply PREREG pass marks to the JSONs |
| `tests/` | `pytest bridgelab/real/tests` (CPU, ~2 min) |

Only edit outside this directory: `custom_io/models/ledger.py` accepts a per-item `bridge_in` vector of shape `[B, d]` (1-D `[d]` behaves exactly as before; tested).

## Mechanism (shown, in code)
* D is frozen; its messages are computed once per item (identity entity numbering) and cached in `ckpt/dmsg-*.pt`. No gradient reaches D.
* `pooled`: RMSNorm(reg0) -> Linear(zero-init) = v, added to the creative controller tokens Z once before iteration 0. `xattn`: after every controller block Z += tanh(gate) * CrossAttn(Z, Linear(RMSNorm(regs))), gate = 0. `ema_const`: `v1/joint.py` Bridge (EMA of reg0, same vector for every question). `none`: no message.
* Number handoff (all types): count head (MLP on the summary) predicts c in 0..20, CE on the TRUE c (**auxiliary label**), argmax is written as the VALUE of the query slot; the slot's embedding = usual value code + v. The executor computes with that exact integer. While training the creative loss the slot holds the true c (`--inject-train pred` to use the head's guess), so the program/pointer loss is the C2 warm-up loss.
* Zero-init => creative outputs are bit-identical to bridge-off with the slot value fixed (`tests/test_bridge.py`).

## Checkpoints
* Creative: `--c-ckpt` any `sleep.save_parent` file. Raw parent used for the smoke: `claude/b2-confirm-checkpoints:custom_io/checkpoints/33-b2-confirm/B2_s200/checkpoint.pt` (copied to `ckpt/B2_s200.pt`; not committed). It solves add 12% / mult 34% of C2 warm prompts first try, so for the smoke the creative is first adapted with the `text` arm (`--save-creative`). For the full run use `W2.pt` (then the creative needs little adaptation).
* D: `--d-ckpt` = the v1 `D-final.pt` (`{"model", "config": MiniConfig dict}`) when it arrives. No trained D existed in the repo / remote branches when this was built; the smoke used `random` or a D pretrained a few hundred CPU steps on count questions only (`ckpt/D_smoke_150.pt`). `--d-ckpt synthetic` (smoke only) fabricates messages that carry c (registers = A[c] + noise, D's answer right 85%) to prove the arms/ablations can show flow; it says nothing about D.

## Commands
Data (once; the v1 layout ROOT/{train,dev,validation}; train = shards 0-379, dev = 380-399): `python v1/build_data.py BUILD 8 && python v1/split_dirs.py BUILD ROOT`
(`ROOT` must also hold `premonition-names.json`/caches from v1 training so D's pointer numbering matches; `v1.dtrain.open_data` builds them if absent.)

```bash
R=ROOT D=D-final.pt C=W2.pt OUT=bridgelab/real/results
# 0. unit tests
pytest bridgelab/real/tests
# 1. text arms: creative on typed true c; scores oracle_text, d_text, prior_text.  Also makes D's messages (cached for the arms below)
python -m bridgelab.real.train --bridge text      --d-ckpt $D --c-ckpt $C --village-root $R --steps 1500 --device cuda --seed 0 --out $OUT --save-creative bridgelab/real/ckpt/creative_text.pt
# 2. controls and per-item bridges, 3 seeds
for s in 0 1 2; do for b in none ema_const pooled xattn; do
  python -m bridgelab.real.train --bridge $b --d-ckpt $D --c-ckpt $C --village-root $R --steps 4000 --device cuda --seed $s --out $OUT
done; done
# optional: frozen creative (bridge only):  add --freeze-creative --tag frozen
python -m bridgelab.real.verdict $OUT
```
Useful flags: `--train-items N` / `--eval-items N` (caps), `--batch 64`, `--lr-bridge 1e-3`, `--lr-creative 3e-4`, `--kinds add,mult` (add `last_digit,square` for a second run with its own tag; those kinds are NOT taught-with-labels in C2, here they are taught by the reference programs), `--d-max-tokens` (D reading batch size; 60000 tokens fits a 16 GB card), `--bf16`.

## Time estimate for the full GPU run (suggested, untested on a GPU; from CPU timings x a guess)
* D reading: ~0.6 count items per visit, ~1.1k tokens per visit in the smoke data; reading up to 57k train items = up to 95k visits. Estimate 5-15 min once on a single GPU (cached afterwards; `--train-items 20000` cuts it to ~3 min).
* Creative + bridge: CPU measures ~1.1 s per step at batch 64 (4 cores). A GPU should be ~10x faster, so 4000 steps ~ 8-10 min per arm. Eval of dev+validation (~4k items x ~8 arms): ~1 min.
* Whole grid (text + 4 bridge types x 3 seeds): ~13 runs x ~12 min ~ 2.5-3 h. One seed of everything: ~1 h.

## Reading the output
`results/<bridge>-s<seed>.json`: `prior` (c distribution, entropy, prior baseline per split), `results.{dev,validation}.{d_own, arms}` (first-try exact accuracy, `count_acc`, `acc_given_count_right`, per-kind), `probes` (linear probe train->dev on `v`, `h`, raw `reg0`, all registers; chance = prior baseline), `aux_label`, `smoke` flag.
Arms: `real off shuffle mean` (ablations of the message, per-item bridges), `oracle_inject` (true c injected into this run's creative: its ceiling), `prior_inject` (prior mode injected, no bridge vectors), `oracle_text`, `d_text`.
Canonical text baselines are the `--bridge text` run (its creative was trained on typed numbers).
