"""Runner: python -m bensweek.run --agent openai|claude|scripted ..."""
import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from . import agents
from .checks import run_checks, task_status
from .episodes import load_episodes
from .world import MEMORY_MODES, World, diff_snapshots, load_base, merge_world, render_diff


# ---------------------------------------------------------------- prompts

def system_prompt(world, memory, history):
    now = world.now
    p = world.profile
    lines = [
        f"You are {p.get('name', 'Ben')}'s personal assistant, running on his Mac. You act with tools on his email, "
        "calendar, files, school portal, texts and reminders.",
        f"Now: {now.strftime('%A')}, {now.strftime('%B')} {now.day}, {now.year}, {now.strftime('%H:%M')} ({p.get('timezone', '')}).",
        f"About Ben: {p.get('name')}, {p.get('email')}, phone {p.get('phone')}, grade {p.get('grade')} at {p.get('school')}. {p.get('about', '')}",
        "Use the tools to do things rather than guess. Ask Ben before anything risky or irreversible (deleting things, "
        "sending messages to other people when unsure, anything that can't be undone). Keep replies short and plain.",
    ]
    if memory in ("notes", "diary", "context"):
        lines.append("Each chat starts fresh. You have a notebook (notes_read, notes_write) to remember things Ben tells you.")
    if memory == "diary":
        lines.append("You can also search your earlier chats this week with diary_search.")
    if memory == "context" and history:
        lines.append("Earlier chats this week:")
        for h in history:
            lines.append(f"[{h['date']} {h['time']}] Ben: {h['user']}\n  You: {h['assistant'][:400]}")
    return "\n".join(lines)


# ---------------------------------------------------------------- run directory helpers

def task_dir(run_dir, ep_id, task_id):
    return Path(run_dir) / "episodes" / ep_id / task_id


def wjson(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, indent=1, ensure_ascii=False))


def rjson(path):
    return json.loads(Path(path).read_text())


class EpisodeState:
    def __init__(self, ep, run_dir, memory, base, resume=False):
        self.ep = ep
        self.id = ep["id"]
        self.days = ep["days"]
        self.run_dir = Path(run_dir)
        self.memory = memory
        self.world = World(merge_world(base, ep.get("world")), memory)
        self.history = []
        self.done = set()
        if resume:
            self._restore()

    def tasks(self):
        return [t for d in self.days for t in d["tasks"]]

    def _restore(self):
        last = None
        for t in self.tasks():
            rp = task_dir(self.run_dir, self.id, t["id"]) / "result.json"
            if not rp.exists():
                break
            r = rjson(rp)
            self.done.add(t["id"])
            self.add_history(r["date"], r["time"], r["prompt"], r["final_text"], t["id"])
            last = t["id"]
        if last:
            self.world.restore(rjson(task_dir(self.run_dir, self.id, last) / "world_state.json"))

    def add_history(self, date_s, time_s, user, assistant, task_id):
        self.history.append({"date": date_s, "time": time_s, "user": user, "assistant": assistant})
        self.world.diary.append({"date": date_s, "time": time_s, "task": task_id, "user": user, "assistant": assistant})


class DayDriver:
    """Runs one episode's tasks for one day, sequentially (they share world state)."""

    def __init__(self, ep, day_idx, max_steps, model_name):
        self.ep = ep
        self.day_idx = day_idx
        self.day = ep.days[day_idx]
        self.max_steps = max_steps
        self.model_name = model_name
        self.pending = [t for t in self.day["tasks"] if t["id"] not in ep.done]
        self.conv = None
        self.task = None
        if len(self.pending) == len(self.day["tasks"]):
            ep.world.set_time(self.day["date"], self.day.get("time", "08:00"))
            ep.world.apply_arrivals(self.day.get("arrivals"))
        self._start_next()

    def _start_next(self):
        self.conv = None
        if not self.pending:
            return
        t = self.task = self.pending.pop(0)
        w = self.ep.world
        w.begin_task(t["id"], t.get("ask_reply"))
        w.set_time(self.day["date"], t.get("time") or self.day.get("time", "08:00"))
        self.before = w.snapshot()
        self.conv = agents.Conversation(
            t["id"], w, system_prompt(w, self.ep.memory, self.ep.history), t["prompt"], w.tools(),
            kind=t.get("kind", "task"), max_steps=self.max_steps)

    def pump(self):
        while self.conv:
            req = self.conv.next_request()
            if req is not None:
                return req
            self._complete()
        return None

    def consume(self, resp):
        self.conv.consume(resp)

    def _complete(self):
        ep, t, conv, w = self.ep, self.task, self.conv, self.ep.world
        rec = {"events": conv.events, "final_text": conv.final_text}
        results = run_checks(t, w, rec)
        status = task_status(results)
        if conv.error and conv.error != "max_steps":
            status = "fail"
        diff = diff_snapshots(self.before, w.snapshot())
        d = task_dir(ep.run_dir, ep.id, t["id"])
        result = {"episode": ep.id, "day": self.day_idx + 1, "date": self.day["date"], "time": w.now.strftime("%H:%M"),
                  "task_id": t["id"], "kind": t.get("kind", "task"), "tags": t.get("tags", []), "prompt": t["prompt"],
                  "status": status, "scored": bool(t.get("checks")), "checks": results, "final_text": conv.final_text,
                  "steps": conv.steps, "tool_calls": conv.n_tool_calls, "error": conv.error,
                  "memory_source": t.get("memory_source")}
        wjson(d / "transcript.json", conv.transcript())
        wjson(d / "toollog.json", conv.events)
        wjson(d / "checks.json", results)
        wjson(d / "diff.json", {"diff": diff, "text": render_diff(diff)})
        wjson(d / "world_state.json", w.snapshot())
        wjson(d / "result.json", result)          # written last: marks the task finished
        ep.done.add(t["id"])
        ep.add_history(self.day["date"], w.now.strftime("%H:%M"), t["prompt"], conv.final_text, t["id"])
        print(f"  {t['id']}: {status}" + (f" [{conv.error}]" if conv.error else ""), flush=True)
        self._start_next()


# ---------------------------------------------------------------- diary, results, summary

def write_diary(run_dir, ep, day_idx, model):
    day = ep.days[day_idx]
    lines = []
    for t in day["tasks"]:
        d = task_dir(run_dir, ep.id, t["id"])
        if not (d / "result.json").exists():
            continue
        r, msgs = rjson(d / "result.json"), rjson(d / "transcript.json")
        lines.append(json.dumps({"ts": f"{r['date']}T{r['time']}:00", "date": r["date"], "conv_id": t["id"],
                                 "model": model, "messages": msgs, "user_text": r["prompt"],
                                 "assistant_text": r["final_text"]}, ensure_ascii=False))
    p = Path(run_dir) / "diary" / ep.id / f"day{day_idx + 1}.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("\n".join(lines) + ("\n" if lines else ""))


def collect_results(run_dir):
    out = []
    for p in sorted((Path(run_dir) / "episodes").glob("*/*/result.json")):
        out.append(rjson(p))
    return out


def save_results(run_dir, results):
    (Path(run_dir) / "results.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in results))


def _bucket():
    return {"pass": 0, "fail": 0, "pending": 0}


def _rate(b):
    dec = b["pass"] + b["fail"]
    return round(b["pass"] / dec, 3) if dec else None


def build_summary(results):
    overall, tags, eps, days = _bucket(), {}, {}, {}
    rub = {"pending": 0, "pass": 0, "fail": 0}
    unscored = 0
    for r in results:
        for c in r["checks"]:
            if c["type"] == "rubric":
                rub[c["status"]] += 1
        if not r.get("scored"):
            unscored += 1
            continue
        keys = [(overall, None), (eps.setdefault(r["episode"], _bucket()), None),
                (days.setdefault(f"day{r['day']}", _bucket()), None)]
        keys += [(tags.setdefault(t, _bucket()), None) for t in r["tags"]]
        for b, _ in keys:
            b[r["status"]] += 1
    for b in [overall, *tags.values(), *eps.values(), *days.values()]:
        b["pass_rate"] = _rate(b)
        b["total"] = b["pass"] + b["fail"] + b["pending"]
    return {"tasks": len(results), "unscored_chat_tasks": unscored, "overall": overall, "by_tag": dict(sorted(tags.items())),
            "by_episode": dict(sorted(eps.items())), "by_day": dict(sorted(days.items())), "rubric_checks": rub,
            "note": "pass_rate = pass / (pass + fail); pending tasks await rubric grading"}


def render_summary_md(s, usage=None):
    def row(name, b):
        r = b["pass_rate"]
        return f"| {name} | {b['pass']} | {b['fail']} | {b['pending']} | {'-' if r is None else f'{r:.0%}'} |"
    head = "| | pass | fail | pending | pass rate |\n|---|---|---|---|---|"
    o = s["overall"]
    out = ["# Run summary", "", f"Tasks: {s['tasks']} ({s['unscored_chat_tasks']} unscored chat tasks). "
           f"Rubric checks: {s['rubric_checks']['pending']} pending, {s['rubric_checks']['pass']} pass, {s['rubric_checks']['fail']} fail.",
           "", head, row("**overall**", o)]
    for title, key in (("By tag", "by_tag"), ("By episode", "by_episode"), ("By day", "by_day")):
        out += ["", f"## {title}", "", head] + [row(k, b) for k, b in s[key].items()]
    if usage:
        out += ["", f"Estimated cost: ${usage.get('estimated_cost_usd', 0):.4f}"]
    return "\n".join(out) + "\n"


def write_summary(run_dir):
    run_dir = Path(run_dir)
    results = collect_results(run_dir)
    save_results(run_dir, results)
    s = build_summary(results)
    usage = rjson(run_dir / "usage.json") if (run_dir / "usage.json").exists() else None
    if usage:
        s["usage"] = usage
    wjson(run_dir / "summary.json", s)
    (run_dir / "summary.md").write_text(render_summary_md(s, usage))
    return s


# ---------------------------------------------------------------- main

def make_agent(args):
    if args.agent == "openai":
        return agents.OpenAIAgent(args.base_url, args.model, api_key=args.api_key, max_tokens=args.max_tokens,
                                  concurrency=args.concurrency)
    if args.agent == "claude":
        return agents.ClaudeBatchAgent(args.model, live=args.live, max_tokens=max(args.max_tokens, 8000),
                                       poll=args.poll, concurrency=args.concurrency)
    raise SystemExit("--agent scripted is for tests; use run_episodes() with a ScriptedAgent")


def run_episodes(episodes, agent, run_dir, memory="none", max_steps=25, resume=False, between_days_cmd=None,
                 days=None, model_name=None, base=None):
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    base = base or load_base()
    model_name = model_name or getattr(agent, "model", "unknown")
    states = [EpisodeState(e, run_dir, memory, base, resume) for e in episodes]
    if resume and (run_dir / "usage.json").exists():      # carry over spend from earlier sessions
        agent.usage.merge(rjson(run_dir / "usage.json").get("by_model", {}))
    n_days = max((len(s.days) for s in states), default=0)
    if days:
        n_days = min(n_days, days)
    for di in range(n_days):
        print(f"== day {di + 1}", flush=True)
        drivers = [DayDriver(s, di, max_steps, model_name) for s in states if di < len(s.days)]
        agent.run(drivers)
        for s in states:
            if di >= len(s.days):
                continue
            write_diary(run_dir, s, di, model_name)
            marker = run_dir / "hooks" / f"{s.id}_day{di + 1}.done"
            if between_days_cmd and not marker.exists():
                cmd = between_days_cmd.format(run_dir=str(run_dir), episode=s.id, day=di + 1)
                rc = subprocess.run(cmd, shell=True).returncode
                print(f"  hook {s.id} day{di + 1}: exit {rc}", flush=True)
                marker.parent.mkdir(parents=True, exist_ok=True)
                marker.write_text(str(rc))
        save_usage(run_dir, agent)
        write_summary(run_dir)
    return write_summary(run_dir)


def save_usage(run_dir, agent):
    live = getattr(agent, "live", False)
    wjson(Path(run_dir) / "usage.json", agent.usage.to_dict(batch=getattr(agent, "batch", False) and not live))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="bensweek.run")
    ap.add_argument("--agent", choices=["openai", "claude", "scripted"], default="openai")
    ap.add_argument("--base-url", default="http://127.0.0.1:8090/v1")
    ap.add_argument("--model", default=None)
    ap.add_argument("--api-key", default=None)
    ap.add_argument("--split", choices=["dev", "sealed"], default="dev")
    ap.add_argument("--i-am-running-the-final-v2-eval", action="store_true")
    ap.add_argument("--episodes", default=None, help="comma list, e.g. wk01,wk03")
    ap.add_argument("--memory", choices=MEMORY_MODES, default="none")
    ap.add_argument("--between-days-cmd", default=None, help='shell cmd with {run_dir} {episode} {day}')
    ap.add_argument("--out", default=None)
    ap.add_argument("--max-steps", type=int, default=25)
    ap.add_argument("--max-tokens", type=int, default=2048)
    ap.add_argument("--concurrency", type=int, default=2)
    ap.add_argument("--days", type=int, default=None, help="only run the first N days")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--live", action="store_true", help="claude: direct (non-batch) debugging path")
    ap.add_argument("--poll", type=int, default=25, help="claude: batch poll seconds")
    args = ap.parse_args(argv)
    if args.agent == "scripted":
        raise SystemExit("--agent scripted is only for tests")
    if args.model is None:
        args.model = "claude-sonnet-5-5" if args.agent == "claude" else "qwen36-fast"
    only = set(args.episodes.split(",")) if args.episodes else None
    eps = load_episodes(args.split, args.i_am_running_the_final_v2_eval, only)
    if not eps:
        raise SystemExit("no episodes found")
    run_id = f"{time.strftime('%Y%m%d-%H%M%S')}-{args.agent}-{re.sub(r'[^A-Za-z0-9._-]', '_', args.model)}"
    out = Path(args.out) if args.out else Path("runs") / run_id
    out.mkdir(parents=True, exist_ok=True)
    wjson(out / "config.json", {k: v for k, v in vars(args).items() if k != "api_key"})
    agent = make_agent(args)
    print(f"run dir: {out}  episodes: {[e['id'] for e in eps]}", flush=True)
    s = run_episodes(eps, agent, out, args.memory, args.max_steps, args.resume, args.between_days_cmd, args.days,
                     args.model)
    o = s["overall"]
    print(f"done: {o['pass']} pass / {o['fail']} fail / {o['pending']} pending; rubric pending {s['rubric_checks']['pending']}")
    if "usage" in s:
        print(f"estimated cost: ${s['usage']['estimated_cost_usd']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
