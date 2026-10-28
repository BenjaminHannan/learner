"""Reference real sleep worker for the Mac: LoRA on diary + practice data with mlx_lm.

Run as `python -m sleepmode.mlx_worker` under CommandWorker (reads SLEEPMODE_* env, writes SLEEPMODE_OUT).
quiz = -test_loss * 100 on a frozen held-out split of diary conversations.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

QUIZ_FRACTION = 0.05
QUIZ_MIN_TURNS = 20


# ---- diary -> chat data (pure) ----

def flatten_content(content) -> Optional[str]:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"]
        return "\n".join(p for p in parts if p) or None
    return None


def record_to_example(rec: dict) -> Optional[dict]:
    """One diary record -> {"conv_id", "messages"} (user/assistant turns plus the logged response)."""
    msgs = []
    for m in rec.get("messages") or []:
        role = m.get("role")
        if role not in ("user", "assistant"):
            continue
        text = flatten_content(m.get("content"))
        if text:
            msgs.append({"role": role, "content": text})
    resp = rec.get("response") or {}
    reply = resp.get("content") if isinstance(resp, dict) else None
    if not isinstance(reply, str) or not reply.strip():
        return None
    if rec.get("status") not in (None, 200):
        return None
    msgs.append({"role": "assistant", "content": reply})
    if not any(m["role"] == "user" for m in msgs) or len(msgs) < 2:
        return None
    conv = str(rec.get("conv_id") or hashlib.sha1(msgs[0]["content"].encode()).hexdigest()[:12])
    return {"conv_id": conv, "messages": msgs}


def read_diary(diary_dir: str) -> List[dict]:
    out: List[dict] = []
    for p in sorted(Path(diary_dir).glob("*.jsonl")):
        try:
            lines = p.read_text().splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                ex = record_to_example(json.loads(line))
            except ValueError:
                continue
            if ex:
                out.append(ex)
    return out


def conv_bucket(conv_id: str) -> float:
    return int(hashlib.sha1(conv_id.encode()).hexdigest()[:8], 16) / float(16 ** 8)


def split_quiz(examples: Sequence[dict], frac: float = QUIZ_FRACTION,
               min_turns: int = QUIZ_MIN_TURNS) -> Tuple[List[dict], List[dict]]:
    """Whole conversations go to the quiz by hash (stable). Top up with lowest-hash convs to min_turns."""
    convs = sorted({e["conv_id"] for e in examples}, key=conv_bucket)
    chosen = {c for c in convs if conv_bucket(c) < frac}
    counts = {}
    for e in examples:
        counts[e["conv_id"]] = counts.get(e["conv_id"], 0) + 1
    n = sum(counts[c] for c in chosen)
    limit = len(examples) // 2
    for c in convs:
        if n >= min_turns:
            break
        if c not in chosen and n + counts[c] <= max(limit, min_turns):
            chosen.add(c)
            n += counts[c]
    quiz = [e for e in examples if e["conv_id"] in chosen]
    train = [e for e in examples if e["conv_id"] not in chosen]
    return train, quiz


def load_jsonl(path: Path) -> List[dict]:
    out = []
    try:
        for line in path.read_text().splitlines():
            if line.strip():
                out.append(json.loads(line))
    except (OSError, ValueError):
        pass
    return out


def write_jsonl(path: Path, rows: Iterable[dict]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with open(str(path), "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
            n += 1
    return n


def read_practice_sft(files: Iterable[str]) -> List[dict]:
    out = []
    for f in files:
        if os.path.basename(f) == "sft.jsonl":
            out += [{"conv_id": "practice", "messages": r["messages"]}
                    for r in load_jsonl(Path(f)) if isinstance(r.get("messages"), list)]
    return out


def build_data(diary_dir: str, practice_files: Iterable[str], worker_dir: Path, data_dir: Path) -> dict:
    """Write data_dir/{train,valid,test}.jsonl. Quiz split is frozen in worker_dir/quiz.jsonl on first run."""
    diary = read_diary(diary_dir)
    quiz_path = worker_dir / "quiz.jsonl"
    quiz = load_jsonl(quiz_path)
    if quiz:
        frozen = {q["conv_id"] for q in quiz}
        train = [e for e in diary if e["conv_id"] not in frozen]
    else:
        train, quiz = split_quiz(diary)
        if quiz:
            write_jsonl(quiz_path, quiz)
    train = train + read_practice_sft(practice_files)
    strip = lambda rows: [{"messages": r["messages"]} for r in rows]
    write_jsonl(data_dir / "train.jsonl", strip(train))
    write_jsonl(data_dir / "valid.jsonl", strip(quiz[:5]))
    write_jsonl(data_dir / "test.jsonl", strip(quiz))
    return {"train": len(train), "quiz": len(quiz)}


# ---- planning, args, parsing (pure) ----

def plan_iters(budget_s: float, step_s: float, reserve_frac: float = 0.15, reserve_min_s: float = 30.0) -> int:
    """Iterations that fit in the budget after reserving time for model load and the quiz."""
    if step_s <= 0:
        return 0
    usable = budget_s - max(reserve_min_s, reserve_frac * budget_s)
    return max(0, int(usable / step_s))


def lora_train_args(model: str, data_dir: str, adapter_path: str, iters: int, resume: bool = False,
                    grad_checkpoint: bool = True, steps_per_report: Optional[int] = None,
                    python: str = sys.executable) -> List[str]:
    a = [python, "-m", "mlx_lm", "lora", "--model", model, "--train", "--data", str(data_dir),
         "--adapter-path", str(adapter_path), "--iters", str(iters), "--batch-size", "1",
         "--num-layers", "16", "--max-seq-length", "2048"]
    if resume:
        a += ["--resume-adapter-file", str(Path(adapter_path, "adapters.safetensors"))]
    if grad_checkpoint:
        a.append("--grad-checkpoint")
    if steps_per_report:
        a += ["--steps-per-report", str(steps_per_report)]
    return a


def lora_test_args(model: str, data_dir: str, adapter_path: str, python: str = sys.executable) -> List[str]:
    return [python, "-m", "mlx_lm", "lora", "--model", model, "--adapter-path", str(adapter_path),
            "--data", str(data_dir), "--test"]


def parse_test_loss(text: str) -> Optional[float]:
    m = re.findall(r"Test loss\s+([0-9]*\.?[0-9]+)", text)
    return float(m[-1]) if m else None


def parse_it_per_sec(text: str) -> Optional[float]:
    m = re.findall(r"It/sec\s+([0-9]*\.?[0-9]+)", text)
    return float(m[-1]) if m else None


# ---- running ----

_child: Optional[subprocess.Popen] = None
_stopping = False


def _run(args: Sequence[str], log: Path) -> Tuple[int, str]:
    global _child
    with open(str(log), "ab") as lf:
        lf.write(("\n$ " + " ".join(args) + "\n").encode())
    _child = subprocess.Popen(list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    chunks = []
    with open(str(log), "a") as lf:
        for line in _child.stdout:
            chunks.append(line)
            lf.write(line)
            lf.flush()
    rc = _child.wait()
    _child = None
    return rc, "".join(chunks)


def _on_term(signum, frame):
    global _stopping
    _stopping = True
    if _child is not None:
        _child.terminate()


def main() -> int:
    from .config import load
    cfg = load()
    budget = float(os.environ.get("SLEEPMODE_BUDGET_S", "600"))
    out_path = Path(os.environ.get("SLEEPMODE_OUT", str(cfg.worker_dir / "chunk_out.json")))
    practice = [p for p in os.environ.get("SLEEPMODE_PRACTICE", "").split(os.pathsep) if p]
    wd = Path(os.environ.get("SLEEPMODE_WORKDIR", str(cfg.worker_dir)))
    adapter = wd / "adapters"
    data_dir = wd / "data"
    log = wd / "mlx.log"
    wd.mkdir(parents=True, exist_ok=True)
    signal.signal(signal.SIGTERM, _on_term)
    t0 = time.time()
    result: dict = {"quiz": None, "steps": 0}

    def finish() -> int:
        result["elapsed_s"] = time.time() - t0
        out_path.write_text(json.dumps(result))
        return 0

    counts = build_data(cfg.diary_dir, practice, wd, data_dir)
    result.update(counts)
    if counts["train"] == 0:
        result["error"] = "no training data"
        return finish()
    resume = (adapter / "adapters.safetensors").exists()
    # time a few steps in a throwaway adapter dir (includes model load, so it is conservative)
    probe_n = 6
    t1 = time.time()
    rc, text = _run(lora_train_args(cfg.mlx_model, str(data_dir), str(wd / "probe"), probe_n,
                                    steps_per_report=3), log)
    ips = parse_it_per_sec(text)
    step_s = 1.0 / ips if ips else (time.time() - t1) / probe_n
    if _stopping:
        result["interrupted"] = True
        return finish()
    iters = plan_iters(budget - (time.time() - t0), step_s)
    result["step_s"] = step_s
    if iters > 0:
        rc, text = _run(lora_train_args(cfg.mlx_model, str(data_dir), str(adapter), iters, resume=resume), log)
        result["steps"] = iters if rc == 0 else 0
        if rc != 0:
            result["error"] = "train exit %d" % rc
    if _stopping:
        result["interrupted"] = True
        return finish()
    if (adapter / "adapters.safetensors").exists() and counts["quiz"] > 0:
        rc, text = _run(lora_test_args(cfg.mlx_model, str(data_dir), str(adapter)), log)
        loss = parse_test_loss(text)
        if loss is not None:
            result["quiz"] = -loss * 100
            result["test_loss"] = loss
            hist = wd / "quiz_history.jsonl"
            with open(str(hist), "a") as f:
                f.write(json.dumps({"ts": time.time(), "test_loss": loss, "iters": iters}) + "\n")
    return finish()


if __name__ == "__main__":
    sys.exit(main())
