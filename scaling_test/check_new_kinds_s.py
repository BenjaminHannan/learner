import json, re, sys, collections
from pathlib import Path
H = Path(__file__).resolve().parent
sys.path.insert(0, str(H))
import gen_english as G
d = json.load(open(H / "NEW-KINDS-S.json"))
ex = d["examples"]; bad = []
def err(m): bad.append(m); print("PROBLEM:", m)
if set(d) != {"title", "note", "examples"}: err("top keys")
if len(ex) != 48: err(f"{len(ex)} examples")
fc = collections.Counter(e["family"] for e in ex)
print("families:", dict(fc))
if len(fc) != 6 or set(fc.values()) != {8}: err("not 6x8")
OTHERS = ["english_training_candidates_v3.json", "FRESH-EN-R3.json", "NEW-KINDS-R5.json", "GEN-HELDOUT-R4.json"]
o_pass, o_ans, o_names, o_fams = set(), set(), set(), set()
for f in OTHERS:
    for e in json.load(open(H / f))["examples"]:
        o_fams.add(e["family"])
        for t in (e["source_text"], e["paraphrase"]):
            o_pass.add(G.norm(t)); o_names |= set(re.findall(r"[A-Z][a-z]+", t))
        for q in e["questions"]:
            for a in q["accepted_answers"] + [q["canonical_answer"]]:
                o_ans |= set(G.norm(a).replace("'s", "").replace("-", " ").split())
print("family overlap with others:", set(fc) & o_fams or "none")
pool_names = {(a + b).capitalize() for a in G.SYL1 for b in G.SYL2}
pool_words = set(G.NOUNS) | set(G.ADJS) | set(G.PLACES) | set(G.SURFACES)
pool_words |= {w for n in pool_words for w in n.split()}
numw = set("one two three four five six seven eight nine ten eleven twelve".split())
stop = {"the", "a", "an", "to", "of", "in", "on", "by", "with", "did", "and", "yes", "no", "was", "is", "it", "does", "not", "as", "from", "up", "only", "one", "stairs", "were", "had", "did", "do"}
ids = set(); yn = collections.Counter(); mine_names = set()
for e in ex:
    if set(e) != {"id", "family", "source_text", "paraphrase", "questions"}: err(f"keys {e.get('id')}")
    if e["id"] in ids: err("dup id")
    ids.add(e["id"])
    if not re.fullmatch(r"new_.+_0[1-8]", e["id"]) or not e["id"].startswith("new_" + e["family"]): err(f"id {e['id']}")
    if len(e["questions"]) != 2 or [q["type"] for q in e["questions"]] != ["short_answer", "yes_no"]: err(f"qtypes {e['id']}")
    for t in (e["source_text"], e["paraphrase"]):
        if G.norm(t) in o_pass: err(f"passage overlap {e['id']}")
        mine_names |= set(re.findall(r"(?<!^)(?<!\. )[A-Z][a-z]+", t))
        for q in e["questions"]:
            n = len((t + " " + q["question"]).split())
            if n > 30: err(f"{n} words {e['id']}")
    if e["source_text"] == e["paraphrase"]: err("same para " + e["id"])
    for q in e["questions"]:
        if set(q) != {"question", "type", "canonical_answer", "accepted_answers"}: err(f"qkeys {e['id']}")
        if q["canonical_answer"] not in q["accepted_answers"]: err(f"canon not in acc {e['id']}")
        if q["type"] == "yes_no":
            yn[q["canonical_answer"]] += 1
            if q["accepted_answers"] != [q["canonical_answer"]] or q["canonical_answer"] not in ("Yes", "No"): err(f"yn {e['id']}")
        else:
            ws = set()
            for a in q["accepted_answers"]: ws |= set(G.norm(a).replace("'s", "").replace("-", " ").split())
            ws -= stop
            for w in sorted(ws):
                tag = "number-word/digit (allowed)" if (w in numw or w.isdigit()) else None
                if w in o_ans and not tag: print(f"overlap answer word with other files: {w!r} in {e['id']}")
                if w in o_ans and tag: print(f"note: {tag} {w!r} in {e['id']} also used elsewhere")
                if w in pool_words and w not in numw: print(f"overlap answer word with generator pool: {w!r} in {e['id']}")
mine_names = {n for n in mine_names if n not in {"Only", "Nobody", "Both", "Lemonade", "After", "Over", "Before", "Three", "Two", "Of", "All", "By", "When", "The", "Selwyn_"}} | {n for e in ex for t in (e["source_text"], e["paraphrase"]) for n in re.findall(r"[A-Z][a-z]+(?='s\b|\b)", t) if n in {"Orlin","Brisa","Hobart","Quill"}}
for n in sorted(mine_names):
    if n in pool_names: print(f"name in generator pool: {n}")
    if n in o_names: print(f"name used in other files: {n}")
print("yes/no:", dict(yn))
if abs(yn["Yes"] - yn["No"]) > 4: err("yes/no unbalanced")
print("RESULT:", "FAIL" if bad else "OK")
