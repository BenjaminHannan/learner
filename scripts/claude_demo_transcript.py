"""Render artifacts/claude-demo-dryrun-20260922/transcript.md from raw.json + script.json."""
import json
from pathlib import Path
ART = Path(__file__).resolve().parent.parent / "artifacts" / "claude-demo-dryrun-20260922"
S = {t["id"]: t for t in json.loads((ART / "script.json").read_text())["turns"]}
R = json.loads((ART / "raw.json").read_text())
A = {x["id"]: x for x in R["agent"] if "id" in x}
Sm = {x["id"]: x for x in R["smol"] if "id" in x}
esc = lambda s: s.replace("|", "\\|").replace("\n", " ")
out = ["# Demo dry-run transcript (2026-09-22, one run)", "",
       "Agent = loop138i base agent (fresh temp state dir). SmolLM = SmolLM2-360M-Instruct with the fair",
       "prompt from scripts/fable_fairsmol211.py (all taught sentences so far, numbered, correction marked",
       "'(this replaces fact N)'), greedy decode, max %d new tokens. Restart (turn 24): agent = new daemon on the"
       % R["smol"][-1]["max_new_tokens"],
       "same state dir; SmolLM = empty context (it has no memory of its own).",
       "Agent run %.1fs, SmolLM run %.1fs. 'Agent saved' = notebook triples added (+) / removed (-) on that turn."
       % (R["agent_seconds"], R["smol_seconds"]), "",
       "| # | Visitor types | Expected | Agent reply | Agent saved | SmolLM reply |",
       "|---|---|---|---|---|---|"]
for i in sorted(S):
    t, a, s = S[i], A[i], Sm[i]
    saved = " ".join("+(%s)" % ", ".join(x) for x in a["added"]) + " ".join(" -(%s)" % ", ".join(x) for x in a["removed"])
    if t["kind"] == "restart":
        saved = "facts on disk kept (4); in-memory index lists %d rows (doubled, see RESULTS)" % len(a["facts_after"])
    out.append("| %d%s | %s | %s | %s | %s | %s |" % (i, " (improv)" if t.get("improv") else "", esc(t["text"]),
               esc(t["expect"]), esc(a["reply"]), esc(saved or "-"), esc(s["reply"])))
(ART / "transcript.md").write_text("\n".join(out) + "\n")
print("ok")
