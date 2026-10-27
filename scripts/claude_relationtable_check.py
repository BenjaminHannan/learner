#!/usr/bin/env python3
"""Checker for the relation table v1 (artifacts/claude-relationtable-20260922/).

Pure Python (json, ast, re, glob). No torch, no agent import, no writes
except stdout. It never opens reading94/reading94b data or the
naturalpanel208 test panels.

Checks (each prints PASS/FAIL; exit code 0 iff no FAIL):
  C1 no duplicate canonical names
  C2 no key (canonical, alias, storage key, inverse storage key; normalised
     like FakeEars._relation) belongs to two relations
  C3 every inverse phrasing is inside an existing relation, marked
     never_store with the "worked out backwards" label, has {Y} and no {X};
     every "narrower" and "generic" reference exists
  C4 every relation named in the code inventory (read by AST from the
     source files, not imported) and in the frozen suite/bench data is
     covered by the table or listed in inventory_exclusions with a reason
  C5 every template is well formed (known slots only, balanced brackets,
     the right slots for its kind); date relations carry the date rule
  C6 no expanded template string belongs to two relations unless both
     carry a value_guard that tells them apart
Info (not pass/fail): counts, and a table-only matcher run over the
evidence sentences from the task (this shows what the TABLE can read; it
says nothing about the agent, which is unchanged).

Run from the repo root:
  OMP_NUM_THREADS=1 python3 scripts/claude_relationtable_check.py
"""
from __future__ import annotations

import ast
import glob
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / "artifacts" / "claude-relationtable-20260922" / "relation_table_v1.json"
FORBIDDEN = ("reading94", "naturalpanel208")

SLOTS = {"X", "Y", "R", "WH"}
INVERSE_LABEL = "worked out backwards"


def key(surface: str) -> str:
    """Same rule as FakeEars._relation (scripts/fable_agent_loop.py:151)."""
    return "_".join(str(surface).strip().lower().split())


def _guard(path: Path) -> Path:
    if any(f in str(path) for f in FORBIDDEN):
        raise SystemExit(f"refusing to open forbidden path {path}")
    return path


# ------------------------------------------------------------ code inventory
# (file, constant, mode). Modes: strings = every str constant in the value
# except inside calls (so regex text is skipped); idx:N = element N of each
# tuple; keys / values / both = dict parts; literal:<k> = a fixed key.
CODE_SOURCES = [
    ("scripts/fable_agent_loop.py", "PERSON_RELATIONS", "strings"),
    ("scripts/fable_fix154_yesno.py", "SINGLE_VALUED_154", "strings"),
    ("scripts/fable_fix154_yesno.py", "_WHO_154", "strings"),
    ("scripts/fable_fix154c_allowlist.py", "MULTI_VALUED_154C", "strings"),
    ("scripts/fable_fix154e_allowlist.py", None, "literal:language"),
    ("scripts/fable_fix171_nameval.py", "NAME_KEYS", "strings"),
    ("scripts/fable_fix174_chainof.py", "REL174", "strings"),
    ("scripts/fable_fix190_reverse.py", "REVERSE_RELATIONS", "strings"),
    ("scripts/fable_fix190_reverse.py", "LIVES_RELATION", "strings"),
    ("scripts/fable_fix190_reverse.py", "BORN_RELATION", "strings"),
    ("scripts/fable_fix139e_tail.py", "LISTED_RELATIONS", "strings"),
    ("scripts/fable_fix166_me.py", "_SYNONYMS", "both"),
    ("scripts/fable_fix167_verb.py", "VERB_STATEMENTS", "idx:2"),
    ("scripts/fable_fix167d_verb.py", "VERB_STATEMENTS_167D", "idx:2"),
    ("scripts/fable_loop158b_agent.py", "WHEN_RELATIONS", "strings"),
    ("scripts/fable_loop158b_agent.py", "HOW_OLD_RELATION", "strings"),
    ("scripts/fable_loop158b_agent.py", "WHERE_FROM_CANDIDATES", "strings"),
    ("scripts/fable_loop158b_agent.py", "WHERE_LIVE_CANDIDATES", "strings"),
    ("scripts/fable_bench73_english_arm.py", "STATEMENT_PATTERNS", "strings"),
    ("scripts/fable_bench73_english_arm.py", "REV_OF_NOUNS", "both"),
    ("scripts/fable_bench73_english_arm.py", "REV_BY_VERBS", "values"),
    ("scripts/fable_bench73_english_arm.py", "REL_MENTION_CUES", "keys"),
    ("scripts/fable_bench92_english_arm.py", "EXTRA_STATEMENT_PATTERNS", "strings"),
    ("scripts/fable_bench92_english_arm.py", "EXTRA_REL_CUES", "keys"),
    ("scripts/fable_listening_english.py", "RELATION_MAP", "values"),
    ("scripts/fable_fix135_office.py", "OFFICE_RELATIONS", "strings"),
    ("scripts/fable_reasoner50.py", "CORE8", "strings"),
]


def _strings_no_calls(node) -> list[str]:
    out: list[str] = []

    def walk(n):
        if isinstance(n, ast.Call):
            return
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            out.append(n.value)
            return
        for child in ast.iter_child_nodes(n):
            walk(child)
    walk(node)
    return out


def code_inventory() -> dict[str, list[str]]:
    """relation key -> list of 'file:line CONST' where the code names it."""
    inv: dict[str, list[str]] = {}
    for path, const, mode in CODE_SOURCES:
        p = _guard(ROOT / path)
        if mode.startswith("literal:"):
            inv.setdefault(key(mode.split(":", 1)[1]), []).append(path)
            continue
        tree = ast.parse(p.read_text(encoding="utf-8"))
        found = False
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.Assign):
                targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                targets = [node.target.id]
            if const not in targets or node.value is None:
                continue
            found = True
            val = node.value
            if isinstance(val, ast.Call) and val.args:  # frozenset({...})
                val = val.args[0]
            names: list[str] = []
            if mode == "strings":
                names = _strings_no_calls(val)
            elif mode.startswith("idx:"):
                i = int(mode.split(":")[1])
                for elt in getattr(val, "elts", []):
                    if isinstance(elt, ast.Tuple) and len(elt.elts) > i and \
                            isinstance(elt.elts[i], ast.Constant):
                        names.append(elt.elts[i].value)
            elif isinstance(val, ast.Dict):
                ks = [k.value for k in val.keys if isinstance(k, ast.Constant)]
                vs = [v.value for v in val.values if isinstance(v, ast.Constant)
                      and isinstance(v.value, str)]
                names = {"keys": ks, "values": vs, "both": ks + vs}[mode]
            for n in names:
                inv.setdefault(key(n), []).append(f"{path}:{node.lineno} {const}")
        if not found:
            inv.setdefault(f"<MISSING CONST {const} in {path}>", []).append(path)
    return inv


# ----------------------------------------------------------- suite inventory
_POSS = re.compile(r"['’]s ([a-z][a-z]*(?: [a-z]+)?)(?= is\b| are\b|\?|['’]s)")
_OF = re.compile(r"\bthe ([a-z][a-z ]*?) of\b")
_MY = re.compile(r"\b[Mm]y ([a-z]+(?: [a-z]+)?) (?:is|are)\b")


def _english(text: str) -> list[str]:
    out = [m.group(1) for m in _POSS.finditer(text)]
    out += [m.group(1) for m in _OF.finditer(text)]
    out += [m.group(1) for m in _MY.finditer(text)]
    return out


def suite_inventory() -> dict[str, list[str]]:
    inv: dict[str, list[str]] = {}

    def add(src, name):
        k = key(name)
        if k:
            inv.setdefault(k, [])
            if src not in inv[k]:
                inv[k].append(src)
    # bench data: structured relation fields
    for pat in ("data/open/bench65/*.jsonl", "data/open/bench92/*.jsonl",
                "data/open/bench103/*.jsonl", "data/open/bench121/*.jsonl",
                "data/open/bench132/*.jsonl"):
        for f in sorted(glob.glob(str(ROOT / pat))):
            src = Path(f).parent.name
            for line in _guard(Path(f)).read_text(encoding="utf-8").splitlines():
                try:
                    row = json.loads(line)
                except ValueError:
                    continue
                for t in row.get("taught") or []:
                    if isinstance(t, dict) and t.get("relation"):
                        add(src, t["relation"])
                for r in (row.get("frame") or {}).get("relations") or []:
                    add(src, r)

    def walk(src, obj):
        if isinstance(obj, str):
            for n in _english(obj):
                add(src, n)
        elif isinstance(obj, list):
            for x in obj:
                walk(src, x)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                if k == "expect" and isinstance(v, list) and len(v) == 3:
                    add(src, v[1])
                elif k not in ("id", "family", "group", "note", "abstain_markers"):
                    walk(src, v)
    rt136 = ROOT / "artifacts/fable-redteam136-20260922/cases136.json"
    rt143 = ROOT / "artifacts/fable-redteam143-20260922/fable_redteam143_cases.json"
    s152 = ROOT / "scripts/fable_session152_sessions.py"
    walk("rt136", json.loads(_guard(rt136).read_text(encoding="utf-8")))
    walk("rt143", json.loads(_guard(rt143).read_text(encoding="utf-8"))["cases"])
    tree = ast.parse(_guard(s152).read_text(encoding="utf-8"))  # strings only, never imported
    doc = ast.get_docstring(tree, clean=False)
    walk("sessions152", [n.value for n in ast.walk(tree)
                         if isinstance(n, ast.Constant) and isinstance(n.value, str)
                         and n.value != doc])
    return inv


# ------------------------------------------------------------- templates
def template_slots(t: str) -> list[str]:
    return re.findall(r"\{([^{}]*)\}", t)


def well_formed(t: str) -> str | None:
    for s in template_slots(t):
        if s not in SLOTS:
            return f"unknown slot {{{s}}}"
    if re.search(r"\{[^{}]*$|^[^{}]*\}", t) or t.count("{") != t.count("}"):
        return "unbalanced braces"
    depth = {"(": 0, "[": 0}
    for ch in t:
        if ch in "([":
            depth[ch] += 1
        elif ch == ")":
            depth["("] -= 1
        elif ch == "]":
            depth["["] -= 1
        if min(depth.values()) < 0:
            return "unbalanced brackets"
    if any(depth.values()):
        return "unbalanced brackets"
    if "()" in t or "[]" in t or "(|" in t or "|)" in t:
        return "empty alternative"
    return None


def kind_rule(kind: str, t: str) -> str | None:
    s = set(template_slots(t))
    low = t.lower()
    first_person = bool(re.search(r"\b(my|i|am i)\b", low))
    has_x = "X" in s or first_person
    if kind == "teach":
        if not (has_x and "Y" in s):
            return "teach needs {X} (or my) and {Y}"
        if t.rstrip().endswith("?"):
            return "teach must not end with '?'"
    elif kind == "ask":
        if not has_x or "Y" in s:
            return "ask needs {X} (or my/I) and no {Y}"
        if not t.rstrip().endswith("?"):
            return "ask must end with '?'"
    elif kind == "yesno":
        if not (has_x and "Y" in s):
            return "yes/no needs {X} (or my) and {Y}"
        if not t.rstrip().endswith("?"):
            return "yes/no must end with '?'"
    elif kind == "inverse":
        if "Y" not in s or "X" in s:
            return "inverse needs {Y} and no {X}"
        if not t.rstrip().endswith("?"):
            return "inverse must end with '?'"
    return None


def surfaces(rel: dict) -> list[str]:
    return [rel["name"].replace("_", " ")] + list(rel["aliases"])


def expanded(rel: dict, table: dict) -> list[tuple[str, str, dict]]:
    """(kind, concrete template, pattern) for the relation, generic families included."""
    out = []
    pats = []
    for fam in rel["generic"]:
        for kind, lst in table["generic_patterns"][fam].items():
            pats += [(kind, p) for p in lst]
    for kind in ("teach", "ask", "yesno", "inverse"):
        pats += [(kind, p) for p in rel[kind]]
    for kind, p in pats:
        t = p["t"]
        rs = surfaces(rel) if "{R}" in t else [None]
        whs = rel["wh"] if "{WH}" in t else [None]
        for r in rs:
            for wh in whs:
                c = t
                if r is not None:
                    c = c.replace("{R}", r)
                if wh is not None:
                    c = c.replace("{WH}", wh)
                out.append((kind, c, p))
    return out


def norm_t(t: str) -> str:
    return " ".join(t.lower().rstrip(" .?!").split())


# ------------------------------------------------ table-only matcher (info)
def compile_template(t: str) -> re.Pattern:
    """Template -> regex. Slots become lazy named groups."""
    out, i = [], 0
    body = t.rstrip(" .?!")
    while i < len(body):
        ch = body[i]
        if ch == "{":
            j = body.index("}", i)
            name = body[i + 1:j]
            out.append(f"(?P<{name}>.+?)")
            i = j + 1
        elif ch == "(":
            j = body.index(")", i)
            alts = [re.escape(a) for a in body[i + 1:j].split("|")]
            out.append("(?:" + "|".join(alts) + ")")
            i = j + 1
        elif ch == "[":
            j = body.index("]", i)
            word = re.escape(body[i + 1:j])
            if j + 1 < len(body) and body[j + 1] == " ":
                out.append(f"(?:{word} )?")
                i = j + 2
            else:
                out.append(f"(?:{word})?")
                i = j + 1
        else:
            out.append(re.escape(ch))
            i += 1
    return re.compile("".join(out).replace("\\ ", " "), re.IGNORECASE)


_MONTHS = ("january february march april may june july august september october november december "
           "jan feb mar apr jun jul aug sep sept oct nov dec").split()


def looks_like_date(v: str) -> bool:
    """Tiny date shape test for the value guards (months, day+month, years)."""
    toks = re.findall(r"[a-z]+|\d+", v.lower())
    if not toks:
        return False
    return all(t in _MONTHS or t.isdigit() or t in ("st", "nd", "rd", "th", "of", "the")
               for t in toks) and any(t in _MONTHS or (t.isdigit() and len(t) == 4) for t in toks)


def guard_ok(rel: dict, value: str | None) -> bool:
    g = rel.get("value_guard") or ""
    if value is None:
        return True
    if g.startswith("value must look like a date"):
        return looks_like_date(value)
    if g.startswith("value must NOT look like a date"):
        return not looks_like_date(value)
    return True


def table_read(text: str, table: dict) -> list[str]:
    """Every (relation, kind, slots) reading the table allows for a turn."""
    t = " ".join(text.split())
    is_q = t.endswith("?")
    body = t.rstrip(" .?!")
    reads = []
    for rel in table["relations"]:
        for kind, c, p in expanded(rel, table):
            if (kind == "teach") == is_q:
                continue
            m = compile_template(c).fullmatch(body)
            if not m:
                continue
            g = {k: v for k, v in m.groupdict().items() if v}
            if "X" not in g and re.search(r"\b(my|i)\b", c.lower()):
                g["X"] = "<user>"
            if "Y" in g and rel.get("date_rule"):
                for w in rel["date_rule"]["strip_leading"]:
                    if g["Y"].lower().startswith(w + " "):
                        g["Y"] = g["Y"][len(w) + 1:]
            if not guard_ok(rel, g.get("Y")):
                continue
            tag = f"{rel['name']}/{kind}"
            if p.get("never_store"):
                tag += " [never_store: " + p["label"] + "]"
            reads.append(f"{tag} {g}")
    return sorted(set(reads))


EVIDENCE = [
    "Sam is the boss of Kim.",
    "Lena is the mother of Theo.",
    "Ada Pell is the composer of Blue Rain.",
    "Blue Rain's composer is Ada Pell.",
    "Who composed Blue Rain?",
    "What did Ada Pell compose?",
    "My birthday is in June.",
    "When is my birthday?",
    "Pia's birthday is in May.",
    "What is the manager of Kim?",
    "Who is Kim's manager?",
    "Sabine works at Acme.",
    "Who works at Acme?",
    "Who is Kim's?",
    "May is Tom's sister.",
    "Tom was born in May.",
]


# ------------------------------------------------------------------- main
def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else TABLE  # override only for self-tests
    table = json.loads(_guard(path).read_text(encoding="utf-8"))
    rels = table["relations"]
    by_name = {r["name"]: r for r in rels}
    fails = 0

    def report(tag, problems):
        nonlocal fails
        if problems:
            fails += 1
            print(f"FAIL {tag}: {len(problems)} problem(s)")
            for p in problems[:40]:
                print("   -", p)
        else:
            print(f"PASS {tag}")

    # C1
    names = [r["name"] for r in rels]
    report("C1 no duplicate canonical names",
           sorted({n for n in names if names.count(n) > 1}))

    # C2
    owner: dict[str, str] = {}
    probs = []
    for r in rels:
        ks = {key(r["name"])} | {key(a) for a in r["aliases"]} | \
             {key(s) for s in r["storage_keys"]} | {key(s) for s in r["inverse_storage_keys"]}
        for k in ks:
            if k in owner and owner[k] != r["name"]:
                probs.append(f"key '{k}' belongs to {owner[k]} and {r['name']}")
            owner.setdefault(k, r["name"])
    report("C2 no alias/storage key maps to two relations", probs)

    # C3
    probs = []
    for fam, parts in table["generic_patterns"].items():
        for p in parts.get("inverse", []):
            if p.get("never_store") is not True or p.get("label") != INVERSE_LABEL:
                probs.append(f"generic.{fam}: inverse '{p['t']}' not never_store + labelled")
    for r in rels:
        for p in r["inverse"]:
            if p.get("never_store") is not True:
                probs.append(f"{r['name']}: inverse '{p['t']}' not marked never_store")
            if p.get("label") != INVERSE_LABEL:
                probs.append(f"{r['name']}: inverse '{p['t']}' lacks label '{INVERSE_LABEL}'")
        for n in r["narrower"]:
            if n not in by_name:
                probs.append(f"{r['name']}: narrower '{n}' is not a relation")
        for fam in r["generic"]:
            if fam not in table["generic_patterns"]:
                probs.append(f"{r['name']}: generic family '{fam}' does not exist")
    report("C3 inverse phrasings point to existing relations, never stored, labelled", probs)

    # C4
    covered = set(owner)
    excl = table["inventory_exclusions"]

    def is_covered(k):
        if k in covered or k in excl:
            return True
        return any(e.endswith("*") and k.startswith(e[:-1]) for e in excl)
    code = code_inventory()
    suites = suite_inventory()
    probs = [f"code: '{k}' named at {v[0]}" for k, v in sorted(code.items()) if not is_covered(k)]
    probs += [f"suite: '{k}' seen in {v}" for k, v in sorted(suites.items()) if not is_covered(k)]
    report(f"C4 coverage of code inventory ({len(code)} keys) and suite/bench data ({len(suites)} keys)", probs)

    # C5
    probs = []
    all_templates = []
    for fam, parts in table["generic_patterns"].items():
        for kind, lst in parts.items():
            for p in lst:
                all_templates.append((f"generic.{fam}", kind, p))
    for r in rels:
        for kind in ("teach", "ask", "yesno", "inverse"):
            for p in r[kind]:
                all_templates.append((r["name"], kind, p))
        if r["value_kind"] == "date":
            dr = r.get("date_rule") or {}
            if sorted(dr.get("strip_leading", [])) != ["in", "on"] or "When" not in dr.get("when_question", ""):
                probs.append(f"{r['name']}: date relation without the in/on strip rule + When question")
            if "When" not in r["wh"]:
                probs.append(f"{r['name']}: date relation must allow 'When'")
        if r["cardinality"] not in ("single", "multi"):
            probs.append(f"{r['name']}: bad cardinality")
    for owner_name, kind, p in all_templates:
        e = well_formed(p["t"]) or kind_rule(kind, p["t"])
        if e:
            probs.append(f"{owner_name}.{kind}: '{p['t']}': {e}")
        if p.get("where") not in ("live", "layer_c", "not_live", "NEW"):
            probs.append(f"{owner_name}.{kind}: '{p['t']}': bad 'where'")
        try:
            compile_template(p["t"].replace("{WH}", "What").replace("{R}", "boss"))
        except (re.error, ValueError) as exc:
            probs.append(f"{owner_name}.{kind}: '{p['t']}': does not compile ({exc})")
    report(f"C5 templates well formed ({len(all_templates)} templates)", probs)

    # C6
    seen: dict[tuple[str, str], set[str]] = {}
    for r in rels:
        for kind, c, _p in expanded(r, table):
            cls = "statement" if kind == "teach" else "question"
            seen.setdefault((cls, norm_t(c)), set()).add(r["name"])
    probs = []
    for (cls, t), owners in sorted(seen.items()):
        if len(owners) > 1:
            unguarded = [o for o in owners if not by_name[o].get("value_guard")]
            if unguarded:
                probs.append(f"'{t}' ({cls}) read by {sorted(owners)}; no value_guard on {unguarded}")
    report("C6 no expanded template shared by two relations without a value guard", probs)

    # ----- info
    n_new = sum(1 for r in rels if r["status"] == "NEW")
    n_alias = sum(len(r["aliases"]) for r in rels)
    n_rel_specific = sum(len(r[k]) for r in rels for k in ("teach", "ask", "yesno", "inverse"))
    n_generic = sum(len(v) for parts in table["generic_patterns"].values() for v in parts.values())
    n_expanded = sum(len(expanded(r, table)) for r in rels)
    n_inverse_specific = sum(len(r["inverse"]) for r in rels)
    where_counts: dict[str, int] = {}
    for _o, _k, p in all_templates:
        where_counts[p["where"]] = where_counts.get(p["where"], 0) + 1
    print()
    print("INFO counts")
    print(f"  relations: {len(rels)} (NEW: {n_new}; known: {len(rels) - n_new})")
    print(f"  NEW relations: {', '.join(r['name'] for r in rels if r['status'] == 'NEW')}")
    print(f"  aliases: {n_alias}; storage keys beyond canonical: "
          f"{sum(len(r['storage_keys']) - 1 for r in rels)}; inverse storage keys: "
          f"{sum(len(r['inverse_storage_keys']) for r in rels)}")
    print(f"  written templates: {len(all_templates)} ({n_generic} generic + {n_rel_specific} relation-specific, "
          f"of which {n_inverse_specific} relation-specific inverse)")
    print(f"  templates by status: {dict(sorted(where_counts.items()))}")
    print(f"  expanded per-relation patterns (generic x surfaces x wh): {n_expanded}")
    print(f"  code inventory keys: {len(code)}; suite/bench keys: {len(suites)}; exclusions: {len(excl)}")
    print()
    print("INFO table-only matcher on the task's evidence sentences (NOT the agent):")
    for s in EVIDENCE:
        reads = table_read(s, table)
        print(f"  {s!r}: {len(reads)} reading(s)")
        for rd in reads[:6]:
            print(f"      {rd}")
        if len(reads) > 6:
            print(f"      ... {len(reads) - 6} more")
    print()
    print("RESULT:", "PASS (all checks)" if fails == 0 else f"FAIL ({fails} check(s) failed)")
    return 0 if fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
