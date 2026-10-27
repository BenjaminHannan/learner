#!/usr/bin/env python3
"""0.2c sleep inside the joined agent (month-end line, 2026-09-26; Ben's 01:45 UTC goal). New file only.

What: Fix sleep's copy-practice night (dl-1/dl-2 arm S: claude_dl1_nights.gather + copy_examples + train_copy,
unchanged) trained on the joined agent's OWN shared MiniCPM5-1B, the model every 1B layer of the agent calls
(claude_e2e330_arms._GEN[gen_model], a Gen333b; Gen338 shares it). The adapter is claude_blurt2.add_lora, added in
place; its B matrices start at zero, so the agent is unchanged until a night trains it.
  day    the agent practises fresh number puzzles in downtime (bored mode): one greedy answer + N_GUESS guesses at
         T 1.5 per puzzle, every guess marked by the exact checker (claude_blurt1.check).
  night  copy practice on the day's checked right answers (greedy right + first lucky hit on a miss), 3 epochs,
         lr 2e-4, one adapter that keeps growing. Nothing is written to the notebook or the memory store.
Measured before and after every night (never trained on): TEST = fresh puzzles (another seed, none seen in a day)
x 20 guesses: right guesses ("lucky"), puzzles reached, greedy solves; HARM = dl-1's 300 general items as flips
against the pre-sleep agent; KL to the pre-sleep model; CHAT = fresh puzzles asked in plain English through the
agent's turn loop, solved if an expression in the reply uses each number once and hits the target.

  python -B scripts/claude_twinb_wrap.py scripts/claude_sleep02c.py --arm claude_e2e02c:build_02c \
      --model READER --gen-model BASE --out OUT [--nights 3 --n-day 150 --n-test 100 --n-chat 40]
writes OUT/sleep02c_results.json and OUT/adapter02c.pt (the LoRA weights only). A later process gets the slept
agent with SLEEP02C_ADAPTER=OUT/adapter02c.pt and install_sleep02c(one_b) (every builder of 0.2c calls it).
  python -B scripts/claude_sleep02c.py --selftest       (no model)
Every saved night has a sidecar OUT/adapter02c.json (Fix sleep, 02:19 UTC 09-26): the base model's fingerprint, the
sha256 of this code and of the adapter file, and the night's greedy answers on CHECK02C fixed day puzzles. A saved
adapter loads only when its sidecar exists, its sha256 matches the file, and the base fingerprint matches the model.
  python -B scripts/claude_sleep02c.py --check-activation OUT/adapter02c.pt --gen-model BASE   (report only)
in a fresh process: greedy answers on the CHECK02C puzzles with the adapter (must equal the saved night's) and with
every LoRA scale set to 0 (must differ on at least 1). One JSON line.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import random
import sys
import tempfile
import time
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

N_GUESS = 30
N_GUESS_TEST = 20
DAY_SEED02C = 4700          # night d uses puzzles(DAY_SEED02C + d); never used by dl-1 (3900+), dl-2 or blurt runs
TEST_SEED02C = 4790
CHAT_SEED02C = 4795
CHECK02C = 10                # activation check: the first 10 puzzles of night 1's day
CHAT_ASK = ("Can you solve this number puzzle? Use each of the numbers {nums} exactly once, with + - * / and "
            "brackets, to make {target}. Give the expression.")


def lora_mods(model):
    return [x for x in model.modules() if hasattr(x, "A") and hasattr(x, "B") and hasattr(x, "scale")]


def _sha256(path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def base_fingerprint(model) -> str:
    """The base model's identity without its path: count of base (non-LoRA) parameters plus a hash of the first
    base tensor's first 256 rows, read as float32."""
    import hashlib
    base = [(n, t) for n, t in model.named_parameters() if not (n.endswith(".A") or n.endswith(".B"))]
    first = base[0][1].detach()[:256].float().cpu().contiguous()
    h = hashlib.sha256(first.numpy().tobytes()).hexdigest()[:16]
    return f"{sum(t.numel() for _, t in base)}:{h}"


def code_hash() -> str:
    return _sha256(Path(__file__).resolve())[:16]


def sidecar_path(path) -> Path:
    return Path(path).with_suffix(".json")


def check_puzzles():
    import claude_blurt2 as B2
    return B2.puzzles(DAY_SEED02C + 1, CHECK02C)


def check_sidecar(model, path) -> dict:
    sc = sidecar_path(path)
    if not sc.exists():
        raise RuntimeError(f"sleep02c: {path} has no sidecar {sc.name}; refusing to load")
    meta = json.loads(sc.read_text(encoding="utf-8"))
    if meta.get("adapter_sha256") != _sha256(path):
        raise RuntimeError("sleep02c: adapter file does not match its sidecar (torn save?); refusing to load")
    if meta.get("base") != base_fingerprint(model):
        raise RuntimeError("sleep02c: adapter was trained on a different base model; refusing to load")
    return meta


def install_sleep02c(one_b, path: str | None = None) -> None:
    """Add the LoRA adapter to the shared 1B once (identity until trained); load saved weights if a path is given
    (default: env SLEEP02C_ADAPTER)."""
    import claude_blurt2 as B2
    if not getattr(one_b, "sleep02c", False):
        B2.add_lora(one_b.model).eval()
        one_b.sleep02c = True
    path = path if path is not None else os.environ.get("SLEEP02C_ADAPTER", "")
    if path and getattr(one_b, "sleep02c_trained", False):
        raise RuntimeError("sleep02c: refusing to load a saved adapter over weights a night trained in this process")
    if path:
        import torch
        check_sidecar(one_b.model, path)
        state = torch.load(path, map_location="cpu")
        mods = lora_mods(one_b.model)
        if len(state) != len(mods):
            raise RuntimeError(f"sleep02c: adapter has {len(state)} layers, model has {len(mods)}")
        for m, (a, b) in zip(mods, state):
            m.A.data.copy_(a.to(m.A.device))
            m.B.data.copy_(b.to(m.B.device))
        one_b.sleep02c_loaded = path


def save_adapter(one_b, path) -> None:
    import torch
    torch.save([(m.A.detach().cpu(), m.B.detach().cpu()) for m in lora_mods(one_b.model)], path)


def lora_vector(one_b):
    import torch
    return torch.cat([t.detach().float().flatten().cpu() for m in lora_mods(one_b.model) for t in (m.A, m.B)])


def reload_matches(one_b, path) -> bool:
    """The saved night, loaded again, equals the weights in memory (active after a reload)."""
    import torch
    state = torch.load(path, map_location="cpu")
    return all(torch.equal(a, m.A.detach().cpu()) and torch.equal(b, m.B.detach().cpu())
               for m, (a, b) in zip(lora_mods(one_b.model), state)) and len(state) == len(lora_mods(one_b.model))


def solver_shim(one_b):
    """claude_blurt2.Solver's prompt/generate/answer on the agent's own tokenizer and model (no second load)."""
    import claude_blurt2 as B2
    s = B2.Solver.__new__(B2.Solver)
    s.torch, s.tok, s.dev, s.model = one_b.torch, one_b.tok, one_b.dev, one_b.model
    return s


def chat_solved(agent, puzzles) -> list[int]:
    import claude_panel382_run as P
    out = []
    for p in puzzles:
        nums = ", ".join(str(n) for n in p["nums"][:-1]) + " and " + str(p["nums"][-1])
        parts = agent.turn(CHAT_ASK.format(nums=nums, target=p["target"]))
        reply = " ".join(x for x in (parts or []) if x)
        out.append(int(P.puzzle_solved(reply, p["nums"], p["target"])))
    return out


def run(a) -> None:
    import claude_blurt1 as B1
    import claude_blurt2 as B2
    import claude_dl1_nights as D1
    import claude_e2e330_arms as A
    os.environ.pop("SLEEP02C_ADAPTER", None)       # the nights train here; a saved file must never be reloaded over them
    t0 = time.time()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    mod, fn = a.arm.split(":")
    build = getattr(importlib.import_module(mod), fn)

    def agent():
        return build(tempfile.mkdtemp(prefix="s02c-"), a)

    ag = agent()
    one_b = A._GEN[a.gen_model]
    install_sleep02c(one_b, "")
    s = solver_shim(one_b)
    m = one_b.model
    fingerprint = base_fingerprint(m)
    day_keys = {(tuple(p["nums"]), p["target"]) for d in range(1, a.nights + 1)
                for p in B2.puzzles(DAY_SEED02C + d, a.n_day)}
    test = [p for p in B2.puzzles(TEST_SEED02C, a.n_test + 300)
            if (tuple(p["nums"]), p["target"]) not in day_keys][:a.n_test]
    tkeys = day_keys | {(tuple(p["nums"]), p["target"]) for p in test}
    chat = [p for p in B2.puzzles(CHAT_SEED02C, a.n_chat + 300)
            if (tuple(p["nums"]), p["target"]) not in tkeys][:a.n_chat]
    panel = D1.harm_panel()
    replies = [(q, D1.free_answer(s, q, m, 40)) for q in (D1.CHAT_PROMPTS + [it["q"] for it in panel[::5]])[:60]]
    res = {"config": {k: v for k, v in vars(a).items() if k not in ("model", "gen_model")}, "n_test": len(test),
           "n_chat": len(chat), "n_harm": len(panel), "temp": D1.TEMP, "day_seed": DAY_SEED02C,
           "test_seed": TEST_SEED02C, "chat_seed": CHAT_SEED02C, "base_fingerprint": fingerprint,
           "code": code_hash(), "layers": getattr(ag, "layers330c", None)}
    b = D1.measure(s, m, test, N_GUESS_TEST, panel)
    res["base"] = {"lucky": b["lucky"], "reached": b["reached"], "greedy": b["greedy"], "harm_right": sum(b["harm"]),
                   "chat_solved": sum(chat_solved(agent(), chat))}
    print(f"[sleep02c] before: {res['base']}", flush=True)
    res["nights"] = []
    for d in range(1, a.nights + 1):
        t1 = time.time()
        day = B2.puzzles(DAY_SEED02C + d, a.n_day)
        groups = D1.gather(s, m, day, N_GUESS)
        ex = D1.copy_examples(groups)
        tries = sum(1 + len(g["guesses"]) for g in groups)
        w0 = lora_vector(one_b)
        tr = D1.train_copy(s, m, ex, seed=d)
        change = float((lora_vector(one_b) - w0).norm())
        one_b.sleep02c_trained = True
        if m.training:
            raise RuntimeError("sleep02c: model left in train mode after the night")
        now = D1.measure(s, m, test, N_GUESS_TEST, panel, replies)
        row = {"night": d, "tries": tries, "day_puzzles": len(day),
               "day_greedy_right": sum(g["greedy_right"] for g in groups),
               "day_reached": sum(1 for g in groups if g["greedy_right"] or any(g["rewards"])),
               "train": tr, "eligible_examples": len(ex), "optimizer_steps": 3 * -(-len(ex) // 8),
               "weight_change_l2": round(change, 6), "test": {k: now[k] for k in ("lucky", "reached", "greedy")},
               "harm": D1.flips(b["harm"], now["harm"]), "kl": now["kl"],
               "chat_solved": sum(chat_solved(agent(), chat)), "minutes": round((time.time() - t1) / 60, 1)}
        tmp = out / "adapter02c.tmp"
        save_adapter(one_b, tmp)
        meta = {"night": d, "base": fingerprint, "code": code_hash(), "adapter_sha256": _sha256(tmp),
                "check_answers": [s.answer(p, m) for p in check_puzzles()]}
        (out / "adapter02c.json.tmp").write_text(json.dumps(meta), encoding="utf-8")
        os.replace(out / "adapter02c.json.tmp", out / "adapter02c.json")
        os.replace(tmp, out / "adapter02c.pt")          # candidate -> active in one step (sidecar sha256 guards the pair)
        row["adapter_saved"] = (out / "adapter02c.pt").exists()
        row["adapter_sha256"] = meta["adapter_sha256"]
        row["check_greedy_right"] = sum(int(B1.check(g, p["nums"], p["target"]))
                                        for g, p in zip(meta["check_answers"], check_puzzles()))
        row["active_after_reload"] = reload_matches(one_b, out / "adapter02c.pt")
        res["nights"].append(row)
        print(f"[sleep02c] night {d}: {json.dumps(row)}", flush=True)
        (out / "sleep02c_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    res["minutes"] = round((time.time() - t0) / 60, 1)
    (out / "sleep02c_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({"base": res["base"], "last": res["nights"][-1] if res["nights"] else None}))


def check_activation(a) -> None:
    """Report only, fresh process: the saved night is what runs, and turning it off changes behaviour."""
    import claude_cre333b_agent as C333B
    one_b = C333B.Gen333b(a.gen_model)
    install_sleep02c(one_b, a.check_activation)
    meta = json.loads(sidecar_path(a.check_activation).read_text(encoding="utf-8"))
    s = solver_shim(one_b)
    m = one_b.model.eval()
    ps = check_puzzles()
    on = [s.answer(p, m) for p in ps]
    mods = lora_mods(m)
    scales = [x.scale for x in mods]
    for x in mods:
        x.scale = 0.0
    off = [s.answer(p, m) for p in ps]
    for x, sc in zip(mods, scales):
        x.scale = sc
    again = [s.answer(p, m) for p in ps]
    same_saved = sum(int(x == y) for x, y in zip(on, meta["check_answers"]))
    differ_off = sum(int(x != y) for x, y in zip(on, off))
    print(json.dumps({"check_activation": {"night": meta.get("night"), "puzzles": len(ps),
                      "on_equals_saved": same_saved, "on_differs_from_off": differ_off,
                      "on_again_equals_on": sum(int(x == y) for x, y in zip(on, again)),
                      "pass": same_saved == len(ps) and differ_off >= 1}}), flush=True)


def selftest() -> None:
    import torch
    import claude_blurt2 as B2

    class Tiny(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.q_proj = torch.nn.Linear(4, 4)

        def forward(self, x):
            return self.q_proj(x)

    class OneB:
        pass

    ok = 0
    ob = OneB()
    ob.model = Tiny()
    x = torch.randn(2, 4)
    y0 = ob.model(x).detach().clone()
    install_sleep02c(ob, "")
    assert torch.allclose(ob.model(x), y0); ok += 1                        # identity until trained
    install_sleep02c(ob, "")
    assert len(lora_mods(ob.model)) == 1; ok += 1                          # added once only
    for mm in lora_mods(ob.model):
        mm.B.data.fill_(0.1)
    y1 = ob.model(x).detach().clone()
    assert not torch.allclose(y1, y0); ok += 1
    def save_with_sidecar(o, pth):
        save_adapter(o, pth)
        sidecar_path(pth).write_text(json.dumps({"base": base_fingerprint(o.model), "adapter_sha256": _sha256(pth)}))

    with tempfile.TemporaryDirectory() as d:
        save_with_sidecar(ob, Path(d) / "a.pt")
        ob2 = OneB()
        ob2.model = Tiny()
        ob2.model.load_state_dict({"q_proj.weight": ob.model.q_proj.base.weight, "q_proj.bias": ob.model.q_proj.base.bias})
        install_sleep02c(ob2, str(Path(d) / "a.pt"))
        ob2.model.eval()
        ob.model.eval()
        assert torch.allclose(ob2.model(x), ob.model(x)); ok += 1         # a saved night reloads exactly
        assert reload_matches(ob, Path(d) / "a.pt") and reload_matches(ob2, Path(d) / "a.pt"); ok += 1
        ob3 = OneB()
        ob3.model = Tiny()                                                 # another base (fresh random weights)
        try:
            install_sleep02c(ob3, str(Path(d) / "a.pt"))
        except RuntimeError as e:
            ok += "different base" in str(e)                               # refuses another base model
        ob4 = OneB()
        ob4.model = Tiny()
        ob4.model.load_state_dict({"q_proj.weight": ob.model.q_proj.base.weight, "q_proj.bias": ob.model.q_proj.base.bias})
        with open(Path(d) / "a.pt", "ab") as f:
            f.write(b"x")
        try:
            install_sleep02c(ob4, str(Path(d) / "a.pt"))
        except RuntimeError as e:
            ok += "torn" in str(e)                                         # refuses a file that is not the sidecar's
    assert len({(tuple(p["nums"]), p["target"]) for p in B2.puzzles(DAY_SEED02C + 1, 20)}) == 20; ok += 1
    ob.sleep02c_trained = True
    with tempfile.TemporaryDirectory() as d:
        save_with_sidecar(ob, Path(d) / "b.pt")
        try:
            install_sleep02c(ob, str(Path(d) / "b.pt"))
        except RuntimeError:
            ok += 1                                                        # never reloads over trained weights
    print(f"claude_sleep02c selftest: {ok}/9 OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="claude_e2e02c:build_02c")
    ap.add_argument("--model", default="", help="reader dir")
    ap.add_argument("--gen-model", default="", help="base MiniCPM5-1B dir")
    ap.add_argument("--mouth-model", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--nights", type=int, default=3)
    ap.add_argument("--n-day", type=int, default=150)
    ap.add_argument("--n-test", type=int, default=100)
    ap.add_argument("--n-chat", type=int, default=40)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--check-activation", default="", help="a saved adapter02c.pt (report only)")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    if a.check_activation:
        if not a.gen_model:
            raise SystemExit("sleep02c: --check-activation needs --gen-model")
        check_activation(a)
        return
    if not (a.out and a.gen_model):
        raise SystemExit("sleep02c: --out and --gen-model are required")
    run(a)


if __name__ == "__main__":
    main()
