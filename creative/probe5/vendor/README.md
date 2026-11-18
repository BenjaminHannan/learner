# Vendored LFM3 model code

Why: the Mac must not fetch and run remote code (`trust_remote_code=True`). The model classes are loaded from these files instead, with local weights.

Source: https://huggingface.co/LiquidAI/LFM3-1.7B at revision

    40ebe0aa6662c9d40389c2f5d565b6a2c6aebacd      (lastModified 2026-10-27T05:58:29Z)

Downloaded on 2026-10-27 from `https://huggingface.co/LiquidAI/LFM3-1.7B/resolve/<revision>/<file>`. Files are byte-for-byte as served (LFM Open License v1.0, see LICENSE).

| file | sha256 |
|---|---|
| modeling_lfm3.py | e8cd5254ea99ce6bd731b57b10908c2e8b5010ce8315341f895a38484885eeab |
| lfm3_conv.py | 80d4a985382a22774212759248a6b4c737bfbf9c2a47b3dd7f797dda748e4bb4 |
| configuration_lfm3.py | 176cced35657aedfea7d7002221360582d1c05fcaca882c21508bc3a73b282e5 |
| config.json | 8c6ae8b8f6d88c87cfb98cf4b5e34e943d0ee07e24215c4121b3159a46e1399d |
| generation_config.json | 0095ba7158e938b1e2d3082d412f00d8be85e42cbbd7608b63866f7a081cf270 |
| LICENSE | 4d28ca14dedc0b3d0fcc2b3339f0e79931faa33874f3d24f522183a8fc70068c |

`__init__.py` (one docstring line) is ours; it makes the folder a package, because `modeling_lfm3.py` uses relative imports (`from .configuration_lfm3 import ...`, `from .lfm3_conv import ...`).
`lfm3_conv.py` has an optional Triton kernel (CUDA only, inference only); on the Mac the plain torch convolution runs.

Use: `lfm3_load.load_model(<local HF dir>, dtype)` imports `Lfm3ForCausalLM` from here and calls `from_pretrained(<local dir>)`. The weights (model.safetensors) and tokenizer files come from the
local HF snapshot (`huggingface-cli download LiquidAI/LFM3-1.7B --revision 40ebe0aa6662c9d40389c2f5d565b6a2c6aebacd --local-dir ...`; run_m3.sh does this). `lfm3_load.check_hashes()` compares these files with the table above.
To update: re-download at a new revision, replace the files, update this table and `PINNED_REVISION` in `lfm3_load.py`, rerun the tests.
