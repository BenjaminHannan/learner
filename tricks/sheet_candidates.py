"""Sheet-1 step 1: show Claude the 4B's saved baseline outputs on the 100 TRAIN questions, get 6 candidate instruction sheets.
Never reads test rows. One Messages API call (needs env LEARNER_ANTHROPIC_API_KEY); --dry-run only writes the prompt."""
import argparse, json, os, random, re, ssl, urllib.error, urllib.request
from datetime import datetime, timezone
from pathlib import Path
import tricks1

HERE = Path(__file__).parent
SAVED = "/mnt/project-files/results/tricks1/small/rows_s_py_gsmh.jsonl"
MODEL, CA = "claude-opus-5-5", "/root/.ccr/ca-bundle.crt"
N_SHEETS, MAX_CHARS, MAX_WORDS, N_OK = 6, 1600, 200, 8
# general (primary, PREREG-sheet1.md): steer away from fitting GSM-Hard's label quirks. quirk (exploratory): the first prompt,
# which told Claude the gold can be negative/fractional, so all six sheets leaned on "compute literally, never clamp or round".
GOLD = {"general": "The gold answer comes from running the original solution with the new numbers; the story was not re-checked, so some gold "
                   "answers are odd or wrong in real life.",
        "quirk": "The gold answer is what the original solution program gives on the large numbers, so it can be negative, fractional or "
                 "implausible in real life."}
EXTRA = {"general": ["- Do not write rules aimed at matching odd or wrong gold answers (for example about negative, fractional or impossible results). "
                     "Aim for sheets that make the model a better, more careful problem solver on ordinary word problems too."],
         "quirk": []}

def fmt(x):
    if x is None:
        return "none"
    return str(int(x)) if float(x).is_integer() else repr(float(x))

def train_acc(train_rows, saved_by_id):
    return sum(bool(saved_by_id[r["id"]]["correct"]) for r in train_rows) / len(train_rows)

def build_prompt(train_rows, saved_by_id, sheet, variant="general"):
    """Pure: uses only train_rows (and the saved rows with the same ids). variant: see GOLD/EXTRA."""
    rs = [(r, saved_by_id[r["id"]]) for r in train_rows]
    bad = [(r, s) for r, s in rs if not s["correct"]]
    ok = [(r, s) for r, s in rs if s["correct"]]
    n_ok, ok = len(ok), random.Random(0).sample(ok, min(N_OK, len(ok)))
    p = ["You are helping tune a system prompt (an \"instruction sheet\") for a small language model.\n",
         "## Target model and setup",
         "- Model: Qwen3.5-4B with thinking mode OFF (it still writes visible step-by-step reasoning in its reply), greedy decoding.",
         "- Task: GSM-Hard, i.e. GSM8K-style grade-school word problems whose numbers were replaced by large numbers. " + GOLD[variant],
         "- The model sees your sheet as the system message, then a user message: the problem followed by \"End with 'Final answer: <number>'.\"",
         "- It has one tool, `python` (runs Python 3 code and returns stdout; 10 s timeout, output cut at 2000 characters, no network; the code must print()). "
         "It can use the tool for up to 4 rounds; the final round offers no tool, so it must then answer in plain text. Each reply is capped at 2048 tokens; "
         "a reply cut off by the cap usually has no final answer line and scores wrong.",
         "- Scoring: the answer is the number after the last \"Final answer:\" in the final reply (if there is none, a last \\boxed{} number, else the last number "
         "in the text). It is correct if it matches the gold number to within a relative tolerance of 1e-4.",
         "- Your sheets will be scored on problems of the same kind that you are not shown.\n",
         "## Current sheet (baseline)", f"\"\"\"\n{sheet}\n\"\"\"",
         f"Its accuracy on the {len(rs)} training problems below: {n_ok}/{len(rs)}.\n",
         f"## All {len(bad)} failures on the training problems",
         "Each shows the problem, the gold answer, the model's parsed answer, how many python calls it made, and the last 1500 characters of its final reply.\n"]
    for i, (r, s) in enumerate(bad, 1):
        p += [f"### Failure {i}", f"Problem: {r['q']}", f"Gold: {fmt(r['gold'])}", f"Model's parsed answer: {fmt(s['pred'])}",
              f"Python calls: {s['tool_calls']}   Tokens: {s['tokens']}", f"End of final reply:\n\"\"\"\n{s['text']}\n\"\"\"\n"]
    p += [f"## {len(ok)} successes (randomly chosen)\n"]
    for i, (r, s) in enumerate(ok, 1):
        p += [f"### Success {i}", f"Problem: {r['q']}", f"Python calls: {s['tool_calls']}   Tokens: {s['tokens']}\n"]
    p += ["## Your task",
          f"Write exactly {N_SHEETS} candidate instruction sheets that replace the current one. They must take clearly different strategies (not rewordings of one idea). Requirements:",
          f"- At most {MAX_WORDS} words each.",
          "- General: do not mention specific problems, numbers or answers from the examples above.",
          *EXTRA[variant],
          "- Each must keep the instruction to end the reply with a final line of the form 'Final answer: <number>'.",
          "- Each is used as the whole system message, so it can say how to use the python tool.",
          "",
          "Reply with JSON only (no code fences, no commentary): a list of exactly "
          f"{N_SHEETS} objects, each {{\"name\": <short strategy name>, \"sheet\": <the sheet text>}}."]
    return "\n".join(p)

def parse_sheets(text):
    t = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", text.strip())
    try:
        arr = json.loads(t)
    except ValueError:
        arr = json.loads(t[t.index("["):t.rindex("]") + 1])
    assert isinstance(arr, list) and len(arr) == N_SHEETS, f"want {N_SHEETS} items, got {len(arr) if isinstance(arr, list) else type(arr).__name__}"
    for a in arr:
        assert isinstance(a, dict) and isinstance(a.get("name"), str) and a["name"].strip(), f"bad name in {a!r:.100}"
        assert isinstance(a.get("sheet"), str) and a["sheet"].strip(), f"empty sheet for {a['name']}"
        assert len(a["sheet"]) <= MAX_CHARS, f"sheet {a['name']!r} is {len(a['sheet'])} chars > {MAX_CHARS}"
    return [{"name": a["name"].strip(), "sheet": a["sheet"].strip()} for a in arr]

def call_api(prompt, model=MODEL, max_tokens=8000, timeout=900):
    key = os.environ.get("LEARNER_ANTHROPIC_API_KEY")
    if not key:
        raise SystemExit("LEARNER_ANTHROPIC_API_KEY is not set")
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", method="POST",
        data=json.dumps({"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": prompt}]}).encode(),
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        try:
            r = urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.URLError as e:
            if not (isinstance(e.reason, ssl.SSLError) and os.path.exists(CA)):
                raise
            r = urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context(cafile=CA))
        with r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"API error HTTP {e.code}: {e.read().decode(errors='replace')[:1000]}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(HERE / "sheet1_data.json")); ap.add_argument("--saved", default=SAVED)
    ap.add_argument("--out", default=str(HERE / "sheets1.json")); ap.add_argument("--prompt-out", default=str(HERE / "sheets1_prompt.txt"))
    ap.add_argument("--model", default=MODEL); ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--variant", choices=sorted(GOLD), default="general")
    a = ap.parse_args()
    train = json.loads(Path(a.data).read_text())["train"]
    ids = {r["id"] for r in train}
    saved = {}
    for l in Path(a.saved).open():
        if l.strip() and json.loads(l)["id"] in ids:
            s = json.loads(l); saved[s["id"]] = s
    assert set(saved) == ids, f"{len(ids - set(saved))} train ids missing from {a.saved}"
    prompt = build_prompt(train, saved, tricks1.PY_SYS, a.variant)
    Path(a.prompt_out).write_text(prompt)
    acc = train_acc(train, saved)
    print(f"[prompt] {len(prompt)} chars, train acc (saved baseline) {acc:.2f} -> {a.prompt_out}")
    if a.dry_run:
        return
    resp = call_api(prompt, a.model)
    text = "".join(b.get("text", "") for b in resp.get("content", []) if b.get("type") == "text")
    try:
        assert resp.get("stop_reason") != "max_tokens", "reply hit max_tokens"
        sheets = parse_sheets(text)
    except Exception as e:
        raw = Path(a.out).with_suffix(".raw.txt"); raw.write_text(text)
        raise SystemExit(f"could not use the reply ({type(e).__name__}: {e}); raw reply saved to {raw}")
    Path(a.out).write_text(json.dumps({"model": resp.get("model", a.model), "made_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                                       "variant": a.variant, "train_acc_saved": acc, "prompt_chars": len(prompt), "sheets": sheets}, indent=1))
    for i, s in enumerate(sheets, 1):
        w = len(s["sheet"].split())
        print(f"[sheet {i}] {s['name']} ({w} words{' !! over ' + str(MAX_WORDS) if w > MAX_WORDS else ''})")
    print(f"[done] {a.out}")

if __name__ == "__main__":
    main()
