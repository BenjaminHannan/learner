"""Exp 238 step 2b/3b: render code-scanned reply templates with tricky fillers.

Reads codetemplates.jsonl (from claude_grammar238_codescan.py), keeps the ones
that are user-facing reply templates (drops test inputs, questions the tests
ask, regexes, class labels, bench teach sentences), marks whether each was
ever seen in the harvest, and fills every placeholder with tricky fillers:
names ending in s/x/z, multi-word names, lower-case names, vowel-initial and
plural values, 0/1/2, empty/one/three-item lists, raw relation keys, dates.
These are SUBSTITUTED renders (string filling), not agent runs; the agent-run
renders are in probes/. Writes coderenders.jsonl.
"""
import json, re, itertools
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "artifacts" / "claude-grammar238-20260922"
DROP_FILES = re.compile(r"selftest|bench\d|bert_loader|wordmatch149|qrewrite132|wire57|thinking_m2|listening_english|"
                        r"_probe|fix167_verb|fix167d_verb|loop221c_agent|fix221_tableask|self99\.py:(8[0-9]|9[0-9]|1[0-9][0-9]|2[0-4][0-9])$")
DROP_TEXT = re.compile(r"^(Loop|Reasoner|Indexed|Self99|Sleep|JSON config|Exp \d|Notebook contract|The glue|Qmark|ScreenStatus|"
                       r"SPLIT clarify|ANSWERING|English Listening|FAIL \(|SMOKE|Template English|\(script|\(each answer|"
                       r"Ben taught|Ben:|Agent:|Where does/do|Who does/do|What language)")
FILL = {
    "num": ["0", "1", "2"],
    "list": ["", "Max", "Max, Ines and Ula"],
    "name": ["Silas", "Juniper Lane Books", "max", "Lux"],
    "rel": ["country_of_citizenship", "founding_year", "friends", "city"],
    "val": ["an owl", "engineer", "3 May", "Oslo"],
}


def slot_kind(expr: str) -> str:
    e = expr.lower()
    if re.search(r"n_|turns|sleeps|writes|answers|clarif|count|len\(|max_hops|\bt\b|^t$|shown_n", e):
        return "num"
    if re.search(r"people|names|listed|joined|others|remainers|choices|join", e):
        return "list"
    if re.search(r"rel|key|\brd\b|^r$|relation|disp", e):
        return "rel"
    if re.search(r"value|val|\bv\b|^v$|new|old|answer|ans|span|shown|exc|reason", e):
        return "val"
    return "name"


def main():
    harvested = [json.loads(l)["reply"] for l in open(D / "harvest.jsonl")]
    hset = set(harvested)
    blob = "\n".join(harvested)
    rows, seen_t = [], set()
    for l in open(D / "codetemplates.jsonl"):
        r = json.loads(l)
        t, loc = r["template"], f'{r["file"]}:{r["line"]}'
        if DROP_FILES.search(loc) or DROP_TEXT.search(t) or (t, r["kind"]) in seen_t:
            continue
        if r["kind"] == "literal" and t.endswith("?") and not t.startswith(("Which one", "Do you", "Was that", "Could you")):
            continue  # test questions, not replies
        seen_t.add((t, r["kind"]))
        if r["kind"] in ("fstring", "format"):
            slots = re.findall(r"\{([^{}]+)\}", t)
            pat = re.escape(t)
            for sl in slots:
                pat = pat.replace(re.escape("{" + sl + "}"), ".+?", 1)
        elif r["kind"] == "percent":
            slots = re.findall(r"%[sd]", t)
            pat = re.escape(t).replace("%s", ".+?").replace("%d", r"\d+")
        else:
            slots, pat = [], None
        try:
            seen = (t in hset) if pat is None else bool(re.search(pat, blob))
        except re.error:
            seen = False
        renders = []
        if not slots:
            renders = [t]
        else:
            for i in range(4):
                out = t
                for sl in slots:
                    k = slot_kind(sl) if sl not in ("%s", "%d") else ("num" if sl == "%d" else "name")
                    opts = FILL[k]
                    val = opts[i % len(opts)]
                    out = out.replace("{" + sl + "}", val, 1) if sl not in ("%s", "%d") else out.replace(sl, val, 1)
                renders.append(out)
        for rd in dict.fromkeys(renders):
            rows.append({"source": loc, "template": t, "seen_in_harvest": seen, "render": rd})
    with open(D / "coderenders.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    ntempl = len({r["template"] for r in rows})
    nunseen = len({r["template"] for r in rows if not r["seen_in_harvest"]})
    print(f"reply templates kept={ntempl} never_seen_in_runs={nunseen} renders={len(rows)}")


if __name__ == "__main__":
    main()
