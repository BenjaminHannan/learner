# V1 FULL weights (v1full-pc re-run, 2026-10-23)

Read-only copies of the V1 FULL arm's final weights. They come from the $0 re-run on BensPC (RTX 5070 Ti, WSL2) of `python -m v1.run --arm full`, 12,000 steps.

- Code commit: `71a6919e04e62a734105844cb5f4d438364b8d9f` (this branch is based on it; nothing else in the repo is changed)
- `D-final.pt` sha256 `bc8ea994c0a05a3b9eae401e1d84778ffa62d0cd9fd44e73a09a112f78304fb3` (main brain D d128 + bridge state, key `bridge`)
- `creative/W2.pt` sha256 `4310043e92881891ebf634453009ee3115e68b734d3d20f3a0fbd7321f0ea95d` (creative module d256 after W2 sleep)
- Creative parent: B2_s200.pt (sha256 94057436..., per V1_PARAMS)

| Split | D (village) | Creative first-try |
|---|---|---|
| dev | 82.0% | 35.9% |
| validation | 46.1% | n/a |
| sealed test (read once, 17:18 ET) | 48.5% | 35.5% |

W1 and W2 both pass, so the run is marked `working = true`. See `final_dev.json`, `DECISION.json` and `SEALED_READ.json`.

Loading follows `v1/sealed_read.py`:
1. Build `PremonitionMini(mini_config_from(saved["config"]))` and `load_state_dict(saved["model"])`.
2. Attach a `Bridge(128, 256)` to D and the creative model, then `bridge.load_state_dict(saved["bridge"])` and set `frozen_ctx=True`.
3. Load W2.pt with `creative.sleep.load_parent`, then `bridge.attach_creative(m)`.
