from collections import Counter
from learnlab.splits import assign_ranked
fam = [f"rule{i}" for i in range(20)]
base = assign_ranked("rule_family", fam)
worst = Counter()
for k in range(1, 9):
    grown = assign_ranked("rule_family", fam + [f"new{j}" for j in range(k)])
    c = Counter((base[x], grown[x]) for x in fam if base[x] != grown[x])
    print(f"+{k} families:", dict(c))
shrunk = assign_ranked("rule_family", fam[1:])
print("-1 family:", dict(Counter((base[x], shrunk[x]) for x in fam[1:] if base[x] != shrunk[x])))
