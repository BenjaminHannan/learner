#!/usr/bin/env python3
"""Thread-side helper for the project's Managed Agents (see README.md in this folder).

Needs `pip install anthropic pyyaml` and the project environment variable
LEARNER_ANTHROPIC_API_KEY (a separate name, so Claude Code's own login is untouched).
Only `review --repo` also needs LEARNER_GITHUB_RO_TOKEN (read-only access to the repo) and ids.json.

    python3 ops/managed-agents/ma.py status                 # latest BensPC check
    python3 ops/managed-agents/ma.py job "tail the G1 log"  # hand a job to the PC operator
    python3 ops/managed-agents/ma.py review prompt.md --attach results.json   # half-price batch, no repo, waits
    python3 ops/managed-agents/ma.py review prompt.md --no-wait               # submit, collect later
    python3 ops/managed-agents/ma.py review prompt.md --repo                  # live session, repo mounted
    python3 ops/managed-agents/ma.py batch submit q1.md q2.md --model sonnet --attach data.json --wait
    python3 ops/managed-agents/ma.py batch status [BATCH_ID]
    python3 ops/managed-agents/ma.py batch collect BATCH_ID
    python3 ops/managed-agents/ma.py cost --days 30

Anything that can wait up to an hour or so goes through the Message Batches API at 50% of list price
(`batch ...` and the default `review`, which has no repo and a per-request cap). Live PC checks and PC jobs stay
Managed Agents sessions, and so does `review --repo`. Batch commands need only LEARNER_ANTHROPIC_API_KEY (no ids.json,
Mac worker or GitHub token). `review` and `batch submit --wait` block up to --minutes (60): run them in the background
or use --no-wait and collect later.
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
CHECK_SCHEDULE = {"type": "cron", "expression": "*/30 * * * *", "timezone": "America/New_York"}
BUDGET_CENTS = {"check": 50, "job": 100, "review": 300}
TOTAL_CAP_CENTS = {"batch": 500, "review": 300}  # worst case for a whole batch
MAX_BODY_BYTES = 256 * 1024 * 1024  # Message Batches request size limit
STALE_MINUTES = 45
POLL_SECONDS = 30
MODELS = {"haiku": "claude-haiku-5-5", "sonnet": "claude-sonnet-5-5",
          "opus": "claude-opus-5-5", "fable": "claude-fable-5-1"}
# list price, USD per million tokens: input, output, cache read
PRICES = {"claude-haiku-5-5": (0.10, 0.50, 0.01), "claude-sonnet-5-5": (2.00, 10.00, 0.20),
          "claude-opus-5-5": (4.00, 20.00, 0.20), "claude-fable-5-1": (10.00, 50.00, 0.25)}
HAIKU_LONG = (0.50, 2.50, 0.05)  # Haiku prompts over 100K input tokens
LONG_PROMPT = 100_000
BATCH_DISCOUNT = 0.5
NO_REPO_NOTE = ("NOTE: in this mode you have NO repository and NO tools. Rely only on the prompt and the attached "
                "files below, and say what you could not check because of that.")


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


# ---- Message Batches API (half price) ----

def model_id(name):
    name = MODELS.get(name, name)
    if name not in PRICES:
        sys.exit(f"Unknown model {name!r}. Use {', '.join(MODELS)} or one of: {', '.join(PRICES)}.")
    return name


def batch_cost(model, input_tokens=0, cache_write=0, cache_read=0, output=0):
    """Dollars at batch price (50% of list) from token counts."""
    price_in, price_out, price_read = PRICES[model]
    if model == "claude-haiku-5-5" and input_tokens + cache_write + cache_read > LONG_PROMPT:
        price_in, price_out, price_read = HAIKU_LONG
    list_cost = input_tokens * price_in + cache_write * price_in * 1.25 + cache_read * price_read + output * price_out
    return BATCH_DISCOUNT * list_cost / 1e6


def usage_cost(model, usage):
    n = lambda name: getattr(usage, name, None) or 0
    return batch_cost(model, n("input_tokens"), n("cache_creation_input_tokens"),
                      n("cache_read_input_tokens"), n("output_tokens"))


def default_out_dir():
    shared = Path("/mnt/project-files")
    return shared / "api-batches" if shared.exists() else HERE / "batches"


def make_custom_ids(stems):
    seen, ids = set(), []
    for stem in stems:
        base = re.sub(r"[^a-zA-Z0-9_-]", "-", stem)[:64] or "request"
        cid, n = base, 1
        while cid in seen:
            n += 1
            suffix = f"-{n}"
            cid = base[:64 - len(suffix)] + suffix
        seen.add(cid)
        ids.append(cid)
    return ids


def read_text_file(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except UnicodeDecodeError:
        sys.exit(f"{path} is not valid UTF-8; attach text files only.")
    except OSError as err:
        sys.exit(f"Cannot read {path}: {err.strerror}")


def system_blocks(system_text, attach):
    """Optional system text, then all attachments as one cached block. Files are read in full."""
    blocks = []
    if system_text:
        blocks.append({"type": "text", "text": system_text})
    if attach:
        files = "\n".join(f'<file path="{path}">\n{read_text_file(path)}\n</file>' for path in attach)
        blocks.append({"type": "text", "text": files, "cache_control": {"type": "ephemeral"}})
    return blocks


def reviewer_body():
    """The opus-reviewer prompt without the paragraph about the cloned repo and uploads (not true in batch mode)."""
    paragraphs = load_agent("opus-reviewer")["system"].split("\n\n")
    return "\n\n".join(p for p in paragraphs if not p.startswith("The repository is cloned"))


def read_prompts(paths):
    if paths.count("-") > 1:
        sys.exit("stdin ('-') can be used for one prompt only.")
    prompts = [("stdin", sys.stdin.read(), "-") if p == "-" else (Path(p).stem, read_text_file(p), p) for p in paths]
    for _, text, path in prompts:
        if not text.strip():
            sys.exit(f"{path} is empty; nothing to send.")
    return prompts


def submit_batch(c, prompts, model, effort, max_tokens, system, cap_cents, total_cap_cents, out_dir,
                 out_paths=None, lower_tokens_flag=True):
    """prompts: [(stem, text, path)]. Checks the worst-case caps and the size limit, submits one batch, writes the manifest."""
    cids = make_custom_ids([stem for stem, _, _ in prompts])
    requests, worst = [], {}
    for cid, (_, text, _) in zip(cids, prompts):
        params = {"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": text}],
                  "output_config": {"effort": effort}}
        if system:
            params["system"] = system
        count_args = {k: params[k] for k in ("model", "system", "messages") if k in params}
        tokens = c.messages.count_tokens(**count_args).input_tokens
        worst[cid] = batch_cost(model, cache_write=tokens, output=max_tokens) * 100
        requests.append({"custom_id": cid, "params": params})
    shorten = "Shorten the attachments, " + ("lower --max-tokens, " if lower_tokens_flag else "")
    over = [(cid, cents) for cid, cents in worst.items() if cents > cap_cents]
    for cid, cents in over:
        print(f"REFUSED {cid}: worst case {cents:.1f} cents is over the cap of {cap_cents} cents "
              f"by {cents - cap_cents:.1f}.")
    if over:
        print(f"Nothing submitted. {shorten}or raise --cap-cents.")
        return None
    total = sum(worst.values())
    if total > total_cap_cents:
        print(f"REFUSED: worst case for the whole batch is {total:.1f} cents, over --max-total-cents "
              f"{total_cap_cents} by {total - total_cap_cents:.1f}.")
        print(f"Nothing submitted. {shorten}send fewer prompts, or raise --max-total-cents.")
        return None
    size = len(json.dumps({"requests": requests}).encode())
    if size > MAX_BODY_BYTES:
        print(f"REFUSED: the request body is {size / 1024 / 1024:.1f} MB, over the {MAX_BODY_BYTES // 1024 // 1024} MB "
              f"batch limit. Nothing submitted. Split the prompts or shorten the attachments.")
        return None
    out_dir = Path(out_dir)
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
    except OSError as err:
        sys.exit(f"Cannot create {out_dir}: {err.strerror}. Nothing submitted; pass --out-dir.")
    if not os.access(out_dir, os.W_OK):
        sys.exit(f"{out_dir} is not writable. Nothing submitted; pass --out-dir.")
    print(f"{len(requests)} request(s) on {model}, worst case ${total / 100:.2f} (batch price).")
    batch = c.messages.batches.create(requests=requests)
    print(f"BATCH {batch.id}")
    print(f"Collect with: {collect_command(batch.id, out_dir)}")
    manifest = {
        "id": batch.id, "model": model, "effort": effort, "max_tokens": max_tokens,
        "created": et(getattr(batch, "created_at", None) or dt.datetime.now(dt.timezone.utc)),
        "worst_case_cents": round(total, 2),
        "requests": {cid: {"prompt": path, "out": str((out_paths or {}).get(cid) or out_dir / f"{cid}.md")}
                     for cid, (_, _, path) in zip(cids, prompts)},
    }
    try:
        (out_dir / f"batch-{batch.id}.json").write_text(json.dumps(manifest, indent=2) + "\n")
    except OSError as err:
        print(f"WARNING: could not write the manifest ({err.strerror}). The batch IS submitted: {batch.id}. "
              f"Collect with: {collect_command(batch.id, out_dir)}")
    return batch.id


def collect_command(batch_id, out_dir):
    return f"python3 ops/managed-agents/ma.py batch collect {batch_id} --out-dir {out_dir}"


def wait_ended(c, batch_id, minutes):
    """Poll until the batch ends. Network errors, 429s and 5xx are retried until the deadline."""
    import anthropic
    deadline = time.monotonic() + minutes * 60
    while True:
        try:
            if c.messages.batches.retrieve(batch_id).processing_status == "ended":
                return True
        except (anthropic.APIConnectionError, anthropic.APIStatusError) as err:
            status = getattr(err, "status_code", None)
            if status is not None and status != 429 and status < 500:
                raise  # a bad key or unknown batch will not fix itself
            print(f"Could not check {batch_id} ({type(err).__name__}); will retry.")
        if time.monotonic() >= deadline:
            return False
        time.sleep(POLL_SECONDS)


def submit_and_maybe_wait(c, prompts, args, system, out_paths=None):
    out_dir = args.out_dir or default_out_dir()
    batch_id = submit_batch(c, prompts, model_id(args.model), args.effort, args.max_tokens, system,
                            args.cap_cents, args.max_total_cents, out_dir, out_paths,
                            lower_tokens_flag=not getattr(args, "no_max_tokens_flag", False))
    if batch_id is None:
        return 1
    command = collect_command(batch_id, out_dir)
    if not getattr(args, "wait", True):
        return 0
    if wait_ended(c, batch_id, args.minutes):
        return collect(c, batch_id, out_dir)
    print(f"Not finished after {args.minutes:g} min (batches finish within 24 h). Collect later with: {command}")
    return 0


def cmd_batch_submit(args):
    prompts = read_prompts(args.prompts)
    c = client()
    system = system_blocks(read_text_file(args.system).strip() if args.system else None, args.attach)
    return submit_and_maybe_wait(c, prompts, args, system)


def counts_text(batch):
    rc = batch.request_counts
    return (f"{rc.processing} processing, {rc.succeeded} succeeded, {rc.errored} errored, "
            f"{rc.canceled} canceled, {rc.expired} expired")


def when_text(value):
    return et(value) if value else "-"


def cmd_batch_status(args):
    c = client()
    if args.batch_id:
        batch = c.messages.batches.retrieve(args.batch_id)
        print(f"{batch.id}: {batch.processing_status}; {counts_text(batch)}")
        print(f"created {when_text(batch.created_at)}, ended {when_text(batch.ended_at)}")
        return 0
    batches = []
    for batch in c.messages.batches.list(limit=10):
        batches.append(batch)
        if len(batches) >= 10:
            break
    for batch in batches:
        print(f"{batch.id}  {batch.processing_status}  {when_text(batch.created_at)}  {counts_text(batch)}")
    if not batches:
        print("No batches yet.")
    return 0


def find_manifest(batch_id, out_dir):
    path = Path(out_dir) / f"batch-{batch_id}.json"
    return path, (json.loads(path.read_text()) if path.exists() else None)


def result_text(message):
    return "".join(b.text for b in message.content if getattr(b, "type", None) == "text")


def collect(c, batch_id, out_dir):
    batch = c.messages.batches.retrieve(batch_id)
    if batch.processing_status != "ended":
        print(f"{batch_id}: {batch.processing_status}; {counts_text(batch)}. Nothing written yet.")
        return 0
    out_dir = Path(out_dir)
    manifest_path, manifest = find_manifest(batch_id, out_dir)
    if manifest is None:
        print(f"WARNING: No manifest at {manifest_path}: writing to {out_dir} (any review --out was not applied).")
    outs = (manifest or {}).get("requests", {})
    manifest_model = (manifest or {}).get("model")
    total, unpriced = 0.0, 0
    for item in c.messages.batches.results(batch_id):  # any order; keyed by custom_id
        cid, result = item.custom_id, item.result
        if result.type != "succeeded":
            error = getattr(getattr(result, "error", None), "type", None)
            detail = getattr(getattr(getattr(result, "error", None), "error", None), "type", None)
            print(f"{cid}: {result.type}" + (f" ({detail or error})" if detail or error else ""))
            continue
        msg = result.message
        out = Path(outs.get(cid, {}).get("out") or out_dir / f"{cid}.md")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(result_text(msg) + "\n")
        priced = msg.model if msg.model in PRICES else manifest_model if manifest_model in PRICES else None
        if priced:
            cost = usage_cost(priced, msg.usage)
            total += cost
            print(f"{cid}: {out}  (${cost:.4f})")
        else:
            unpriced += 1
            print(f"{cid}: {out}  (not priced)")
            print(f"WARNING {cid}: unknown model {msg.model!r}; its cost is not in the total.")
        if msg.stop_reason in ("refusal", "max_tokens"):
            print(f"WARNING {cid}: stopped with {msg.stop_reason}; the answer may be missing or cut off.")
    print(f"total actual cost ${total:.4f} (batch price)"
          + (f", {unpriced} result(s) with an unknown model not priced" if unpriced else ""))
    if manifest is not None:
        manifest["collected"] = et(dt.datetime.now(dt.timezone.utc))
        manifest["cost_cents"] = round(total * 100, 4)
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    return 0


def cmd_batch_collect(args):
    return collect(client(), args.batch_id, args.out_dir or default_out_dir())


def batches_cost(c, since):
    """(count, running, dollars, unpriced, expired) for batches created at or after `since`."""
    import anthropic
    count = running = unpriced = expired = 0
    dollars = 0.0
    for batch in c.messages.batches.list(limit=100):
        if batch.created_at < since:
            break
        count += 1
        if batch.processing_status != "ended":
            running += 1
            continue
        if getattr(batch, "archived_at", None):  # results are kept 29 days
            expired += 1
            continue
        batch_dollars = batch_unpriced = 0
        try:
            for item in c.messages.batches.results(batch.id):
                if item.result.type != "succeeded":
                    continue
                msg = item.result.message
                if msg.model in PRICES:
                    batch_dollars += usage_cost(msg.model, msg.usage)
                else:
                    batch_unpriced += 1
        except anthropic.AnthropicError:  # no results_url, or the results are gone
            expired += 1
            continue
        dollars += batch_dollars
        unpriced += batch_unpriced
    return count, running, dollars, unpriced, expired


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
        name="benspc-check-30min",
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
    if args.repo:
        return cmd_review_repo(args)
    prompts = read_prompts([args.prompt])
    c = client()
    system = system_blocks(NO_REPO_NOTE + "\n\n" + reviewer_body(), args.attach)
    args.model, args.effort, args.max_tokens, args.out_dir = "opus", "xhigh", 64000, None
    args.wait = not args.no_wait
    args.no_max_tokens_flag = True  # review has no --max-tokens option
    out_paths = {make_custom_ids([prompts[0][0]])[0]: str(Path(args.out).resolve())} if args.out else None
    return submit_and_maybe_wait(c, prompts, args, system, out_paths)


def cmd_review_repo(args):
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
    return finish(c, session.id, args.minutes, args.out)


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
    count, running, dollars, unpriced, expired = batches_cost(
        c, dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=args.days))
    print(f"batches: {count} created, ${dollars:.2f} actual (batch price), {running} still running"
          + (f", {expired} with results expired (not counted)" if expired else "")
          + (f", {unpriced} results with an unknown model not priced" if unpriced else ""))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("setup", help="create or update the agents, reviewer environment and 30-minute check")
    p.add_argument("--env-id", help="the self-hosted environment made in the Console (env_...)")
    p.set_defaults(func=cmd_setup)

    p = sub.add_parser("check-now", help="run the BensPC check once and print its report")
    p.add_argument("--wait-min", type=float, default=15)
    p.set_defaults(func=cmd_check_now)

    sub.add_parser("pause", help="pause the 30-minute check").set_defaults(func=lambda a: cmd_pause(a, True))
    sub.add_parser("unpause", help="resume the 30-minute check").set_defaults(func=lambda a: cmd_pause(a, False))
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

    p = sub.add_parser("review", help="ask the Opus reviewer: half-price batch with no repo by default; "
                                      "--repo for a live session with the repo (needs ids.json and LEARNER_GITHUB_RO_TOKEN)")
    p.add_argument("prompt")
    p.add_argument("--attach", nargs="*", action="extend", default=[],
                   help="files inlined in the prompt (with --repo: mounted under /mnt/session/uploads/)")
    p.add_argument("--repo", action="store_true", help="live Managed Agents session with the repo mounted read-only "
                                                       "(not a batch; needs ids.json and LEARNER_GITHUB_RO_TOKEN)")
    p.add_argument("--ref", default="main", help="branch to check out (--repo)")
    p.add_argument("--budget-cents", type=int, default=BUDGET_CENTS["review"], help="session cap (--repo)")
    p.add_argument("--cap-cents", type=int, default=300, help="worst-case cost cap for the request (batch mode)")
    p.add_argument("--max-total-cents", type=int, default=TOTAL_CAP_CENTS["review"],
                   help="worst-case cost cap for the whole batch (batch mode)")
    p.add_argument("--minutes", "--wait-min", dest="minutes", type=float, default=60,
                   help="block up to this many minutes waiting for the answer (default 60)")
    p.add_argument("--no-wait", action="store_true", help="submit and return at once; collect later with the printed "
                                                          "`batch collect` command (--repo: do not wait for the session)")
    p.add_argument("--out", help="file for the answer (batch mode: stored as an absolute path in the manifest)")
    p.set_defaults(func=cmd_review)

    b = sub.add_parser("batch", help="half-price Message Batches API jobs").add_subparsers(dest="batch_command", required=True)
    p = b.add_parser("submit", help="one request per prompt file (or - for stdin)")
    p.add_argument("prompts", nargs="+", metavar="PROMPT")
    p.add_argument("--model", default="haiku", help="haiku, sonnet, opus, fable or a full claude-* id")
    p.add_argument("--effort", default="xhigh", choices=["low", "medium", "high", "xhigh", "max"])
    p.add_argument("--max-tokens", type=int, default=32000)
    p.add_argument("--attach", action="append", default=[], metavar="FILE",
                   help="text file inlined for all requests; repeatable (one file per --attach)")
    p.add_argument("--system", metavar="FILE", help="extra system text")
    p.add_argument("--out-dir", help="where answers and the batch manifest go (default: shared folder, else batches/)")
    p.add_argument("--cap-cents", type=int, default=100, help="worst-case cost cap per request")
    p.add_argument("--max-total-cents", type=int, default=TOTAL_CAP_CENTS["batch"],
                   help="worst-case cost cap for the whole batch")
    p.add_argument("--wait", action="store_true",
                   help="poll until done, then collect (blocks up to --minutes); default is submit and return")
    p.add_argument("--minutes", type=float, default=60, help="with --wait: give up waiting after this many minutes (default 60)")
    p.set_defaults(func=cmd_batch_submit)
    p = b.add_parser("status", help="one batch, or the 10 newest")
    p.add_argument("batch_id", nargs="?")
    p.set_defaults(func=cmd_batch_status)
    p = b.add_parser("collect", help="write the answers of an ended batch and print the real cost")
    p.add_argument("batch_id")
    p.add_argument("--out-dir")
    p.set_defaults(func=cmd_batch_collect)

    p = sub.add_parser("cost", help="spend per agent (list price) and batches (batch price)")
    p.add_argument("--days", type=int, default=30)
    p.set_defaults(func=cmd_cost)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
