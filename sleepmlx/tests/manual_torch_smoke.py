"""Manual, local MPS backend smoke: python -m sleepmlx.tests.manual_torch_smoke.

Uses a tiny random Llama and synthetic token IDs; no downloads or real data.
It does not validate LFM3, generation, export, or learning quality.
"""
import os, time, tempfile, math, signal
from types import SimpleNamespace
import torch, transformers, peft
from transformers import LlamaConfig, LlamaForCausalLM
from sleepmlx.torch_backend import TorchBackend
from sleepmlx.backend import Guards, Clock, Stop

print('torch', torch.__version__, 'transformers', transformers.__version__, 'peft', peft.__version__, 'mps', torch.backends.mps.is_available(), flush=True)
t0 = time.monotonic()
torch.manual_seed(1)
model = LlamaForCausalLM(LlamaConfig(vocab_size=128, hidden_size=32, intermediate_size=64, num_hidden_layers=2, num_attention_heads=4, num_key_value_heads=2, max_position_embeddings=64)).to(device='mps', dtype=torch.float16)
tok = SimpleNamespace(eos_token_id=2, pad_token_id=0, padding_side='left')
prof = SimpleNamespace(runtime={'mps_mem_gb': 1}, lora={'rank':2, 'scale':1.0, 'dropout':0.0, 'target_modules':['q_proj','k_proj','v_proj','o_proj']}, stop_token='')
be = TorchBackend(model, tok, prof, 'tiny-local-llama', tok_budget=64, grad_ckpt=False)
be.train_begin(3, 0.01)
before = [p.detach().clone() for p in be.params]
metrics = be.train_step([([1,4,5,6,7,2], 2)], [([1,8,9,10,2], 1)], 0)
assert all(math.isfinite(x) for x in metrics.values()), metrics
assert any(not torch.equal(a, b) for a,b in zip(before, be.params)), 'parameters did not change'
metrics2 = be.train_step([([1,4,5,6,7,2], 2)], [([1,8,9,10,2], 1)], 1)
assert all(math.isfinite(x) for x in metrics2.values()) and metrics2['kl'] > 0, metrics2
print('second step', metrics2, flush=True)
with tempfile.TemporaryDirectory(prefix='premonition-adapter-') as tmp:
    path = os.path.join(tmp, 'adapter')
    be.save_adapter(path)
    saved = [p.detach().clone() for p in be.params]
    with torch.no_grad():
        for p in be.params: p.zero_()
    be.load_adapter(path)
    assert all(torch.allclose(a,b) for a,b in zip(saved,be.params)), 'reload did not restore adapter'
    print('adapter files', sorted(os.listdir(path)), flush=True)
print('device', be.device, 'metrics', metrics, 'changed', True, 'save_reload', True, 'elapsed_s', round(time.monotonic()-t0,3), flush=True)
guards = Guards(pressure=lambda: 1)
clock = Clock(60, guards, reserve_s=0)
previous = signal.getsignal(signal.SIGTERM)
try:
    signal.signal(signal.SIGTERM, lambda signum, frame: guards.signal('sigterm'))
    os.kill(os.getpid(), signal.SIGTERM)
    try:
        clock.check()
        raise AssertionError('SIGTERM was not observed')
    except Stop as exc:
        assert exc.reason == 'sigterm' and exc.external
finally:
    signal.signal(signal.SIGTERM, previous)
print('SIGTERM guard and clock: passed', flush=True)
