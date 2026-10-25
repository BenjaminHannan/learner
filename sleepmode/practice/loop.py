"""One practice round: tasks -> model -> sandbox -> checker -> SFT / DPO records."""
from __future__ import annotations

import datetime
import json
import os
import re
import time

from . import agent, habits, research, sandbox, tasks

SYSTEM = ("You write a Python 3 script that uses only the standard library. The script reads the input CSV "
          "file(s) in the current directory and writes the result to output.csv in the current directory. "
          "Follow the column names and ordering rules in the task exactly. Reply with one ```python code "
          "block and nothing else.")
TOOLS_NOTE = (" Before answering you may use tools: python to test your script on the task files (they are in "
              "the working directory), web_search for tips, diary_search to see how Ben phrases requests. "
              "Then reply with the final ```python block.")
_FENCE = re.compile(r"```[ \t]*(?:python3?|py)?[ \t]*\r?\n(.*?)```", re.S | re.I)


def _compiles(code: str) -> bool:
    try:
        compile(code, "attempt.py", "exec")
        return True
    except (SyntaxError, ValueError):
        return False


def extract_code(reply: str):
    blocks = [b.strip("\n") for b in _FENCE.findall(reply or "")]
    for b in blocks:
        if _compiles(b):
            return b
    if blocks:
        return blocks[0]
    bare = (reply or "").strip()
    return bare if bare and _compiles(bare) else None


def _preview(files: dict, n: int = 5) -> str:
    return "\n\n".join("%s (first %d lines):\n%s" % (k, n, "\n".join(v.splitlines()[:n])) for k, v in files.items())


def _words(s):
    return set(re.findall(r"[a-z]{4,}", s.lower()))


def pick_card(task, cards):
    for c in cards:
        if task.family in (c.get("families") or []):
            return c
    best, score = None, 0
    tw = _words(task.instruction)
    for c in cards:
        n = len(tw & _words(c.get("title", "") + " " + c.get("how", "")))
        if n > score:
            best, score = c, n
    return best if score >= 3 else None


def user_prompt(task, hint=None) -> str:
    u = "%s\n\n%s" % (task.instruction, _preview(task.files))
    if hint:
        u += "\n\nHint (a trick that may help): %s. %s Example: %s" % (hint["title"], hint["how"], hint.get("example", ""))
    return u


def _fenced(code: str) -> str:
    return "```python\n%s\n```" % code


def _attempt(task, code):
    if code is None:
        return False, "no Python code block found in the reply", None
    r = sandbox.run_python(code, task.files, timeout_s=20)
    if not r.ok:
        return False, "script failed:\n" + (r.stderr or r.stdout)[-1500:], r
    ok, why = task.check(r.files_out)
    return ok, "" if ok else "output.csv is wrong: " + why, r


def _append(path, recs):
    if recs:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            for r in recs:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")


def run_round(kind, model, budget_s, out_dir, seed=0, n_tasks=12, tricks=None, retries=2,
              toolbox=None, use_tools=None, max_steps=6) -> dict:
    t0 = time.time()
    tricks = tricks or []
    use_tools = toolbox is not None if use_tools is None else (use_tools and toolbox is not None)
    tool_n: dict = {}
    sft, pairs, done, p1, pany, used, errs, consec = [], [], 0, 0, 0, 0, 0, 0
    stopped = False
    for task in tasks.generate(kind, n_tasks, seed):
        if time.time() - t0 >= budget_s or consec >= 3:
            stopped = True
            break
        hint = pick_card(task, tricks)
        used += hint is not None
        base = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user_prompt(task)}]
        msgs = [base[0], {"role": "user", "content": user_prompt(task, hint)}]
        if use_tools:
            toolbox.sandbox_files = dict(task.files)
            msgs[0] = {"role": "system", "content": SYSTEM + TOOLS_NOTE}
        first_bad = passed = None
        for i in range(retries + 1):
            try:
                temp = 0.2 if i == 0 else 0.5
                if use_tools:
                    reply, tr = agent.run_agent(model, msgs, toolbox, max_steps=max_steps,
                                                budget_s=max(10.0, budget_s - (time.time() - t0)), temperature=temp)
                    for k, v in agent.tool_counts(tr).items():
                        tool_n[k] = tool_n.get(k, 0) + v
                else:
                    reply = model.chat(msgs, max_tokens=1500, temperature=temp)
                consec = 0
            except Exception:
                errs += 1
                consec += 1
                break
            code = extract_code(reply)
            ok, why, _ = _attempt(task, code)
            if ok:
                passed = code
                break
            if first_bad is None:
                first_bad = code if code is not None else reply
            msgs = msgs + [{"role": "assistant", "content": reply},
                           {"role": "user", "content": why + "\n\nFix it and reply with the complete corrected script in one ```python block."}]
        if consec:
            continue
        done += 1
        p1 += passed is not None and first_bad is None
        pany += passed is not None
        if passed is not None:
            sft.append({"messages": base + [{"role": "assistant", "content": _fenced(passed)}]})
            if first_bad is not None:
                pairs.append({"prompt": base, "chosen": _fenced(passed), "rejected": _fenced(first_bad)})
    summary = {"kind": kind, "n": done, "pass1": p1 / done if done else 0.0,
               "pass_any": pany / done if done else 0.0, "tricks_used": used,
               "elapsed_s": round(time.time() - t0, 2), "seed": seed, "model_errors": errs,
               "stopped_early": stopped, "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
               "sft_n": len(sft), "pairs_n": len(pairs),
               "tools": use_tools, "tool_calls": tool_n, "tool_calls_total": sum(tool_n.values())}
    paths = {"sft_path": os.path.join(out_dir, "sft.jsonl"), "pairs_path": os.path.join(out_dir, "pairs.jsonl"),
             "rounds_path": os.path.join(out_dir, "rounds.jsonl")}
    _append(paths["sft_path"], sft)
    _append(paths["pairs_path"], pairs)
    _append(paths["rounds_path"], [summary])
    summary.update(paths)
    return summary


def make_practice_fn(home_dir, diary_dir, model, *, n_tasks=12, seed=None, research_web=True, min_share=0.05,
                     tools=True):
    """-> callable(budget_s) -> round summary dict, or None when nothing is practicable."""
    def practice(budget_s):
        t0 = time.time()
        kind = habits.pick_kind(habits.analyze(diary_dir), min_share)
        if kind is None:
            return None
        try:
            cards = research.get_tricks(kind, home_dir, web=research_web, model=model)
        except Exception:
            cards = research.get_tricks(kind, home_dir, web=False)
        day = datetime.date.today().isoformat()
        s = seed if seed is not None else int(time.time())
        from ..tools import ToolBox  # tools imports this package
        toolbox = ToolBox(diary_dir, web=research_web) if tools else None
        return run_round(kind, model, max(0.0, budget_s - (time.time() - t0)),
                         os.path.join(str(home_dir), "practice", day), s, n_tasks, cards, toolbox=toolbox)
    return practice
