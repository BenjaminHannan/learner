import random
import re
import unittest

from sleepmode.practice import sandbox, tasks

HEAD = "import csv\n"
OUT = "w = csv.writer(open('output.csv', 'w', newline=''))\n"
DW = ("w = csv.DictWriter(open('output.csv', 'w', newline=''), fieldnames=rd.fieldnames)\n"
      "w.writeheader()\n")

REF = {
"sum_by_group": HEAD + OUT + """t = {}
for r in csv.DictReader(open('expenses.csv', newline='')):
    t[r['category']] = t.get(r['category'], 0) + float(r['amount'])
w.writerow(['category', 'total_amount'])
for k, v in t.items():
    w.writerow([k, '%.2f' % v])
""",
"avg_by_group": HEAD + OUT + """g = {}
for r in csv.DictReader(open('grades.csv', newline='')):
    g.setdefault(r['class'], []).append(float(r['score']))
w.writerow(['class', 'avg_score'])
for k in sorted(g):
    w.writerow([k, '%.2f' % (sum(g[k]) / len(g[k]))])
""",
"filter_rows": HEAD + "rd = csv.DictReader(open('sales.csv', newline=''))\n" + DW + """for r in rd:
    if r['region'] == '@REG@' and int(r['units']) >= @M@:
        w.writerow(r)
""",
"dedupe_key": HEAD + "rd = csv.DictReader(open('contacts.csv', newline=''))\n" + DW + """seen = set()
for r in rd:
    k = r['email'].strip().lower()
    if k in seen:
        continue
    seen.add(k)
    w.writerow(r)
""",
"join_lookup": HEAD + OUT + """p = {r['product_id']: r for r in csv.DictReader(open('products.csv', newline=''))}
w.writerow(['order_id', 'name', 'qty', 'line_total'])
for r in csv.DictReader(open('orders.csv', newline='')):
    q = p[r['product_id']]
    w.writerow([r['order_id'], q['name'], r['qty'], '%.2f' % (int(r['qty']) * float(q['price']))])
""",
"computed_column": HEAD + "rd = csv.DictReader(open('sales.csv', newline=''))\n" + OUT + """w.writerow(rd.fieldnames + ['revenue'])
for r in rd:
    w.writerow(list(r.values()) + ['%.2f' % (int(r['units']) * float(r['price']))])
""",
"sort_two_keys": HEAD + "rd = csv.DictReader(open('grades.csv', newline=''))\n" + """rows = sorted(rd, key=lambda r: (r['class'], -int(r['score']), r['student']))
""" + DW + "w.writerows(rows)\n",
"monthly_totals": HEAD + OUT + """t = {}
for r in csv.DictReader(open('expenses.csv', newline='')):
    t[r['date'][:7]] = t.get(r['date'][:7], 0) + float(r['amount'])
w.writerow(['month', 'total_amount'])
for k in sorted(t):
    w.writerow([k, '%.2f' % t[k]])
""",
"top_n_per_group": HEAD + OUT + """g = {}
for r in csv.DictReader(open('grades.csv', newline='')):
    g.setdefault(r['class'], []).append((int(r['score']), r['student']))
w.writerow(['class', 'student', 'score'])
for c in sorted(g):
    for s, n in sorted(g[c], key=lambda x: (-x[0], x[1]))[:2]:
        w.writerow([c, n, s])
""",
"percent_change": HEAD + OUT + """prev = None
w.writerow(['month', 'revenue', 'pct_change'])
for r in csv.DictReader(open('monthly.csv', newline='')):
    v = float(r['revenue'])
    w.writerow([r['month'], r['revenue'], '' if prev is None else '%.2f' % ((v - prev) / prev * 100)])
    prev = v
""",
"fill_missing": HEAD + "rd = csv.DictReader(open('grades.csv', newline=''))\nrows = list(rd)\n" + """g = {}
for r in rows:
    if r['score'].strip():
        g.setdefault(r['class'], []).append(float(r['score']))
""" + DW + """for r in rows:
    if not r['score'].strip():
        r['score'] = '%.2f' % (sum(g[r['class']]) / len(g[r['class']]))
    w.writerow(r)
""",
"split_fullname": HEAD + OUT + """w.writerow(['id', 'first_name', 'last_name', 'email'])
for r in csv.DictReader(open('contacts.csv', newline='')):
    n = r['full_name']
    if ',' in n:
        l, f = [x.strip() for x in n.split(',')]
    else:
        f, l = n.split()
    w.writerow([r['id'], f, l, r['email']])
""",
}

# subtle bugs: list of (old, new) replacements applied to the reference
WRONG = {
"sum_by_group": [("float(r['amount'])", "int(float(r['amount']))")],
"avg_by_group": [("sorted(g)", "sorted(g, reverse=True)")],
"filter_rows": [(">= @M@", "> @M@")],
"dedupe_key": [(".strip().lower()", ".strip()")],
"join_lookup": [("int(r['qty']) * ", "")],
"computed_column": [("'%.2f' % (int", "'%d' % (int")],
"sort_two_keys": [("-int(r['score'])", "int(r['score'])")],
"monthly_totals": [("[:7]", "[5:7]")],
"top_n_per_group": [("(-x[0], x[1])", "(-x[0],)")],
"percent_change": [("/ prev * 100", "/ v * 100")],
"fill_missing": [("g.setdefault(r['class'], [])", "g.setdefault(0, [])"), ("g[r['class']]", "g[0]")],
"split_fullname": [("if ',' in n:", "if False:")],
}


def solution(task, wrong=False):
    code = REF[task.family]
    if task.family == "filter_rows":
        m = re.search(r"region is exactly (\w+) and whose units are at least (\d+)", task.instruction)
        code = code.replace("@REG@", m.group(1)).replace("@M@", m.group(2))
    if wrong:
        for old, new in WRONG[task.family]:
            old = old.replace("@M@", re.search(r"at least (\d+)", task.instruction).group(1)) if "@M@" in old else old
            new = new.replace("@M@", re.search(r"at least (\d+)", task.instruction).group(1)) if "@M@" in new else new
            assert old in code, (task.family, old)
            code = code.replace(old, new)
    return code


def run_check(task, code):
    r = sandbox.run_python(code, task.files, timeout_s=20)
    assert r.ok, (task.family, r.stderr)
    return task.check(r.files_out)


class TaskTests(unittest.TestCase):
    def test_registry(self):
        self.assertIn("spreadsheet", tasks.registered_kinds())
        self.assertEqual(len(tasks.families("spreadsheet")), 12)
        self.assertEqual(set(tasks.families("spreadsheet")), set(REF))

    def test_deterministic_and_varied(self):
        a, b = tasks.generate("spreadsheet", 12, 5), tasks.generate("spreadsheet", 12, 5)
        self.assertEqual([t.files for t in a], [t.files for t in b])
        self.assertNotEqual([t.files for t in a], [t.files for t in tasks.generate("spreadsheet", 12, 6)])
        self.assertEqual({t.family for t in a}, set(REF))
        self.assertEqual(tasks.generate("nothing", 3, 1), [])

    def test_instructions_name_columns(self):
        for t in tasks.generate("spreadsheet", 12, 3):
            header = t.expected["output.csv"].splitlines()[0]
            self.assertIn(header, t.instruction, t.family)
            self.assertIn("output.csv", t.instruction)

    def test_reference_passes_and_wrong_fails_every_family(self):
        for seed in (1, 2, 3):
            for t in tasks.generate("spreadsheet", 12, seed):
                ok, why = run_check(t, solution(t))
                self.assertTrue(ok, (t.family, seed, why))
                ok, why = run_check(t, solution(t, wrong=True))
                self.assertFalse(ok, (t.family, seed, "wrong solution passed"))
                self.assertTrue(why)

    def test_check_variants(self):
        t = tasks.generate("spreadsheet", 12, 1)
        by = {x.family: x for x in t}
        exp = by["avg_by_group"].expected["output.csv"]
        self.assertEqual(by["avg_by_group"].check({"output.csv": exp})[0], True)
        self.assertFalse(by["avg_by_group"].check({})[0])
        self.assertFalse(by["avg_by_group"].check({"output.csv": exp.replace("avg_score", "avg")})[0])
        lines = exp.splitlines()
        # ordered family: swapping rows fails
        swapped = "\n".join([lines[0], lines[2], lines[1]] + lines[3:]) + "\n"
        self.assertFalse(by["avg_by_group"].check({"output.csv": swapped})[0])
        # unordered family: any order passes
        sg = by["sum_by_group"]
        ls = sg.expected["output.csv"].splitlines()
        self.assertTrue(sg.check({"output.csv": "\n".join([ls[0]] + ls[1:][::-1]) + "\n"})[0])
        # numbers: 2 dp rounding is fine, one cent off is not
        a, b = "k,v\nx,1.005\n", "k,v\nx,1.01\n"
        self.assertTrue(tasks.compare_csv(a, b)[0])
        self.assertFalse(tasks.compare_csv(a, "k,v\nx,1.02\n")[0])
        self.assertFalse(tasks.compare_csv(a, "k,v\nx,1.005\nx,2\n")[0])

    def test_check_reads_directory(self):
        import os
        import tempfile
        t = tasks.generate("spreadsheet", 1, 1)[0]
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(t.check(d)[0])
            with open(os.path.join(d, "output.csv"), "w") as f:
                f.write(t.expected["output.csv"])
            self.assertTrue(t.check(d)[0])


if __name__ == "__main__":
    unittest.main()
