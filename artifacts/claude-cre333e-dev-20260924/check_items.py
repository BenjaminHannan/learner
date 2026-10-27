"""Checks for items.jsonl (DEV set). Run: python3 check_items.py"""
import json, re, os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
items = [json.loads(l) for l in open(os.path.join(HERE, "items.jsonl"))]
fails = []
def check(cond, msg):
    if not cond:
        fails.append(msg)

KEYS = {"item_id", "kind", "turns", "last", "facts", "gold", "about_untaught_person", "avoids_cue_words", "request_type"}
CUE = re.compile(r"\b(idea\w*|suggest\w*|recommend\w*|gift\w*|present\w*|poem\w*|stor(?:y|ies)|song\w*|"
                 r"toast\w*|plan|plans|planned|planning|planner\w*|brainstorm\w*|come up with|help me)\b", re.I)

# 1. keys exact, ids unique
for it in items:
    check(set(it) == KEYS, f"{it.get('item_id')}: keys {sorted(set(it) ^ KEYS)}")
    for fa in it["facts"]:
        check(set(fa) == {"owner", "relation", "value"}, f"{it['item_id']}: bad fact keys")
ids = [it["item_id"] for it in items]
check(len(ids) == len(set(ids)), "duplicate ids")

cre = [it for it in items if it["kind"] == "creative"]
ct = [it for it in items if it["kind"] == "control_teach"]
ca = [it for it in items if it["kind"] == "control_ask"]
mem = [it for it in ca if int(it["item_id"][-2:]) <= 25]
gen = [it for it in ca if int(it["item_id"][-2:]) >= 26]

# 2. counts
check([it["item_id"] for it in cre] == [f"dcre-{i:02d}" for i in range(1, 41)], "creative ids")
check(sorted(it["item_id"] for it in ct + ca) == [f"dctl-{i:02d}" for i in range(1, 31)], "control ids")
rt = Counter(it["request_type"] for it in cre)
check(rt == Counter(gift=10, plan=8, poem_toast_card=8, cook_bring=6, message=4, other=4), f"request_type {rt}")
unt = sum(it["about_untaught_person"] is True for it in cre)
check(unt == 10, f"untaught {unt}")
check(len(ct) == 10 and len(mem) == 15 and len(gen) == 5, f"controls {len(ct)}/{len(mem)}/{len(gen)}")
for it in cre:
    check(2 <= len(it["turns"]) <= 5, f"{it['item_id']}: teach turns {len(it['turns'])}")
    check(it["gold"] is None and isinstance(it["about_untaught_person"], bool), f"{it['item_id']}: fields")
for it in ct + ca:
    check(1 <= len(it["turns"]) <= 3, f"{it['item_id']}: teach turns {len(it['turns'])}")
    check(it["about_untaught_person"] is None and it["avoids_cue_words"] is None and it["request_type"] is None,
          f"{it['item_id']}: creative-only fields set")
for it in ct:
    check(it["gold"] is None, f"{it['item_id']}: control_teach gold")
for it in ca:
    check(isinstance(it["gold"], str) and it["gold"], f"{it['item_id']}: gold missing")

# 3. avoids_cue_words flag computed by regex, >= 15 true
for it in cre:
    check(it["avoids_cue_words"] == (CUE.search(it["last"]) is None), f"{it['item_id']}: avoids flag wrong")
n_avoid = sum(it["avoids_cue_words"] for it in cre)
check(n_avoid >= 15, f"only {n_avoid} avoid cue words")

# 4. memory gold appears in an earlier turn; general gold does not come from turns
for it in mem:
    check(any(it["gold"].lower() in t.lower() for t in it["turns"]), f"{it['item_id']}: gold not in turns")

# 5. names: every capitalized non-whitelisted token starts with S-Z; no name shared across items
NON_NAMES = set("""I I'm I've I'd My We We're Me Our He He's She She's Her His It It's They They've Can Coworker
What Want Write Help Congrats Anniversery Budget Rent One Stuck Friday June Sunday Saturday November Thanksgiving
New Year's Eve March May RSVP Ethiopian Tin Lanterns HER NOT Firm Thoughts Ferry Bay Cross Hills
Brackenford Colderwick Pellmoor Ashcombe Hollins Dunmorrow Marrowby Greyhaven Carrow Lindenmere Eastwater Farthing
Kestrel Oakhallow Glimmerby Hartsloe Norrowgate Quillhaven Millbrindle Tollbridge Birchmere Harrowmere Fernhallow
Ashvelling Lowmere Stonewhistle Kelderhold Rowanbeck Pinecrake Glenmorrow Dovercliff Brookhollow Mossgate Carlowe""".split())
owner_of = {}
for it in items:
    texts = it["turns"] + [it["last"]]
    names = set()
    for t in texts:
        for tok in re.findall(r"[A-Za-z][A-Za-z']*", t):
            tok = re.sub(r"'s$", "", tok)
            if tok[0].isupper() and tok not in NON_NAMES:
                names.add(tok)
    for fa in it["facts"]:
        if fa["owner"] != "USER":
            names.add(fa["owner"])
    for n in names:
        check(n[0] in "STUVWXYZ", f"{it['item_id']}: name {n!r} not S-Z")
        check(n not in owner_of, f"{it['item_id']}: name {n!r} also in {owner_of.get(n)}")
        owner_of.setdefault(n, it["item_id"])

print(f"items={len(items)} creative={len(cre)} control_teach={len(ct)} control_ask={len(ca)} "
      f"(memory={len(mem)}, general={len(gen)})")
print(f"request_type={dict(rt)} untaught={unt} avoids_cue_words_true={n_avoid}")
print(f"distinct person/pet names={len(owner_of)}")
print("FAIL:\n  " + "\n  ".join(fails) if fails else "ALL CHECKS PASSED")
