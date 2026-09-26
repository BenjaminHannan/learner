import sys, json
sys.path.insert(0, 'scripts')
import claude_ask24 as A24, claude_ask24ab as S, claude_feas24 as F
m = open(sys.argv[1]).read().strip()
s = A24.AskSolver(m); s.a_ids, s.b_ids = S.letter_ids(s.tok, "A"), S.letter_ids(s.tok, "B")
ps = S.panel(790, 120)
out = {}
for name, amy in (("AB1", True), ("AB2", False)):
    rows = [S.ab_decide(s, p, amy) for p in ps]
    # p(yes) share among the two letters
    py = [(pa / (pa + pb)) if amy else (pb / (pa + pb)) for _, pa, pb, _ in rows]
    sol = [x for x, p in zip(py, ps) if p["solvable"]]; imp = [x for x, p in zip(py, ps) if not p["solvable"]]
    pair = sum((py[2*k+1] > py[2*k]) + 0.5 * (py[2*k+1] == py[2*k]) for k in range(120))
    out[name] = {"auc_yes_solvable_vs_impossible": round(F.auc(sol, imp), 3), "twin_pairs_ranked_right_of_120": pair,
                 "mean_pyes_solvable": round(sum(sol)/120, 3), "mean_pyes_impossible": round(sum(imp)/120, 3),
                 "min_pyes": round(min(py), 3), "max_pyes": round(max(py), 3)}
    print(name, out[name], flush=True)
json.dump(out, open(sys.argv[2], "w"), indent=1)
