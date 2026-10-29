"""The served check: does the adapter still do its job once it is a GGUF LoRA inside llama-server (Q4 base), not just in the trainer (fp16)?

One llama-server started with `--lora adapter.gguf` answers every question twice in the same process: adapter at scale 1 and at scale 0
(llama-server's per-request "lora" field), so no second server and no restart is needed. Questions: a spread of the gate's general questions
plus the latest night's held-out cards (cards.jsonl). Pass when
    * general: the adapter gets at most `max_general_loss` more wrong than the plain model, and at least half right (a broken conversion
      answers garbage), and
    * held-out: the adapter answers at least as many held-out cards as the plain model.
Grading is gate.correct / gate.recall_hit (strict).

    python -m sleepmlx served-check --server http://127.0.0.1:18090 [--n 8]     exit 0 pass, 1 fail, 2 not checked ("ok": null)
"""
from __future__ import annotations

import json
import hashlib
import os
import socket
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

from . import gate as gate_mod
from .paths import read_json, write_json


def artifact_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pending_check(paths):
    from .export import sidecar_path
    side = read_json(sidecar_path(paths.home / "adapter.gguf"), {}) or {}
    return isinstance(side, dict) and isinstance(side.get("served_pending"), dict)


def _record_finalization(paths, night_id, verdict):
    """Keep an unfinished night from replaying an obsolete pending result."""
    from .checkpoint import Checkpoints
    if not paths.night_json.exists():
        return
    checkpoints = Checkpoints(paths)
    night, items = checkpoints.load()
    if night.get("id") == night_id and night.get("finalization"):
        result = night["finalization"]["result"]
        result["served"] = verdict
        if not result.get("gguf", {}).get("ok"):
            result["gguf"] = {"ok": True, "message": str(paths.home / "adapter.gguf")}
        checkpoints.publish(night, items if items is not None else read_json(paths.items, {}) or {})


def finish_pending(paths, prof, cfg, checker=None, log=lambda message: None):
    """Finish a generation-bound check, even after night cleanup.

    Save the verdict before applying it. A recorded previous hash lets replay
    recognize an interrupted rollback without removing the restored adapter.
    """
    from . import export as export_mod
    gguf = paths.home / "adapter.gguf"
    side_path = export_mod.sidecar_path(gguf)
    side = read_json(side_path, {}) or {}
    pending = side.get("served_pending") if isinstance(side, dict) else None
    if not isinstance(pending, dict):
        return None

    def deferred(reason):
        return {"ok": None, "pending": True, "reasons": [reason]}

    if (pending.get("version") != 1 or pending.get("profile") != prof.name
            or pending.get("base_hf_id") != prof.hf_id
            or pending.get("base_gguf") != cfg.base_gguf
            or pending.get("llama_server") != cfg.llama_server):
        return deferred("not checked: pending adapter belongs to another model or server configuration")
    if (not isinstance(pending.get("night_id"), str) or not pending["night_id"]
            or not isinstance(pending.get("sha256"), str) or len(pending["sha256"]) != 64
            or not isinstance(pending.get("held"), list)):
        return deferred("not checked: invalid pending adapter descriptor")
    try:
        generation = paths.adapter.relative_to(paths.home).as_posix()
    except (RuntimeError, ValueError):
        generation = None
    if (generation != pending.get("adapter") or side.get("night_id") != pending["night_id"]
            or side.get("profile") != prof.name or side.get("base_hf_id") != prof.hf_id):
        return deferred("not checked: pending adapter identity no longer matches the current artifact")
    verdict = pending.get("verdict")
    previous = export_mod.prev_path(gguf)
    current_hash = artifact_hash(gguf) if gguf.is_file() else None
    # The weights may already be restored while the sidecar still has pending.
    restored = (verdict and verdict.get("ok") is False and
                ((pending.get("previous_hash") is None and current_hash is None and not previous.exists()) or
                 (pending.get("previous_hash") == current_hash and not previous.exists())))
    if restored:
        old_side = export_mod.sidecar_path(previous)
        if old_side.exists():
            os.replace(old_side, side_path)
        else:
            side_path.unlink(missing_ok=True)
        return verdict

    def matches():
        latest = read_json(side_path, {}) or {}
        try:
            generation = paths.adapter.relative_to(paths.home).as_posix()
        except (RuntimeError, ValueError):
            generation = None
        descriptor = latest.get("served_pending") if isinstance(latest, dict) else None
        return (isinstance(descriptor, dict) and latest.get("night_id") == pending.get("night_id")
                and latest.get("profile") == prof.name and latest.get("base_hf_id") == prof.hf_id
                and descriptor.get("sha256") == pending.get("sha256")
                and generation == pending.get("adapter") and gguf.is_file()
                and artifact_hash(gguf) == pending.get("sha256"))

    if not matches():
        return deferred("not checked: pending adapter identity no longer matches the current artifact")
    if verdict is None:
        try:
            verdict = (checker or check_gguf)(cfg.llama_server, cfg.base_gguf, str(gguf), pending["held"],
                                             log=str(paths.home / "served_check.log"))
        except Exception as error:
            return deferred("not checked: %s: %s" % (type(error).__name__, error))
        if not matches():
            return deferred("not applied: adapter changed during its served check")
        if verdict.get("ok") is None:
            return dict(verdict, pending=True)
        if verdict.get("ok") is False:
            verdict = dict(verdict, fallback="previous adapter.gguf" if pending.get("previous_hash") else "plain model (no adapter.gguf)",
                           note="the trained adapter was kept for the next night; the daytime GGUF is the older one")
        # Keep serving blocked until sidecar publication or rollback completes.
        pending["verdict"] = verdict
        side["served_pending"] = pending
        write_json(side_path, side)
    # Persist the matching night result before applying the verdict: a crash
    # after rollback may remove the sidecar that held the deferred work.
    _record_finalization(paths, pending["night_id"], verdict)
    if verdict.get("ok") is False:
        expected_previous = pending.get("previous_hash")
        actual_previous = artifact_hash(previous) if previous.is_file() else None
        if actual_previous != expected_previous:
            return deferred("not restored: previous adapter changed during its served check")
        export_mod.restore_prev(gguf)
    else:
        side.pop("served_pending", None)
        side["served"] = verdict
        write_json(side_path, side)
    log("[night] served check (llama-server, adapter on vs off): %s" % verdict)
    return verdict

N_GENERAL = 8
MAX_HELD = 12


def latest_held(cards_path) -> List[dict]:
    """Held-out cards of the newest night in cards.jsonl."""
    rows = []
    try:
        for line in Path(cards_path).read_text().splitlines():
            try:
                r = json.loads(line)
            except ValueError:
                continue
            if r.get("status") == "held_out" and r.get("q") and r.get("a"):
                rows.append(r)
    except OSError:
        return []
    if not rows:
        return []
    last = max(int(r.get("night") or 0) for r in rows)
    return [r for r in rows if int(r.get("night") or 0) == last][:MAX_HELD]


def ask(url: str, system: str, question: str, scale: float, max_tokens: int = 24, timeout: float = 60.0) -> str:
    body = {"messages": [{"role": "system", "content": system}, {"role": "user", "content": question}], "max_tokens": max_tokens,
            "temperature": 0, "lora": [{"id": 0, "scale": scale}], "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(url.rstrip("/") + "/v1/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    msg = json.loads(urllib.request.urlopen(req, timeout=timeout).read())["choices"][0]["message"]
    return msg.get("content") or ""


def judge(gen_on: Sequence[bool], gen_off: Sequence[bool], held_on: Sequence[bool], held_off: Sequence[bool], max_general_loss: int = 1) -> Dict:
    reasons = []
    g1, g0, h1, h0 = sum(gen_on), sum(gen_off), sum(held_on), sum(held_off)
    if g1 < g0 - max_general_loss:
        reasons.append("general %d/%d with the adapter vs %d/%d without" % (g1, len(gen_on), g0, len(gen_off)))
    if gen_on and g1 * 2 < g0:   # relative to the plain model: a broken conversion answers garbage
        reasons.append("general only %d/%d with the adapter vs %d without (broken adapter?)" % (g1, len(gen_on), g0))
    if h1 < h0:
        reasons.append("held-out %d/%d with the adapter vs %d/%d without" % (h1, len(held_on), h0, len(held_off)))
    return {"ok": not reasons, "reasons": reasons, "general_on": g1, "general_off": g0, "general_n": len(gen_on),
            "held_on": h1, "held_off": h0, "held_n": len(held_on)}


def served_check(url: str, held: Sequence[dict], n_general: int = N_GENERAL, asker: Callable = ask) -> Dict:
    t0 = time.time()
    qs = gate_mod.gate_questions(n_general)
    gen = {s: [gate_mod.correct(asker(url, gate_mod.GATE_SYS, q, s), acc, q) for q, acc in qs] for s in (1.0, 0.0)}
    hs = {s: [gate_mod.recall_hit(c["a"], asker(url, "Answer with just the name.", c["q"], s, 16)) for c in held] for s in (1.0, 0.0)}
    r = judge(gen[1.0], gen[0.0], hs[1.0], hs[0.0])
    r["elapsed_s"] = round(time.time() - t0, 1)
    return r


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _healthy(url: str) -> bool:
    try:
        return urllib.request.urlopen(url + "/health", timeout=2).status == 200
    except Exception:
        return False


def _starts(cmd, url, wait_s, out) -> bool:
    """Does llama-server become healthy with this command line? (stopped again at once)"""
    p = subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT)
    try:
        end = time.time() + wait_s
        while time.time() < end and p.poll() is None:
            if _healthy(url):
                return True
            time.sleep(0.5)
        return False
    finally:
        if p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=20)
            except subprocess.TimeoutExpired:
                p.kill()


def check_gguf(server_bin: str, base_gguf: str, lora: str, held: Sequence[dict], port: Optional[int] = None, wait_s: float = 120.0,
               log: Optional[str] = None) -> Dict:
    """Start our own llama-server on a free port with the adapter, run served_check, stop it. Never raises."""
    port = port or free_port()
    url = "http://127.0.0.1:%d" % port
    cmd = [os.path.expanduser(server_bin), "-m", os.path.expanduser(base_gguf), "--lora", str(lora), "--host", "127.0.0.1", "--port", str(port),
           "-c", "2048", "-np", "1", "--jinja", "-ngl", "99", "--no-webui"]
    out = open(log, "ab") if log else subprocess.DEVNULL
    p = None
    try:
        p = subprocess.Popen(cmd, stdout=out, stderr=subprocess.STDOUT)
        end = time.time() + wait_s
        while time.time() < end and p.poll() is None and not _healthy(url):
            time.sleep(0.5)
        if p.poll() is not None:
            # the adapter's fault only if the plain model starts fine on its own (else: memory, binary, model file)
            code = p.returncode
            if _starts(cmd[:cmd.index("--lora")] + cmd[cmd.index("--lora") + 2:], url, wait_s, out):
                return {"ok": False, "reasons": ["llama-server would not load the adapter (exit %s); the plain model loads" % code]}
            return {"ok": None, "reasons": ["not checked: llama-server did not start even without the adapter (exit %s)" % code]}
        if not _healthy(url):
            return {"ok": None, "reasons": ["not checked: llama-server did not become ready in %ds" % wait_s]}
        return served_check(url, held)
    except Exception as e:
        return {"ok": None, "reasons": ["not checked: %s: %s" % (type(e).__name__, e)]}
    finally:
        if p is not None and p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=20)
            except subprocess.TimeoutExpired:
                p.kill()
        if log and out is not subprocess.DEVNULL:
            out.close()


def main(argv) -> int:
    from .paths import Paths
    def opt(name, default=None):
        return argv[argv.index(name) + 1] if name in argv else default
    url = opt("--server")
    if not url:
        print("usage: python -m sleepmlx served-check --server URL [--n 8] [--cards FILE]")
        return 2
    cards = opt("--cards") or str(Paths.from_env().cards)
    if not _healthy(url.rstrip("/")):
        print(json.dumps({"ok": None, "reasons": ["not checked: the server did not answer"]}))
        return 2
    try:
        r = served_check(url.rstrip("/"), latest_held(cards), int(opt("--n", N_GENERAL)))
    except Exception as e:   # the server went away mid-check: not a verdict on the adapter
        print(json.dumps({"ok": None, "reasons": ["not checked: %s: %s" % (type(e).__name__, e)]}))
        return 2
    print(json.dumps(r))
    return 0 if r["ok"] else 1
