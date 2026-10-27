# Exp 239 conversation panel — TEST-ONLY

**TEST-ONLY. Do not train, tune or write agent rules on this panel. Do not edit panel.jsonl after sealing (see SEAL.sha256.txt).**

A standing blind conversation panel: 30 fresh sessions, 244 user turns, written by an ordinary-user writer who did not read agent code, design notes or earlier panels. All names are fictional.

- `panel.jsonl` — one conversation per line: `id`, `persona`, `turns` (list of `{user, intent, expect}`). Intents: greet / smalltalk / teach / ask / correct / self / cannot / thanks / other. `expect` = what a good reply must contain.
- `SEAL.sha256.txt` — sha256 of panel.jsonl (from repo root).
- `transcripts-<version>.jsonl` / `.md` — runs of an agent version on this panel (per turn: user, reply, stored triples after the turn). Ungraded; a separate judge grades them.

Re-run on any version (each conversation gets its own fresh workdir; the repo notebook/ is never touched):

    export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
    uv run --offline --no-project --python 3.12 --with torch --with numpy python -B \
      scripts/claude_convpanel239_run.py --agent <agent.py> --config <config.json> \
      --out artifacts/claude-convpanel239-20260922/transcripts-<version>
