"""Task families with exact automatic checkers (v1: spreadsheets on CSV)."""
from __future__ import annotations

import csv
import io
import os
import random
from dataclasses import dataclass

FIRST = ["Ana", "Ben", "Cara", "Dev", "Eli", "Fay", "Gus", "Hana", "Ivan", "Jo", "Kim", "Leo",
         "Mia", "Noor", "Omar", "Pia", "Quin", "Rosa", "Sam", "Tess", "Uma", "Vic", "Wes", "Zoe"]
LAST = ["Adams", "Brown", "Chen", "Diaz", "Evans", "Fox", "Gupta", "Hill", "Ito", "Jones",
        "Khan", "Lopez", "Moore", "Nash", "Ortiz", "Park", "Reyes", "Stone", "Tran", "Wu"]
REGIONS = ["East", "North", "South", "West"]
PRODUCTS = {"Bolt": 1.25, "Cable": 7.5, "Drill": 49.99, "Gear": 12.4, "Hinge": 3.2, "Lamp": 21.0}
CATS = ["Food", "Fuel", "Office", "Rent", "Travel", "Utilities"]
VENDORS = ["Acme", "Bluebird", "Cobalt", "Delta", "Everest"]
CITIES = ["Austin", "Boston", "Chicago", "Denver", "Fresno"]
CLASSES = ["Art", "Biology", "Chemistry", "Drama", "English"]


def _fmt(x) -> str:
    if isinstance(x, float):
        return ("%.6f" % x).rstrip("0").rstrip(".")
    return "" if x is None else str(x)


def to_csv(header, rows) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows([[_fmt(c) for c in r] for r in rows])
    return buf.getvalue()


def _num(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def compare_csv(expected: str, got: str, ordered: bool = True):
    """Header exact; numbers within half a cent; row order only if `ordered`."""
    def parse(t):
        rows = [[c.strip() for c in r] for r in csv.reader(io.StringIO(t))]
        return [r for r in rows if r]
    try:
        e, g = parse(expected), parse(got)
    except csv.Error as ex:
        return False, "output.csv is not valid CSV: %s" % ex
    if not g:
        return False, "output.csv is empty"
    if g[0] != e[0]:
        return False, "header mismatch: expected %s, got %s" % (e[0], g[0])
    er, gr = e[1:], g[1:]
    if len(er) != len(gr):
        return False, "expected %d data rows, got %d" % (len(er), len(gr))
    if not ordered:
        er, gr = sorted(er, key=lambda r: r[0]), sorted(gr, key=lambda r: r[0])
    for i, (a, b) in enumerate(zip(er, gr)):
        ok = len(a) == len(b)
        for x, y in (zip(a, b) if ok else ()):
            nx, ny = _num(x), _num(y)
            if nx is not None and ny is not None and x and y:
                ok = ok and abs(nx - ny) <= 0.0051
            else:
                ok = ok and x == y
        if not ok:
            return False, "row %d differs: expected %s, got %s" % (i + 1, a, b)
    return True, "ok"


@dataclass
class Task:
    id: str
    kind: str
    family: str
    instruction: str
    files: dict
    expected: dict
    ordered: bool = True

    def check(self, out) -> tuple:
        """out: sandbox directory path, or dict name -> text (RunResult.files_out)."""
        if isinstance(out, dict):
            got = out.get("output.csv")
        else:
            try:
                with open(os.path.join(str(out), "output.csv"), encoding="utf-8", newline="") as f:
                    got = f.read()
            except OSError:
                got = None
        if got is None:
            return False, "output.csv was not written"
        return compare_csv(self.expected["output.csv"], got, self.ordered)


# ---------- data generators ----------

def _sales(rng, n):
    rows = []
    for _ in range(n):
        p = rng.choice(sorted(PRODUCTS))
        rows.append(["2025-%02d-%02d" % (rng.randint(1, 12), rng.randint(1, 28)), rng.choice(REGIONS),
                     p, rng.randint(1, 20), PRODUCTS[p]])
    return ["date", "region", "product", "units", "price"], rows


def _expenses(rng, n, months=((2025, 11), (2025, 12), (2026, 1), (2026, 2))):
    rows = []
    for _ in range(n):
        y, m = rng.choice(months)
        rows.append(["%d-%02d-%02d" % (y, m, rng.randint(1, 28)), rng.choice(CATS),
                     rng.choice(VENDORS), round(rng.uniform(5, 300), 2)])
    return ["date", "category", "vendor", "amount"], rows


def _grades(rng, n):
    names = rng.sample([f + " " + l for f in FIRST for l in LAST], n)
    return ["student", "class", "score"], [[s, rng.choice(CLASSES), rng.randint(40, 100)] for s in names]


def _people(rng, n):
    names = rng.sample([(f, l) for f in FIRST for l in LAST], n)
    rows = [[i + 1, "%s %s" % nm, "%s.%s@example.com" % (nm[0].lower(), nm[1].lower()), rng.choice(CITIES)]
            for i, nm in enumerate(names)]
    return ["id", "full_name", "email", "city"], rows


def _spec(header, rule):
    return ("Write output.csv with exactly these columns in this order: %s. %s "
            "Round computed money/average values to 2 decimal places." % (",".join(header), rule))


def _t(intro, files, out_header, out_rows, rule, ordered=True):
    desc = " ".join("Input file %s has columns: %s." % (n, t.splitlines()[0]) for n, t in files.items())
    return dict(instruction="%s %s %s" % (intro, desc, _spec(out_header, rule)), files=files,
                header=out_header, rows=out_rows, ordered=ordered)


# ---------- families ----------

def f_sum_by_group(rng):
    h, rows = _expenses(rng, rng.randint(25, 40))
    tot = {}
    for r in rows:
        tot[r[1]] = tot.get(r[1], 0) + r[3]
    return _t("Total the expenses for each category.", {"expenses.csv": to_csv(h, rows)},
              ["category", "total_amount"], [[k, v] for k, v in tot.items()],
              "One row per category, in any row order.", False)


def f_avg_by_group(rng):
    h, rows = _grades(rng, rng.randint(20, 30))
    g = {}
    for r in rows:
        g.setdefault(r[1], []).append(r[2])
    return _t("Compute the average score for each class.", {"grades.csv": to_csv(h, rows)},
              ["class", "avg_score"], [[k, sum(v) / len(v)] for k, v in sorted(g.items())],
              "One row per class, sorted by class name ascending (A to Z).")


def f_filter_rows(rng):
    h, rows = _sales(rng, rng.randint(25, 40))
    pick = rng.choice(rows)
    reg, m = pick[1], pick[3]
    out = [r for r in rows if r[1] == reg and r[3] >= m]
    return _t("Keep only the sales rows whose region is exactly %s and whose units are at least %d (units >= %d)."
              % (reg, m, m), {"sales.csv": to_csv(h, rows)}, h, out,
              "Keep the input columns unchanged and the rows in their original input order.")


def f_dedupe_key(rng):
    h, rows = _people(rng, 14)
    out = [list(r) for r in rows]
    for r in rng.sample(rows, 5):
        d = list(r)
        d[2] = d[2].upper()
        out.insert(rng.randint(r[0], len(out)), d)
    for i, r in enumerate(out):
        r[0] = i + 1
    seen, keep = set(), []
    for r in out:
        if r[2].lower() not in seen:
            seen.add(r[2].lower())
            keep.append(r)
    return _t("Remove duplicate contacts. Two rows are duplicates when their email addresses are equal ignoring upper/lower case; keep the first occurrence.",
              {"contacts.csv": to_csv(h, out)}, h, keep,
              "Keep the input columns unchanged and the rows in their original input order.")


def f_join_lookup(rng):
    products = [["P%d" % (i + 1), n, p] for i, (n, p) in enumerate(sorted(PRODUCTS.items()))]
    orders = [["O%03d" % (i + 1), rng.choice(products)[0], rng.randint(1, 9)] for i in range(rng.randint(15, 25))]
    look = {p[0]: p for p in products}
    out = [[o[0], look[o[1]][1], o[2], o[2] * look[o[1]][2]] for o in orders]
    files = {"orders.csv": to_csv(["order_id", "product_id", "qty"], orders),
             "products.csv": to_csv(["product_id", "name", "price"], products)}
    return _t("Look up each order's product in the products table; line_total is qty times price.", files,
              ["order_id", "name", "qty", "line_total"], out, "One row per order, in the original orders.csv order.")


def f_computed_column(rng):
    h, rows = _sales(rng, rng.randint(15, 30))
    return _t("Add a revenue column equal to units times price.", {"sales.csv": to_csv(h, rows)},
              h + ["revenue"], [r + [r[3] * r[4]] for r in rows],
              "Keep the input columns first, then revenue last, rows in original input order.")


def f_sort_two_keys(rng):
    h, rows = _grades(rng, rng.randint(15, 25))
    rows = [[r[0], r[1], rng.choice([60, 70, 80, 90])] for r in rows]
    out = sorted(rows, key=lambda r: (r[1], -r[2], r[0]))
    return _t("Sort the students.", {"grades.csv": to_csv(h, rows)}, h, out,
              "Keep the input columns unchanged. Sorted by class ascending, then score descending (highest first), then student ascending (A to Z).")


def f_monthly_totals(rng):
    h, rows = _expenses(rng, rng.randint(25, 40))
    tot = {}
    for r in rows:
        tot[r[0][:7]] = tot.get(r[0][:7], 0) + r[3]
    return _t("Total the expenses per calendar month (month is the date as YYYY-MM).",
              {"expenses.csv": to_csv(h, rows)}, ["month", "total_amount"], sorted(tot.items()),
              "One row per month that has expenses, sorted by month ascending.")


def f_top_n_per_group(rng):
    h, rows = _grades(rng, rng.randint(20, 30))
    rows = [[r[0], r[1], rng.choice([55, 65, 75, 85, 95])] for r in rows]
    out = []
    for c in sorted({r[1] for r in rows}):
        g = sorted((r for r in rows if r[1] == c), key=lambda r: (-r[2], r[0]))[:2]
        out += [[c, r[0], r[2]] for r in g]
    return _t("For each class keep the 2 highest-scoring students; ties are broken by student name ascending (A to Z). A class with fewer than 2 students keeps all of them.",
              {"grades.csv": to_csv(h, rows)}, ["class", "student", "score"], out,
              "Sorted by class ascending, then score descending, then student ascending.")


def f_percent_change(rng):
    v, rows = 1000.0, []
    for i in range(rng.randint(8, 12)):
        v = round(v * rng.uniform(0.8, 1.25), 2)
        rows.append(["2025-%02d" % (i + 1), v])
    out = [[m, r, "" if i == 0 else (r - rows[i - 1][1]) / rows[i - 1][1] * 100] for i, (m, r) in enumerate(rows)]
    return _t("Add the month-over-month percent change of revenue: (this month - previous month) / previous month * 100.",
              {"monthly.csv": to_csv(["month", "revenue"], rows)}, ["month", "revenue", "pct_change"], out,
              "Rows in original order; pct_change is empty for the first month.")


def f_fill_missing(rng):
    h, rows = _grades(rng, rng.randint(20, 30))
    for c in CLASSES:  # every class gets at least three students
        while sum(1 for r in rows if r[1] == c) < 3:
            rng.choice(rows)[1] = c
    miss = set(rng.sample(range(len(rows)), 5))
    mean = {}
    for c in CLASSES:
        v = [r[2] for i, r in enumerate(rows) if r[1] == c and i not in miss]
        mean[c] = sum(v) / len(v) if v else 0
    inp = [[r[0], r[1], "" if i in miss else r[2]] for i, r in enumerate(rows)]
    out = [[r[0], r[1], mean[r[1]] if i in miss else r[2]] for i, r in enumerate(rows)]
    return _t("Some scores are missing (empty). Fill each missing score with the mean of the non-missing scores of the same class.",
              {"grades.csv": to_csv(h, inp)}, h, out, "Keep the input columns unchanged and the rows in original order.")


def f_split_fullname(rng):
    h, rows = _people(rng, rng.randint(12, 20))
    inp, out = [], []
    for r in rows:
        f, l = r[1].split()
        inp.append([r[0], "%s, %s" % (l, f) if rng.random() < 0.4 else r[1], r[2], r[3]])
        out.append([r[0], f, l, r[2]])
    return _t("Split full_name into first and last name. full_name is either 'First Last' or 'Last, First'.",
              {"contacts.csv": to_csv(h, inp)}, ["id", "first_name", "last_name", "email"], out,
              "Rows in original order.")


# ---------- registry ----------

REGISTRY: dict = {}


def register(kind: str, family: str, fn) -> None:
    REGISTRY.setdefault(kind, {})[family] = fn


def registered_kinds() -> list:
    return sorted(REGISTRY)


def families(kind: str) -> list:
    return sorted(REGISTRY.get(kind, {}))


for _f in (f_sum_by_group, f_avg_by_group, f_filter_rows, f_dedupe_key, f_join_lookup, f_computed_column,
           f_sort_two_keys, f_monthly_totals, f_top_n_per_group, f_percent_change, f_fill_missing,
           f_split_fullname):
    register("spreadsheet", _f.__name__[2:], _f)


def generate(kind: str, n: int, seed: int = 0) -> list:
    fams = families(kind)
    out = []
    for i in range(n if fams else 0):
        fam = fams[i % len(fams)]
        d = REGISTRY[kind][fam](random.Random("%s|%s|%s" % (seed, i, fam)))
        out.append(Task("%s-%s-%d" % (fam, seed, i), kind, fam, d["instruction"], d["files"],
                        {"output.csv": to_csv(d["header"], d["rows"])}, d["ordered"]))
    return out
