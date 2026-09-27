# Claude (director) fairness re-count of exp 125: SmolLM2 replies that decline in its own words
# ("unknown", "not mentioned", "don't know", ...) are counted as ABSTAIN instead of WRONG.
# Scorer v2's abstain list only knew the loop's own decline wording. Reads exp 125 rows; writes fairness.json.
import json, glob, re, collections, os
DECL = re.compile(r"\b(unknown|not (stated|mentioned|given)|cannot|can't|no information|don't know)\b")
out = {}
for f in sorted(glob.glob('artifacts/fable-bench125-20260922/*_rows.jsonl')):
    rows = [json.loads(l) for l in open(f)]
    c = collections.Counter()
    for r in rows:
        v = r['verdict']
        if v == 'wrong' and DECL.search(r['answer'].lower()):
            v = 'abstain'
        c[v] += 1
    out[os.path.basename(f).replace('fable_bench125_', '').replace('_rows.jsonl', '')] = {
        'n': len(rows), 'correct': c['correct'], 'abstain': c['abstain'], 'wrong': c['wrong']}
json.dump(out, open('artifacts/claude-bench125-fairness-20260922/fairness.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
