"""python -m sleepmlx  <command>

  recall "question" [--profile P] [--server URL]
                       base + adapter, answers in one short line (no-think, max 64 tokens). For the Desk's recall tool.
                       --server: ask a running llama-server (started with --lora adapter.gguf) instead of loading the model here;
                       if the server is unreachable, falls back to loading the model with the torch / MLX backend.
  status               what has been slept, what is waiting, the adapter, any night in progress (JSON).
  night [...]          run one chunk by hand (same as python -m sleepmlx.worker; --budget-s 1200 --dry-run ...).
  export-gguf --llama-cpp DIR --base HF_BASE_DIR [--out adapter.gguf]
                       torch backend only: convert the PEFT adapter to a llama.cpp GGUF LoRA (run llama-server with --lora adapter.gguf).
  diary [--date D]     preview the converted diary (what a night would read), secrets already redacted.
"""
from __future__ import annotations

import json
import os
import sys

from . import diary as diary_mod
from .paths import Paths, read_json
from .profile import Renderer, load_profile

RECALL_SYS = "Answer in one short line."


def clean_answer(text: str, prof=None) -> str:
    t = text or ""
    if prof is not None and prof.think_close and prof.think_close in t:
        after = t.split(prof.think_close)[-1].strip()
        t = after if after else t.split(prof.think_close)[0]
    for s in (prof.stop_token if prof else "",):
        if s:
            t = t.split(s)[0]
    lines = [x.strip() for x in t.strip().splitlines() if x.strip()]
    return lines[0] if lines else ""


def recall(question: str, backend, R, prof, adapter_dir=None) -> str:
    """One short line. The adapter (if any) is loaded; no-think prompt; max 64 tokens; greedy."""
    if adapter_dir is not None and os.path.exists(str(adapter_dir)):
        backend.load_adapter(adapter_dir)
    out = backend.generate([R.render(RECALL_SYS, question)], 64, 0.0, True)[0]
    return clean_answer(out, prof)


def recall_server(url: str, question: str, prof, timeout: float = 60.0) -> str:
    """Ask a llama-server (llama.cpp) through its /completion endpoint with the profile's no-think prompt. Raises OSError / ValueError on failure."""
    import urllib.request
    p = load_profile_manual(prof)
    body = json.dumps({"prompt": Renderer(p, None).render(RECALL_SYS, question), "n_predict": 64, "temperature": 0.0, "stop": [prof.stop_token] if prof.stop_token else [],
                       "cache_prompt": True}).encode()
    req = urllib.request.Request(url.rstrip("/") + "/completion", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read().decode())
    return clean_answer(data.get("content", ""), prof)


def load_profile_manual(prof):
    """A copy of the profile that renders with its own template strings (the server tokenizes; we do not load a tokenizer for that)."""
    import copy
    p = copy.copy(prof)
    p.template_mode = "manual"
    return p


def status(paths: Paths, prof) -> dict:
    st = read_json(paths.state, {}) or {}
    week = diary_mod.build_week(paths.diary_dir, ignore_file=paths.ignore)
    from .recipe import next_day
    nxt = next_day(week, st)
    night = read_json(paths.night_json, None)
    cards = 0
    if paths.cards.exists():
        cards = sum(1 for _ in paths.cards.read_text().splitlines())
    last = None
    if paths.nights.exists():
        lines = [l for l in paths.nights.read_text().splitlines() if l.strip()]
        last = json.loads(lines[-1]) if lines else None
    return {"profile": prof.name, "model_dir": prof.expanded_model_dir, "home": str(paths.home),
            "diary_days": week.get("dates", {}), "slept_days": st.get("slept_days", []), "nights": st.get("nights", 0),
            "next_day": nxt[1] if nxt else None, "night_in_progress": ({k: night.get(k) for k in ("date", "phase", "done_steps", "total_steps", "scale", "chunks")} if night else None),
            "adapter": paths.adapter.exists(), "adapter_prev": paths.adapter_prev.exists(), "cards": cards, "last_night": last,
            "last_state": st.get("last_night")}


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, rest = argv[0], argv[1:]
    paths = Paths.from_env()
    if cmd == "status":
        prof = load_profile(os.environ.get("SLEEPMLX_PROFILE"))
        print(json.dumps(status(paths, prof), indent=1))
        return 0
    if cmd == "recall":
        def take(flag):
            if flag in rest:
                i = rest.index(flag)
                v = rest[i + 1]
                del rest[i:i + 2]
                return v
            return None
        prof_name, server = take("--profile"), take("--server")
        q = " ".join(rest).strip()
        if not q:
            print("usage: python -m sleepmlx recall \"question\" [--profile P] [--server URL]", file=sys.stderr)
            return 2
        prof = load_profile(prof_name)
        if server:
            try:
                print(recall_server(server, q, prof))
                return 0
            except (OSError, ValueError) as e:
                print("llama-server at %s did not answer (%s); loading the model here instead (slow)" % (server, e), file=sys.stderr)
        from .worker import make_backend
        be, tok = make_backend(prof)
        print(recall(q, be, Renderer(prof, tok), prof, paths.adapter if paths.adapter.exists() else None))
        return 0
    if cmd == "night":
        from .worker import main as wmain
        return wmain(rest)
    if cmd == "export-gguf":
        import subprocess
        def opt(name, default=None):
            return rest[rest.index(name) + 1] if name in rest else default
        llama, base = opt("--llama-cpp"), opt("--base")
        out = opt("--out", str(paths.home / "adapter.gguf"))
        if not llama or not base:
            print("usage: export-gguf --llama-cpp DIR --base HF_BASE_DIR [--out FILE]", file=sys.stderr)
            return 2
        from .export import export_command
        cmd_ = export_command(llama, base, paths.adapter, out)
        print(" ".join(cmd_))
        return subprocess.call(cmd_)
    if cmd == "diary":
        date = rest[rest.index("--date") + 1] if "--date" in rest else None
        week = diary_mod.build_week(paths.diary_dir, dates=[date] if date else None, ignore_file=diary_mod.ensure_ignore(paths.ignore))
        print(json.dumps({"dates": week["dates"], "turns": len([t for t in week["diary"] if t["role"] == "user"])}))
        for t in week["diary"]:
            print("[day %s %s] %s" % (t["day"], t["role"], t["text"][:300].replace("\n", " ")))
        return 0
    print("unknown command %r\n%s" % (cmd, __doc__), file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
