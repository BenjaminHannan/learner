# Ben's Week benchmark engine

Spec: `SPEC.md`. Run everything from the repo root (`/home/user/learner`).

```
python -m bensweek.validate                                   # check all dev episodes
python -m unittest discover -s bensweek/tests                 # offline tests

# local model (OpenAI-compatible server), 2 conversations at a time
python -m bensweek.run --agent openai --base-url http://127.0.0.1:8090/v1 --model qwen36-fast \
    --split dev --memory notes --concurrency 2
# Claude ceiling via the Message Batches API (lockstep; key in LEARNER_ANTHROPIC_API_KEY)
python -m bensweek.run --agent claude --model claude-sonnet-5-5 --memory context
python -m bensweek.grade runs/<run_id>                        # rubric checks, one batch
python -m bensweek.agree runs/<run_id> --n 40                 # second judge, writes spotcheck.md
python -m bensweek.seal wk09 wk10                             # move episodes into sealed.bin
```

Run options: `--episodes wk01,wk03`, `--memory none|notes|diary|context`, `--days N`, `--resume`,
`--max-steps 25`, `--between-days-cmd "CMD {run_dir} {episode} {day}"`, `--out DIR`,
`--live` (claude only: direct non-batch calls, for debugging). `--split sealed` needs
`--i-am-running-the-final-v2-eval`.

Order: day 1 of every episode (in parallel), between-days hook, day 2, ... Tasks inside one
episode-day run in order because they share world state.

Run output (`runs/<id>/`): `results.jsonl`, `summary.json`, `summary.md`, `usage.json` (tokens and
estimated cost), `diary/<episode>/dayN.jsonl`, and per task `episodes/<ep>/<task>/` with
`transcript.json`, `toollog.json`, `checks.json`, `diff.json` (world changes), `result.json`.
Pass rate is pass / (pass + fail); tasks with an undecided rubric check are `pending` until graded.
A rubric check may set `"context": "episode"` to give the grader every earlier task of the episode.

Cost estimates use the `PRICES` table in `agents.py` (list prices, batch = 50%); check it against the
pricing page before trusting the dollars.
