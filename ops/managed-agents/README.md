# Managed Agents for the project

Two Claude Managed Agents, paid from Ben's monthly API credit (not from his Claude plan):

| Agent | Model | Runs where | Does |
|---|---|---|---|
| `pc-operator` | Haiku 5.5, xhigh | Ben's Mac, through a self-hosted worker that reaches BensPC over `ssh benspc` | Checks the PC every 15 minutes, restarts jobs only as their job cards say, and runs PC jobs that threads send |
| `opus-reviewer` | Opus 5.5, xhigh | Anthropic's cloud sandbox, with the repo cloned read-only | Answers the outside-opinion prompts that CLAUDE.md describes, sent straight from a thread |

Each session has a hard spending cap: $0.50 per scheduled check, $1 per PC job, $3 per review (list price). A check that
finds nothing to do is about a cent (estimate); `ma.py cost` reports the real spend.

## One-time setup

Ben, in the [Claude Console](https://platform.claude.com):
1. Create an API key. Add it to this project's cloud environment as the environment variable
   `LEARNER_ANTHROPIC_API_KEY` (not as a network secret, so Claude Code's own login is untouched).
2. Workspace > Environments > New > Self-hosted, name `pc-worker`. Open it and click "Generate environment key".
   Keep the page open for step 3.
3. On the Mac, in Terminal, from the repo checkout: `bash ops/managed-agents/mac/setup.sh`. It installs the `ant`
   CLI, asks for the environment ID and key (hidden input, stored in the macOS Keychain), and starts the worker at login.
4. On GitHub, create a fine-grained token with read-only Contents access to `BenjaminHannan/learner`. Add it as the
   environment variable `LEARNER_GITHUB_RO_TOKEN`.

Then any new thread session (which picks up the two variables):

```sh
pip install anthropic pyyaml
python3 ops/managed-agents/ma.py setup --env-id env_...   # creates the agents and the paused 15-minute check
python3 ops/managed-agents/ma.py check-now                # one test check on the real PC
python3 ops/managed-agents/ma.py unpause                  # start the 15-minute schedule
```

Commit `ids.json` afterwards (it holds IDs only, no secrets). Rerun `setup` after editing an agent file; it updates the
agents in place and moves the schedule to the new version.

## Using it from a thread

```sh
python3 ops/managed-agents/ma.py status                          # latest PC report and how old it is
python3 ops/managed-agents/ma.py job "Write a job card for ..."  # hand a job to the PC operator
python3 ops/managed-agents/ma.py review reviews/my-prompt.md --attach /mnt/project-files/x/RESULT.json --out reviews/answer.md
python3 ops/managed-agents/ma.py cost --days 30
```

Reviews now go through the half-price batch path by default; see the next section.

The latest status is also on the `pc-status` branch (`pc-status.md`, plus `actions.md`, the log of every restart).

## Half-price batch jobs

Anything that can wait up to an hour or so goes through the Message Batches API at 50% of list price: outside-opinion
reviews, reading or summarising files, scoring. Live PC checks and PC jobs stay Managed Agents sessions.

```sh
# one request per prompt file; --attach files are shared by all requests; models: haiku (default), sonnet, opus, fable
python3 ops/managed-agents/ma.py batch submit q1.md q2.md --model sonnet --attach results.json --wait
python3 ops/managed-agents/ma.py batch status [BATCH_ID]         # one batch, or the 10 newest
python3 ops/managed-agents/ma.py batch collect BATCH_ID          # write the answers, print the real cost
python3 ops/managed-agents/ma.py review prompt.md --attach x.json --out reviews/answer.md   # Opus xhigh, half price
python3 ops/managed-agents/ma.py review prompt.md --repo         # old live session with the repo mounted
```

- The batch reviewer cannot browse the repo: attach what it needs (files are inlined in full), or use `review --repo`.
- Batches have no dollar cap, so `ma.py` checks a worst-case estimate (full prompt as cache writes plus all of
  `--max-tokens` as output) before submitting and refuses if one request is over `--cap-cents` (100; review 300).
- Answers go to `--out-dir` (`/mnt/project-files/api-batches`, else `ops/managed-agents/batches/`, git-ignored) with a
  `batch-<id>.json` manifest. Most batches finish within an hour; the limit is 24 hours and results are kept 29 days.
- Batch commands work as soon as `LEARNER_ANTHROPIC_API_KEY` is set, before any of the Mac setup.

## Job cards

The pc-operator acts on a failing job only when the job's card says how. The thread that starts a long PC job writes a
card from `job-card-template.md` (directly, or through `ma.py job`). A job without a card is only reported.

## Safety

- The worker runs as Ben's user on the Mac, so the agent's `bash` can do anything Ben's account can. The system prompt
  and job cards limit it: no deletes, no kills except a card's exact PID, no secrets, push only to `pc-status`.
- The API key never goes on the Mac; the worker holds only the environment key, which can serve this one queue.
- Anthropic's docs list Linux as the worker host. The `ant` CLI ships for macOS and the Mac is expected to work; if it
  does not, run the same worker in WSL on BensPC.
- To stop everything: `ma.py pause`, and on the Mac
  `launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.learner.pc-worker.plist`.
