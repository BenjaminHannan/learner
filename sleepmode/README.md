# Sleep Mode

While you are away, your assistant can use the Mac to get smarter. You click **Sleep Mode** on the Desktop, it trains for as long as the Mac is free (even for days), and when you click **Wake Up** it stops and leaves you a short morning summary.

## What happens

- **Sleep**: it learns from your past chats (the "diary") using a small LoRA training run. After each hour it takes a quiz on chats it never trained on, so it can tell whether it is still improving.
- **Practice**: when the quiz score stops going up, it looks at what you use the assistant for (say, spreadsheets), reads tips, and practises in a locked sandbox where an automatic checker marks every answer. The good attempts become new training material. Then it goes back to sleep and learns from them.
- **Every hour** it checks your mail and calendar and tells you if something needs you. See "Read-only promise".
- **Wake**: it stops by itself if you click Wake Up, or if you start the assistant (the file `ASSISTANT_RUNNING` appears). It also pauses if `PAUSE_OTHERS` exists or the Mac runs low on memory.

## Use it

1. Once, in Terminal: `bash ~/learner/sleepmode/install_mac.sh` (path to wherever the repo is). It puts two files on your Desktop.
2. Double-click **Sleep Mode.command** to start (it first stops the assistant to free memory).
3. Double-click **Wake Up.command** to stop. It prints the summary.

Terminal versions (with `PYTHONPATH` pointing at the folder that contains `sleepmode`):

```
python -m sleepmode start [--fake] [--foreground]   # --fake = demo with a pretend trainer
python -m sleepmode status
python -m sleepmode wake
python -m sleepmode summary
python -m sleepmode checkin     # one check-in now, prints what it saw
```

The first time it reads Mail or Calendar, macOS asks "allow automation?". Say yes.

## Where things are

Everything lives in `~/learner-ops/sleepmode/` (set `SLEEPMODE_HOME` to move it):

| File | What it is |
| --- | --- |
| `summary.md` | the morning summary |
| `status.json` | what it is doing right now |
| `events.jsonl` | a log line for every event |
| `inbox.md` | things that needed you, newest first |
| `sleepmode.log` | text output of the background process |
| `config.json` | your settings (optional) |
| `practice/` | practice results and tips |
| `worker/` | the trainer's adapters and quiz |

## Read-only promise

Sleep Mode only reads your mail and calendar. It never sends, deletes, moves, or marks anything. The AppleScript only uses `get`-style reads, and the optional IMAP scan opens the mailbox in read-only mode (`EXAMINE`). Practice runs only on made-up files inside a throwaway folder with no network, never your real files. The only things it sends out are the optional `ntfy` phone push (off unless you set a topic, and it would send mail subjects to ntfy.sh) and, if you turn on web research, search requests for tips.

## Settings (`config.json`)

Only list what you want to change. Examples:

```json
{
  "vip_senders": ["mom@example.com", "Mr. Phipps", "college"],
  "urgent_words": ["urgent", "deadline", "due", "interview"],
  "hour_s": 3600,
  "ntfy_topic": "",
  "mlx_model": "mlx-community/Qwen2.5-1.5B-Instruct-4bit"
}
```

- **Email VIPs**: `vip_senders` are matched against the sender name and address (case-insensitive, partial match). A mail from a VIP always notifies you. A mail with an `urgent_words` hit in the subject or start of the text notifies you too. A calendar event starting within `event_soon_h` (default 2) hours does as well. Each item notifies once.
- **Not using Mail.app?** Set `imap_host`, `imap_user`, and put the password in an environment variable named by `imap_password_env`.
- Other useful keys: `mail_lookback_h`, `calendar_ahead_h`, `plateau_min_gain_per_hour`, `min_sleep_hours`, `practice_model_url`.

## Plug in a different sleep trainer

A trainer is any command that follows this contract. The scheduler runs it once per hour with these environment variables:

- `SLEEPMODE_BUDGET_S`: seconds it may use
- `SLEEPMODE_OUT`: path of a JSON file to write when done: `{"quiz": 61.2, "steps": 400}` (`quiz` is a number where higher is better, or `null`)
- `SLEEPMODE_PRACTICE`: practice data files, joined with `:`
- `SLEEPMODE_WORKDIR`: a folder it may keep files in between runs

It should save its progress and exit when it gets SIGTERM (that is how Wake works). In Python, swap the worker in `cli.build_scheduler`:

```python
CommandWorker(["python", "my_trainer.py"], workdir)
```

or subclass `SleepWorker` in `workers.py` and implement `run_chunk(budget_s, practice_files, should_stop)`.

## Tools and dream checking

While it practises, the model can run Python in the sandbox, search your chat diary (read-only), and, if `research_web` is on, search the web (it refuses local/private addresses). Turn tool use off with `"practice_tools": false`. A trainer that makes up "dreams" (synthetic Q/A) can check them first:

```
python -m sleepmode.dreamcheck dreams.jsonl --out checked/ --model-url http://127.0.0.1:18082 [--no-web] [--keep-unknown]
```

It writes `kept.jsonl` (supported or fixed answers), `dropped.jsonl` and `stats.json`; train on `kept.jsonl`.

## Tests

`python3 -m unittest discover -s sleepmode/tests -t .` (from the repo root; no Mac or GPU needed).
