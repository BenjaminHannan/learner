#!/usr/bin/env python3
"""Build chainpanel266b (exp 266b blind panel, reasoning line).

Writes artifacts/claude-chainpanel266b-20260923/panel.jsonl (70 items).

Item: {"id", "family", "setup", "question", "gold", "note"}.
Teaches are plain only ("A's R is B.", "My R is B.").

Usage (run from the repo root):
  uv run --offline --no-project --python 3.12 --with torch --with numpy \
    python -B artifacts/claude-chainpanel266b-20260923/make_panel.py
  ... make_panel.py --check   # verify every setup stores as expected on base 266

Families and counts (70 total):
  multiword_chain 24 (18 two-word heads, 6 three-word heads; 6 per kept form)
  three_link 8 (6 two-word heads, 2 one-word heads)
  oneword_chain 8 (one-word heads, 2 per kept form)
  my_live 4
  broken_chain 12 (8 two-word-start incl. 2 last-word traps, 2 one-word, 2 my-)
  plain_control 8 (5 who-is with two-word heads, 3 where-forms with one-word heads)
  statement_control 6 (no "?", verified no-write on the base)
"""

import json
import sys
from pathlib import Path

OUT = Path("artifacts/claude-chainpanel266b-20260923/panel.jsonl")

ITEMS = []
_counter = [0]


def add(family, setup, question, gold, note):
    _counter[0] += 1
    ITEMS.append({
        "id": f"c266b-{_counter[0]:03d}",
        "family": family,
        "setup": list(setup),
        "question": question,
        "gold": list(gold),
        "note": note,
    })


def T(a, r, b):
    return f"{a}'s {r} is {b}."


def MY(r, b):
    return f"My {r} is {b}."


MW = "multiword_chain"
TH = "three_link"
OW = "oneword_chain"
ML = "my_live"
BR = "broken_chain"
PC = "plain_control"
ST = "statement_control"

# ---------------- multiword_chain: live form x6 ----------------
add(MW, [T("Mara Voss", "boss", "Ivo"), T("Ivo", "city", "Reno")],
    "Where does Mara Voss's boss live?", ["Reno"], "two-link live chain")
add(MW, [T("Petra Lind", "mother", "Wren"), T("Wren", "city", "Oslo")],
    "Where does Petra Lind's mother live?", ["Oslo"], "two-link live chain")
add(MW, [T("Soren Dahl", "sister", "Dara"), T("Dara", "city", "Lima")],
    "Where does Soren Dahl's sister live?", ["Lima"], "two-link live chain")
add(MW, [T("Anouk Vermeer", "friend", "Quill"), T("Quill", "city", "Quito")],
    "Where does Anouk Vermeer's friend live?", ["Quito"], "two-link live chain")
add(MW, [T("Jelmer Bos", "dentist", "Bram"), T("Bram", "city", "Tulsa")],
    "Where does Jelmer Bos's dentist live?", ["Tulsa"], "two-link live chain")
add(MW, [T("Elena Mara Voss", "coach", "Soren"), T("Soren", "city", "Fargo")],
    "Where does Elena Mara Voss's coach live?", ["Fargo"], "three-word head live chain")

# ---------------- multiword_chain: who-is form x6 ----------------
add(MW, [T("Fenna Groot", "boss", "Ivo"), T("Ivo", "mother", "Dara")],
    "Who is Fenna Groot's boss's mother?", ["Dara"], "two-link who chain")
add(MW, [T("Kasper Molen", "father", "Omar"), T("Omar", "boss", "Wren")],
    "Who is Kasper Molen's father's boss?", ["Wren"], "two-link who chain")
add(MW, [T("Ines Serrano", "sister", "Lena"), T("Lena", "coach", "Quill")],
    "Who is Ines Serrano's sister's coach?", ["Quill"], "two-link who chain")
add(MW, [T("Omar Haddad", "brother", "Tomas"), T("Tomas", "dentist", "Bram")],
    "Who is Omar Haddad's brother's dentist?", ["Bram"], "two-link who chain")
add(MW, [T("Priya Nair", "friend", "Nadia"), T("Nadia", "sister", "Lena")],
    "Who is Priya Nair's friend's sister?", ["Lena"], "two-link who chain")
add(MW, [T("Pieter Jan Bos", "neighbour", "Jeroen"), T("Jeroen", "brother", "Mikko")],
    "Who is Pieter Jan Bos's neighbour's brother?", ["Mikko"], "three-word head who chain")

# ---------------- multiword_chain: work form x6 ----------------
add(MW, [T("Tomas Reyes", "boss", "Ivo"), T("Ivo", "employer", "Acme")],
    "Where does Tomas Reyes's boss work?", ["Acme"], "two-link work chain")
add(MW, [T("Nadia Koster", "mother", "Wren"), T("Wren", "employer", "Globex")],
    "Where does Nadia Koster's mother work?", ["Globex"], "two-link work chain")
add(MW, [T("Lena Fischer", "father", "Dara"), T("Dara", "employer", "Initech")],
    "Where does Lena Fischer's father work?", ["Initech"], "two-link work chain")
add(MW, [T("Mikko Aho", "sister", "Quill"), T("Quill", "employer", "Hooli")],
    "Where does Mikko Aho's sister work?", ["Hooli"], "two-link work chain")
add(MW, [T("Maria Luisa Reyes", "friend", "Bram"), T("Bram", "employer", "Umbrella")],
    "Where does Maria Luisa Reyes's friend work?", ["Umbrella"], "three-word head work chain")
add(MW, [T("Anna Sofia Lind", "coach", "Lothar"), T("Lothar", "employer", "Stark")],
    "Where does Anna Sofia Lind's coach work?", ["Stark"], "three-word head work chain")

# ---------------- multiword_chain: work-for form x6 ----------------
add(MW, [T("Bram Jansen", "brother", "Ivo"), T("Ivo", "employer", "Tyrell")],
    "Who does Bram Jansen's brother work for?", ["Tyrell"], "two-link work-for chain")
add(MW, [T("Saskia Vos", "neighbour", "Wren"), T("Wren", "employer", "Gekko")],
    "Who does Saskia Vos's neighbour work for?", ["Gekko"], "two-link work-for chain")
add(MW, [T("Marit Dekker", "dentist", "Dara"), T("Dara", "employer", "Wayne")],
    "Who does Marit Dekker's dentist work for?", ["Wayne"], "two-link work-for chain")
add(MW, [T("Thijs Kuiper", "wife", "Quill"), T("Quill", "employer", "Massive")],
    "Who does Thijs Kuiper's wife work for?", ["Massive"], "two-link work-for chain")
add(MW, [T("Jan Willem Groot", "husband", "Soren"), T("Soren", "employer", "Globex")],
    "Who does Jan Willem Groot's husband work for?", ["Globex"], "three-word head work-for chain")
add(MW, [T("Rosa Maria Serrano", "friend", "Petra"), T("Petra", "employer", "Initech")],
    "Who does Rosa Maria Serrano's friend work for?", ["Initech"], "three-word head work-for chain")

# ---------------- three_link x8 ----------------
add(TH, [T("Eva Smit", "boss", "Ivo"), T("Ivo", "mother", "Dara"), T("Dara", "city", "Reno")],
    "Where does Eva Smit's boss's mother live?", ["Reno"], "three-link live chain")
add(TH, [T("Ruben Maas", "sister", "Lena"), T("Lena", "coach", "Quill"), T("Quill", "city", "Oslo")],
    "Where does Ruben Maas's sister's coach live?", ["Oslo"], "three-link live chain")
add(TH, [T("Noor", "friend", "Nadia"), T("Nadia", "dentist", "Bram"), T("Bram", "city", "Lima")],
    "Where does Noor's friend's dentist live?", ["Lima"], "one-word head three-link live")
add(TH, [T("Daan Verhoeven", "mother", "Wren"), T("Wren", "sister", "Lena"), T("Lena", "coach", "Ines")],
    "Who is Daan Verhoeven's mother's sister's coach?", ["Ines"], "three-link who chain")
add(TH, [T("Sem", "father", "Omar"), T("Omar", "brother", "Tomas"), T("Tomas", "dentist", "Nadia")],
    "Who is Sem's father's brother's dentist?", ["Nadia"], "one-word head three-link who")
add(TH, [T("Isa Bakker", "coach", "Petra"), T("Petra", "sister", "Lena"), T("Lena", "employer", "Stark")],
    "Where does Isa Bakker's coach's sister work?", ["Stark"], "three-link work chain")
add(TH, [T("Stijn Willems", "friend", "Dara"), T("Dara", "brother", "Tomas"), T("Tomas", "employer", "Wayne")],
    "Where does Stijn Willems's friend's brother work?", ["Wayne"], "three-link work chain")
add(TH, [T("Lotte Visser", "sister", "Quill"), T("Quill", "mother", "Nadia"), T("Nadia", "employer", "Umbrella")],
    "Who does Lotte Visser's sister's mother work for?", ["Umbrella"], "three-link work-for chain")

# ---------------- oneword_chain x8 ----------------
add(OW, [T("Jeroen", "boss", "Ivo"), T("Ivo", "city", "Delft")],
    "Where does Jeroen's boss live?", ["Delft"], "one-word head live chain")
add(OW, [T("Marit", "sister", "Wren"), T("Wren", "city", "Ghent")],
    "Where does Marit's sister live?", ["Ghent"], "one-word head live chain")
add(OW, [T("Thijs", "father", "Omar"), T("Omar", "boss", "Dara")],
    "Who is Thijs's father's boss?", ["Dara"], "one-word head who chain")
add(OW, [T("Eva", "friend", "Quill"), T("Quill", "coach", "Bram")],
    "Who is Eva's friend's coach?", ["Bram"], "one-word head who chain")
add(OW, [T("Ruben", "dentist", "Lothar"), T("Lothar", "employer", "Tyrell")],
    "Where does Ruben's dentist work?", ["Tyrell"], "one-word head work chain")
add(OW, [T("Noor", "coach", "Ines"), T("Ines", "employer", "Gekko")],
    "Where does Noor's coach work?", ["Gekko"], "one-word head work chain")
add(OW, [T("Fleur", "neighbour", "Petra"), T("Petra", "employer", "Hooli")],
    "Who does Fleur's neighbour work for?", ["Hooli"], "one-word head work-for chain")
add(OW, [T("Daan", "wife", "Lena"), T("Lena", "employer", "Massive")],
    "Who does Daan's wife work for?", ["Massive"], "one-word head work-for chain")

# ---------------- my_live x4 ----------------
add(ML, [MY("boss", "Ivo"), T("Ivo", "city", "Braga")],
    "Where does my boss live?", ["Braga"], "user-anchored live chain")
add(ML, [MY("sister", "Wren"), T("Wren", "city", "Porto")],
    "Where does my sister live?", ["Porto"], "user-anchored live chain")
add(ML, [MY("friend", "Quill"), T("Quill", "city", "Nice")],
    "Where does my friend live?", ["Nice"], "user-anchored live chain")
add(ML, [MY("dentist", "Bram"), T("Bram", "city", "Turin")],
    "Where does my dentist live?", ["Turin"], "user-anchored live chain")

# ---------------- broken_chain x12 ----------------
add(BR, [T("Mara Voss", "boss", "Ivo")],
    "Where does Mara Voss's boss live?", [], "second link never taught")
add(BR, [T("Ivo", "city", "Reno")],
    "Where does Petra Lind's boss live?", [], "first link never taught")
add(BR, [T("Soren Dahl", "friend", "Quill"), T("Quill", "city", "Quito")],
    "Where does Soren Dahl's boss live?", [], "link taught under another relation")
add(BR, [T("Anouk Vermeer", "boss", "Ivo")],
    "Who is Anouk Vermeer's boss's mother?", [], "second link never taught")
add(BR, [T("Jelmer Bos", "sister", "Wren"), T("Wren", "mother", "Dara")],
    "Who is Jelmer Bos's boss's mother?", [], "link taught under another relation")
add(BR, [T("Voss", "boss", "Ivo"), T("Ivo", "city", "Reno")],
    "Where does Mara Voss's boss live?", [], "head never taught, last word is another person")
add(BR, [T("Lind", "sister", "Wren"), T("Wren", "coach", "Quill")],
    "Who is Petra Lind's sister's coach?", [], "head never taught, last word is another person")
add(BR, [T("Fenna Groot", "dentist", "Bram")],
    "Where does Fenna Groot's dentist work?", [], "second link never taught")
add(BR, [T("Jeroen", "friend", "Ivo"), T("Ivo", "city", "Delft")],
    "Where does Jeroen's boss live?", [], "link taught under another relation")
add(BR, [T("Marit", "boss", "Omar")],
    "Who is Marit's boss's father?", [], "second link never taught")
add(BR, [MY("friend", "Quill"), T("Quill", "city", "Nice")],
    "Where does my boss live?", [], "link taught under another relation")
add(BR, [MY("dentist", "Bram")],
    "Who is my dentist's sister?", [], "second link never taught")

# ---------------- plain_control x8 ----------------
add(PC, [T("Petra Lind", "boss", "Dara")],
    "Who is Petra Lind's boss?", ["Dara"], "direct who control")
add(PC, [T("Soren Dahl", "mother", "Wren")],
    "Who is Soren Dahl's mother?", ["Wren"], "direct who control")
add(PC, [T("Anouk Vermeer", "dentist", "Bram")],
    "Who is Anouk Vermeer's dentist?", ["Bram"], "direct who control")
add(PC, [T("Jelmer Bos", "coach", "Quill")],
    "Who is Jelmer Bos's coach?", ["Quill"], "direct who control")
add(PC, [T("Fenna Groot", "sister", "Lena")],
    "Who is Fenna Groot's sister?", ["Lena"], "direct who control")
add(PC, [T("Jeroen", "city", "Mainz")],
    "Where does Jeroen live?", ["Mainz"], "direct live control")
add(PC, [T("Marit", "employer", "Stark")],
    "Where does Marit work?", ["Stark"], "direct work control")
add(PC, [T("Thijs", "employer", "Wayne")],
    "Who does Thijs work for?", ["Wayne"], "direct work-for control")

# ---------------- statement_control x6 ----------------
add(ST, [T("Mara Voss", "boss", "Ivo"), T("Ivo", "city", "Reno")],
    "Mara Voss's boss lives in Reno.", [], "statement with chain, no write")
add(ST, [T("Petra Lind", "sister", "Wren"), T("Wren", "city", "Oslo")],
    "Yesterday I met Petra Lind's sister in Oslo.", [], "statement with chain, no write")
add(ST, [T("Soren Dahl", "boss", "Ivo"), T("Ivo", "city", "Lima")],
    "Soren Dahl's boss is Ivo.", [], "restated taught fact, no write")
add(ST, [T("Anouk Vermeer", "dentist", "Bram"), T("Bram", "city", "Quito")],
    "I think Anouk Vermeer's dentist likes Quito.", [], "statement with chain, no write")
add(ST, [T("Jelmer Bos", "coach", "Quill"), T("Quill", "city", "Tulsa")],
    "Jelmer Bos's coach's city is Tulsa.", [], "statement with chain, no write")
add(ST, [T("Fenna Groot", "friend", "Dara"), T("Dara", "employer", "Acme")],
    "I heard Fenna Groot's friend likes Acme.", [], "statement with chain, no write")


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for it in ITEMS:
            f.write(json.dumps(it, ensure_ascii=True) + "\n")
    print(f"Wrote {len(ITEMS)} items to {OUT}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        sys.path.insert(0, "scripts")
        import tempfile
        import claude_loop266_agent as A266

        base = json.load(open("artifacts/claude-chain266-20260923/loop266-config.json"))

        def fresh():
            cfg = dict(base)
            cfg["sleep_threshold"] = 100000
            cfg["state_dir"] = tempfile.mkdtemp(prefix="c266b-chk-")
            return A266.build_agent266(cfg)

        def triples(loop):
            return [[s, r, v] for _, s, r, v in loop.nb.nb._triples]

        def parse_teach(t):
            assert t.endswith("."), t
            core = t[:-1]
            if core.startswith("My "):
                rel, val = core[3:].split(" is ")
                return ("USER", rel, val)
            left, val = core.split(" is ")
            idx = left.find("'s ")
            assert idx > 0, t
            return (left[:idx], left[idx + 3:], val)

        bad = 0
        for it in ITEMS:
            loop = fresh()
            reps = [" ".join(loop.turn(t)) for t in it["setup"]]
            st = triples(loop)
            exp = [list(parse_teach(t)) for t in it["setup"]]
            ok = (st == exp)
            nowrite_ok = True
            if it["family"] == "statement_control":
                before = [list(x) for x in st]
                r = " ".join(loop.turn(it["question"]))
                after = triples(loop)
                nowrite_ok = (before == after)
                if not nowrite_ok:
                    print(f"WRITE {it['id']} stmt-reply={r!r} before={before} after={after}")
            if not ok or not nowrite_ok:
                bad += 1
                print(f"MISMATCH {it['id']} replies={reps!r}")
                print(f"  stored={st}")
                print(f"  expect={exp}")
        print(f"checked {len(ITEMS)} items, {bad} bad")
        sys.exit(1 if bad else 0)
    main()
