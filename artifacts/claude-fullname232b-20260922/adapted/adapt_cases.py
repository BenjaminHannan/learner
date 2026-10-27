"""232b post-seal INPUT adapter (unregistered, disclosed): maps the 232b
panel schema (family multi/one/trap, paired by position) onto the fields the
sealed scorer reads (pair, name_words). No scoring logic changes."""
import json, sys
src, dst = sys.argv[1], sys.argv[2]
k = {"multi": 0, "one": 0}
with open(dst, "w", encoding="utf-8") as out:
    for line in open(src, encoding="utf-8"):
        it = json.loads(line)
        fam = it["family"]
        if fam in k:
            k[fam] += 1
            it["pair"] = f"P{k[fam]:02d}"
            it["name_words"] = 2 if fam == "multi" else 1
        else:
            it["pair"] = None
            it["name_words"] = None
        out.write(json.dumps(it, ensure_ascii=False) + "\n")
print(k)
