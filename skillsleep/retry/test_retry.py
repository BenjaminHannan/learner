import importlib.util, sys, types
sys.modules.setdefault("litellm", types.ModuleType("litellm"))
spec = importlib.util.spec_from_file_location("sc", __file__.replace("test_retry.py", "sitecustomize.py")); sc = importlib.util.module_from_spec(spec); spec.loader.exec_module(sc)
class RL(Exception): status_code = 429
n = {"c": 0}; slept = []
def flaky(model, **k):
    n["c"] += 1
    if n["c"] < 4: raise RL("x")
    return "ok"
f = sc.with_retry(flaky, sleep=slept.append, rnd=lambda: 0.5)
assert f(model="anthropic/claude-haiku-5-5") == "ok" and n["c"] == 4 and len(slept) >= 3
n["c"] = 0
try: sc.with_retry(flaky, sleep=slept.append)(model="openai/m"); assert 0
except RL: assert n["c"] == 1  # local model: passes through
def bad(model, **k): raise ValueError("auth")
try: sc.with_retry(bad, sleep=slept.append)(model="anthropic/x"); assert 0
except ValueError: pass
print("retry tests ok")
