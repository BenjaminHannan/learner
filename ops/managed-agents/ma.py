#!/usr/bin/env python3
"""Thread-side helper for the project's Managed Agents (see README.md in this folder).

Needs `pip install anthropic pyyaml` and the project environment variable
LEARNER_ANTHROPIC_API_KEY (a separate name, so Claude Code's own login is untouched).
The reviewer also needs LEARNER_GITHUB_RO_TOKEN (read-only access to the repo).

    python3 ops/managed-agents/ma.py status                 # latest BensPC check
    python3 ops/managed-agents/ma.py job "tail the G1 log"  # hand a job to the PC operator
    python3 ops/managed-agents/ma.py review prompt.md --attach results.json
    python3 ops/managed-agents/ma.py cost --days 30
"""
import argparse
import datetime as dt
import json
import os
import re
import sys
import time
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
IDS_PATH = HERE / "ids.json"
ET = ZoneInfo("America/New_York")
REPO_URL = "https://github.com/BenjaminHannan/learner"
CHECK_SCHEDULE = {"type": "cron", "expression": "*/15 * * * *", "timezone": "America/New_York"}
BUDGET_CENTS = {"check": 50, "job": 100, "review": 300}
STALE_MINUTES = 45


def client():
    key = os.environ.get("LEARNER_ANTHROPIC_API_KEY")
    if not key:
        sys.exit("LEARNER_ANTHROPIC_API_KEY is not set. Ben adds it as a project environment variable; "
                 "a new session picks it up.")
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)  # never mix in another credential
    import anthropic
    return anthropic.Anthropic(api_key=key, base_url="https://api.anthropic.com")


def load_ids():
    if IDS_PATH.exists():
        return json.loads(IDS_PATH.read_text())
    return {"agents": {}}


def save_ids(ids):
    IDS_PATH.write_text(json.dumps(ids, indent=2) + "\n")


def need(ids, *keys):
    for key in keys:
        value = ids
        for part in key.split("."):
            value = value.get(part) if isinstance(value, dict) else None
        if not value:
            sys.exit(f"{key} is missing from {IDS_PATH.name}; run `ma.py setup --env-id env_...` first.")


def budget(cents):
    return {"type": "limit", "max_list_cost": {"amount": str(cents), "currency": "USD"}}


def et(when):
    return when.astimezone(ET).strftime("%Y-%m-%d %I:%M %p ET")


def message(text):
    return {"type": "user.message", "content": [{"type": "text", "text": text}]}


def load_agent(name):
    import yaml
    text = (HERE / "agents" / f"{name}.md").read_text()
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    spec = yaml.safe_load(match.group(1))
    spec["system"] = match.group(2).strip()
    return {k: spec[k] for k in ("name", "description", "model", "system", "tools") if k in spec}


def agent_ref(agent):
    return {"type": "agent", "id": agent.id, "version": agent.version}


def agent_texts(c, session_id):
    texts = []
    for event in c.beta.sessions.events.list(session_id=session_id, order="asc", types=["agent.message"]):
        text = "".join(getattr(block, "text", "") for block in event.content)
        if text.strip():
            texts.append(text)
    return texts


def wait_for_turn(c, session_id, minutes):
    """Poll until the session's first turn ends. Returns the session, or None on timeout."""
    deadline = time.monotonic() + minutes * 60
    seen_running = False
    while time.monotonic() < deadline:
        session = c.beta.sessions.retrieve(session_id=session_id)
        if session.status == "running":
            seen_running = True
        elif session.status == "terminated":
            return session
        elif session.status == "idle" and (seen_running or agent_texts(c, session_id)):
            return session
        time.sleep(15)
    return None


def stop_reason(c, session_id):
    events = c.beta.sessions.events.list(session_id=session_id, order="desc", limit=1,
                                         types=["session.status_idle", "session.status_terminated"]).data
    if events and getattr(events[0], "stop_reason", None):
        return events[0].stop_reason.type
    return events[0].type if events else "unknown"


def cost_text(session):
    cost = session.usage.list_cost if session.usage else None
    return f"${int(cost.amount) / 100:.2f}" if cost else "unknown"


def finish(c, session_id, minutes, out=None, all_messages=False):
    session = wait_for_turn(c, session_id, minutes)
    if session is None:
        print(f"Still not finished after {minutes} min. If it never started, the Mac or its worker is offline. "
              f"Check later with: ma.py result {session_id}")
        return 1
    texts = agent_texts(c, session_id)
    answer = "\n\n".join(texts) if all_messages else (texts[-1] if texts else "(no reply)")
    if out:
        Path(out).write_text(answer + "\n")
        print(f"Answer written to {out}")
    else:
        print(answer)
    print(f"\n[session {session_id}: {session.status}, {stop_reason(c, session_id)}, list cost {cost_text(session)}]")
    return 0


def cmd_setup(args):
    c = client()
    ids = load_ids()
    if args.env_id:
        ids["pc_env"] = args.env_id
    need(ids, "pc_env")
    agents = {}
    for name in ("pc-operator", "opus-reviewer"):
        fields = load_agent(name)
        if ids["agents"].get(name):
            agents[name] = c.beta.agents.update(ids["agents"][name], **fields)
        else:
            agents[name] = c.beta.agents.create(**fields)
        ids["agents"][name] = agents[name].id
        print(f"{name}: {agents[name].id} version {agents[name].version}")
    if not ids.get("reviewer_env"):
        env = c.beta.environments.create(
            name="learner-reviewer",
            config={"type": "cloud", "networking": {"type": "limited", "allow_package_managers": True}})
        ids["reviewer_env"] = env.id
    print(f"reviewer environment: {ids['reviewer_env']}")
    deployment = dict(
        name="benspc-check-15min",
        agent=agent_ref(agents["pc-operator"]),
        environment_id=ids["pc_env"],
        schedule=CHECK_SCHEDULE,
        initial_events=[message("SCHEDULED CHECK")],
        budget=budget(BUDGET_CENTS["check"]),
    )
    if ids.get("deployment"):
        c.beta.deployments.update(ids["deployment"], **deployment)
    else:
        created = c.beta.deployments.create(**deployment)
        ids["deployment"] = created.id
        c.beta.deployments.pause(created.id)
        print("New deployment created paused. Test it with `ma.py check-now`, then `ma.py unpause`.")
    print(f"deployment: {ids['deployment']}")
    save_ids(ids)
    return 0


def cmd_check_now(args):
    c = client()
    ids = load_ids()
    need(ids, "deployment")
    run = c.beta.deployments.run(ids["deployment"])
    if not run.session_id:
        print(f"Run failed to start: {run.error.type if run.error else 'unknown'}")
        return 1
    print(f"SESSION {run.session_id}")
    return finish(c, run.session_id, args.wait_min)


def cmd_pause(args, pause=True):
    c = client()
    ids = load_ids()
    need(ids, "deployment")
    (c.beta.deployments.pause if pause else c.beta.deployments.unpause)(ids["deployment"])
    print("paused" if pause else "unpaused")
    return 0


def cmd_status(args):
    c = client()
    ids = load_ids()
    need(ids, "deployment")
    now = dt.datetime.now(dt.timezone.utc)
    for session in c.beta.sessions.list(deployment_id=ids["deployment"], order="desc", limit=10).data:
        texts = agent_texts(c, session.id)
        if texts and not texts[-1].startswith("SKIP"):
            age = (now - session.created_at).total_seconds() / 60
            print(f"Last BensPC report, {et(session.created_at)} ({age:.0f} min ago):\n{texts[-1]}")
            if age > STALE_MINUTES:
                print(f"\nWARNING: no report for {age:.0f} min. The Mac, its worker or BensPC may be offline.")
            return 0
    print("No finished check found in the last 10 runs. The Mac or its worker may be offline.")
    return 1


def cmd_job(args):
    c = client()
    ids = load_ids()
    need(ids, "agents.pc-operator", "pc_env")
    text = sys.stdin.read() if args.text == "-" else args.text
    session = c.beta.sessions.create(
        agent=ids["agents"]["pc-operator"],
        environment_id=ids["pc_env"],
        title=("JOB: " + text.strip().splitlines()[0])[:80],
        budget=budget(args.budget_cents),
        initial_events=[message("JOB from a project thread:\n" + text)],
    )
    print(f"SESSION {session.id}")
    if args.no_wait:
        return 0
    return finish(c, session.id, args.wait_min, args.out)


def cmd_result(args):
    c = client()
    return finish(c, args.session_id, 0.05, args.out, args.all)


def cmd_review(args):
    c = client()
    ids = load_ids()
    need(ids, "agents.opus-reviewer", "reviewer_env")
    token = os.environ.get("LEARNER_GITHUB_RO_TOKEN")
    if not token:
        sys.exit("LEARNER_GITHUB_RO_TOKEN is not set (a read-only GitHub token for the repo).")
    prompt = Path(args.prompt).read_text()
    resources = [{
        "type": "github_repository", "url": REPO_URL, "authorization_token": token,
        "mount_path": "/workspace/learner", "checkout": {"type": "branch", "name": args.ref},
    }]
    mounted = []
    for i, path in enumerate(args.attach):
        name = Path(path).name
        if name in mounted:
            name = f"{i}-{name}"
        with open(path, "rb") as handle:
            uploaded = c.files.upload(file=(name, handle))
        resources.append({"type": "file", "file_id": uploaded.id, "mount_path": "/" + name})
        mounted.append(name)
    where = ", ".join("/mnt/session/uploads/" + n for n in mounted) or "none"
    note = f"\n\n---\nRepository: /workspace/learner (branch {args.ref}). Attached files: {where}."
    session = c.beta.sessions.create(
        agent=ids["agents"]["opus-reviewer"],
        environment_id=ids["reviewer_env"],
        title=("Review: " + Path(args.prompt).stem)[:80],
        budget=budget(args.budget_cents),
        resources=resources,
        initial_events=[message(prompt + note)],
    )
    print(f"SESSION {session.id}")
    if args.no_wait:
        return 0
    return finish(c, session.id, args.wait_min, args.out)


def cmd_cost(args):
    c = client()
    ids = load_ids()
    since = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=args.days)).isoformat()
    total = 0
    for name, agent_id in ids.get("agents", {}).items():
        cents, count = 0, 0
        for session in c.beta.sessions.list(agent_id=agent_id, created_at_gte=since, limit=100):
            cost = session.usage.list_cost if session.usage else None
            if cost:
                cents += int(cost.amount)
            count += 1
        total += cents
        print(f"{name}: {count} sessions, ${cents / 100:.2f}")
    print(f"total, last {args.days} days: ${total / 100:.2f} (list price)")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("setup", help="create or update the agents, reviewer environment and 15-minute check")
    p.add_argument("--env-id", help="the self-hosted environment made in the Console (env_...)")
    p.set_defaults(func=cmd_setup)

    p = sub.add_parser("check-now", help="run the BensPC check once and print its report")
    p.add_argument("--wait-min", type=float, default=15)
    p.set_defaults(func=cmd_check_now)

    sub.add_parser("pause", help="pause the 15-minute check").set_defaults(func=lambda a: cmd_pause(a, True))
    sub.add_parser("unpause", help="resume the 15-minute check").set_defaults(func=lambda a: cmd_pause(a, False))
    sub.add_parser("status", help="print the latest BensPC report").set_defaults(func=cmd_status)

    p = sub.add_parser("job", help="hand a job to the PC operator (text, or - for stdin)")
    p.add_argument("text")
    p.add_argument("--budget-cents", type=int, default=BUDGET_CENTS["job"])
    p.add_argument("--wait-min", type=float, default=30)
    p.add_argument("--no-wait", action="store_true")
    p.add_argument("--out")
    p.set_defaults(func=cmd_job)

    p = sub.add_parser("result", help="print a session's reply")
    p.add_argument("session_id")
    p.add_argument("--all", action="store_true", help="every message, not just the last")
    p.add_argument("--out")
    p.set_defaults(func=cmd_result)

    p = sub.add_parser("review", help="ask the Opus reviewer (prompt file; repo is mounted read-only)")
    p.add_argument("prompt")
    p.add_argument("--attach", nargs="*", default=[], help="files to mount under /mnt/session/uploads/")
    p.add_argument("--ref", default="main", help="branch to check out")
    p.add_argument("--budget-cents", type=int, default=BUDGET_CENTS["review"])
    p.add_argument("--wait-min", type=float, default=60)
    p.add_argument("--no-wait", action="store_true")
    p.add_argument("--out")
    p.set_defaults(func=cmd_review)

    p = sub.add_parser("cost", help="list-price spend per agent")
    p.add_argument("--days", type=int, default=30)
    p.set_defaults(func=cmd_cost)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
