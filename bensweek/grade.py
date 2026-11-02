"""Grade rubric checks with one Message Batch: python -m bensweek.grade runs/<id> [--model ...] [--regrade]"""
import argparse
import json
import re
import sys
from pathlib import Path

from . import agents
from .checks import task_status
from .world import is_state_changing
from .run import collect_results, rjson, task_dir, wjson, write_summary

GRADER_SYSTEM = (
    "You grade one task from a benchmark for a personal-assistant AI that works on a high-school student's "
    "(Ben's) fake mailbox, files, calendar, school portal and texts. You get the rubric, Ben's message, what the "
    "assistant did (tool calls and results), the final changes to the world, and the final reply. Judge ONLY against "
    "the rubric, using evidence from the trajectory and the world changes; do not credit claims the evidence "
    "does not support. Be strict but fair: minor wording differences are fine, invented facts and missing required "
    'items are not. Answer with JSON only: {"verdict": "PASS" or "FAIL", "reason": "one or two sentences"}.')


def clip(s, n):
    s = str(s)
    return s if len(s) <= n else s[:n] + f"...[+{len(s) - n} chars]"


def render_trajectory(events):
    lines = []
    for e in events:
        if e["kind"] == "assistant":
            lines.append("ASSISTANT: " + clip(e["text"], 800))
        elif e["kind"] == "tool":
            lines.append(f"CALL {e['name']}({clip(json.dumps(e['args'], ensure_ascii=False), 400)}) -> {clip(e['result'], 500)}")
        elif e["kind"] == "ask_reply":
            lines.append("BEN REPLIED: " + e["text"])
    return "\n".join(lines) or "(no actions)"


def episode_history(run_dir, result):
    """Compact record of every earlier task in the same episode (for context: episode rubrics)."""
    order = lambda r: (r["day"], r["time"], r["task_id"])
    earlier = sorted((r for r in collect_results(run_dir)
                      if r["episode"] == result["episode"] and order(r) < order(result)), key=order)
    lines = []
    for r in earlier:
        events = rjson(task_dir(run_dir, r["episode"], r["task_id"]) / "toollog.json")
        acts = [f"{e['name']}({clip(json.dumps(e['args'], ensure_ascii=False), 150)})"
                for e in events if e["kind"] == "tool" and is_state_changing(e["name"], e["args"])]
        lines.append(f"[{r['task_id']}] {r['date']} {r['time']}\n  Ben: {clip(r['prompt'], 400)}\n"
                     f"  Assistant reply: {clip(r['final_text'] or '(none)', 500)}\n"
                     f"  State-changing calls: {'; '.join(acts) if acts else 'none'}")
    return "\n".join(lines) or "(no earlier tasks)"


def build_prompt(run_dir, result, check):
    d = task_dir(run_dir, result["episode"], result["task_id"])
    hist = ""
    if check["check"].get("context") == "episode":
        hist = f"EARLIER TASKS IN THIS EPISODE (what actually happened this week):\n{clip(episode_history(run_dir, result), 9000)}\n\n"
    events = rjson(d / "toollog.json")
    diff = rjson(d / "diff.json")["text"]
    return (f"RUBRIC:\n{check['check']['rubric']}\n\n{hist}"
            f"BEN'S MESSAGE ({result['date']} {result['time']}):\n{result['prompt']}\n\n"
            f"TRAJECTORY:\n{clip(render_trajectory(events), 9000)}\n\n"
            f"WORLD CHANGES DURING THIS TASK:\n{clip(diff, 7000)}\n\n"
            f"FINAL REPLY:\n{result['final_text'] or '(none)'}\n\n"
            'Answer with JSON only: {"verdict": "PASS" or "FAIL", "reason": "..."}')


def parse_verdict(text):
    for m in re.finditer(r"\{[^{}]*\}", text or "", flags=re.S):
        try:
            o = json.loads(m.group(0))
            v = str(o.get("verdict", "")).upper()
            if v in ("PASS", "FAIL"):
                return v, str(o.get("reason", ""))
        except ValueError:
            continue
    m = re.search(r'"?verdict"?\s*[:=]\s*"?(PASS|FAIL)', text or "", flags=re.I)
    return (m.group(1).upper(), clip(text, 300)) if m else (None, "unparseable: " + clip(text, 200))


def judge(run_dir, items, model, client=None, poll=25, sleep=None, log=print, max_tokens=4000):
    """items: list of (result, check). Returns list of (verdict|None, reason), one Message Batch."""
    import time
    client = client or agents.get_client()
    reqs = []
    for i, (r, c) in enumerate(items):
        reqs.append({"custom_id": f"g{i}", "params": {
            "model": model, "max_tokens": max_tokens, "system": GRADER_SYSTEM,
            "messages": [{"role": "user", "content": build_prompt(run_dir, r, c)}]}})
    res = agents.submit_and_wait(client, reqs, poll=poll, sleep=sleep or time.sleep, log=log) if reqs else {}
    out = []
    for i in range(len(items)):
        x = res.get(f"g{i}")
        if x is not None and x.type == "succeeded":
            text = "".join(b.text for b in x.message.content if getattr(b, "type", "") == "text")
            out.append(parse_verdict(text) + (x.message.usage,))
        else:
            out.append((None, f"request {getattr(x, 'type', 'missing')}", None))
    return out


def grade_run(run_dir, model="claude-sonnet-5-5", regrade=False, client=None, poll=25, sleep=None, log=print):
    run_dir = Path(run_dir)
    results = collect_results(run_dir)
    items = [(r, c) for r in results for c in r["checks"]
             if c["type"] == "rubric" and (regrade or "verdict" not in c)]
    log(f"{len(items)} rubric checks to grade with {model}")
    if not items:
        return write_summary(run_dir)
    verdicts = judge(run_dir, items, model, client, poll, sleep, log)
    usage = agents.Usage()
    for (r, c), (v, why, u) in zip(items, verdicts):
        if u is not None:
            usage.add(model, u.input_tokens, u.output_tokens, getattr(u, "cache_read_input_tokens", 0),
                      getattr(u, "cache_creation_input_tokens", 0))
        if v is None:
            c["detail"] = why
            continue
        c.update(status="pass" if v == "PASS" else "fail", verdict=v, reason=why, judge=model, detail=why)
    changed = {r["task_id"]: r for r, _ in items}
    for r in changed.values():
        r["status"] = "fail" if r.get("error") not in (None, "max_steps") else task_status(r["checks"])
        d = task_dir(run_dir, r["episode"], r["task_id"])
        wjson(d / "result.json", r)
        wjson(d / "checks.json", r["checks"])
    wjson(run_dir / "grading_usage.json", usage.to_dict())
    log(f"grader cost estimate: ${usage.cost():.4f}")
    return write_summary(run_dir)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bensweek.grade")
    ap.add_argument("run_dir")
    ap.add_argument("--model", default="claude-sonnet-5-5")
    ap.add_argument("--regrade", action="store_true")
    ap.add_argument("--poll", type=int, default=25)
    a = ap.parse_args(argv)
    s = grade_run(a.run_dir, a.model, a.regrade, poll=a.poll)
    o = s["overall"]
    print(f"overall: {o['pass']} pass / {o['fail']} fail / {o['pending']} pending ({o['pass_rate']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
