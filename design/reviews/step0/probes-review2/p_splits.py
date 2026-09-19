from collections import Counter
from learnlab.splits import assign_ranked, assign, SplitRegistry, SplitLeak, DEFAULT_FRACTIONS
from learnlab.toy import TEMPLATES, STYLES, TOY_FRACTIONS, TOY_SALT, make_registry, episodes, all_names

print("== assign_ranked split sizes (promises every split its share)")
for n in (3, 4, 5, 6, 7, 9, 10):
    fam = [f"r{i}" for i in range(n)]
    for fr in (DEFAULT_FRACTIONS, (0.95, 0.025, 0.025), (0.34, 0.33, 0.33)):
        try:
            c = Counter(assign_ranked("rule_family", fam, fractions=fr).values())
            sizes = (c["train"], c["validation"], c["test"])
            if 0 in sizes: print(f"  n={n} fractions={fr}: train/val/test={sizes}  <-- EMPTY SPLIT")
        except ValueError as e: print(f"  n={n} {fr}: ValueError {e}")
print("  fractions not validated:", assign_ranked("template", ["a","b","c","d"], fractions=(2.0, -1.0, 0.0)))

print("== ranked family membership change moves items across splits")
base = assign_ranked("template", TEMPLATES, salt=TOY_SALT, fractions=TOY_FRACTIONS)
moved_total = Counter()
for extra in [f"t{12+i:02d}" for i in range(6)]:
    grown = assign_ranked("template", list(TEMPLATES) + [extra], salt=TOY_SALT, fractions=TOY_FRACTIONS)
    moved = [(k, base[k], grown[k]) for k in base if base[k] != grown[k]]
    for _, a, b in moved: moved_total[(a, b)] += 1
    if moved: print(f"  +{extra}: {moved}")
print("  crossings over 6 one-item additions:", dict(moved_total))
# the registry cannot see it: two processes, two registries
r_train = SplitRegistry(salt=TOY_SALT, fractions=TOY_FRACTIONS); r_train.fix_family("template", TEMPLATES)
r_eval = SplitRegistry(salt=TOY_SALT, fractions=TOY_FRACTIONS); r_eval.fix_family("template", list(TEMPLATES) + ["t13"])
leaked = [k for k in TEMPLATES if r_train.split_of("template", k) == "train" and r_eval.split_of("template", k) == "test"]
print("  trained-on templates that a later eval registry calls 'test':", leaked)

print("== same registry, family re-fixed mid-run")
reg = SplitRegistry(salt=TOY_SALT, fractions=TOY_FRACTIONS); reg.fix_family("template", TEMPLATES)
item = next(k for k in TEMPLATES if reg.split_of("template", k) == "train"); reg.record("template", item, "train")
reg.fix_family("template", list(TEMPLATES) + ["t13", "t14", "t15"])
new = reg.split_of("template", item)
try:
    if new != "train": reg.record("template", item, new)
    reg.assert_disjoint(); print(f"  {item}: train -> {new}, assert_disjoint silent")
except SplitLeak as e: print("  caught by assert_disjoint:", e)

print("== registry records generation, not consumption")
reg = make_registry(); test_eps = episodes(reg, "test", 50)
# trainer bug: trains on test episodes; nothing in the registry objects
reg.assert_disjoint(); print("  training loop consumed 50 test episodes; registry silent; Episode.split =", test_eps[0].split)

print("== unrecorded mention (generator adds a distractor sentence without record())")
reg = make_registry()
train_name = next(n for n in all_names() if reg.split_of("name", n) == "train")
eps = episodes(reg, "test", 5)
text = eps[0].lines + (f"{train_name} waves hello.",)
reg.assert_disjoint(); print(f"  test episode mentions train name {train_name!r}; registry silent")

print("== name split sizes for toy pool")
c = Counter(reg.split_of("name", n) for n in all_names()); print(" ", dict(c), "of", len(all_names()))
