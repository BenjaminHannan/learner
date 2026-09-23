"""Exp 243 (diagnosis only): call the 138 question composers directly on
each failing case, with the exact triples the notebook holds.

Loop138Ears._hear_question (scripts/fable_loop138_agent.py:115) asks
B92.compose_n_hop first, then B73.compose_question, each gated by
L113C.frame_consumes_question; this prints what each returns.
"""
import sys
sys.path.insert(0, "scripts")
import fable_loop138_agent as L  # noqa: E402

B92, B73, L113C, L113 = L.B92, L.B73, L.L113C, L.L113
J = ("Joren Hale", "spouse", "Sella Marne")
S = ("Sella Marne", "country_of_citizenship", "Tormeil")
T = ("Tormeil", "capital", "Northgate")
CASES = [
    ("Who is Joren Hale married to?", [J]),
    ("Who is Joren Hale married to?", [J, S]),
    ("Who is Joren Hale married to?", [J, ("Joren Hale", "city", "Selwick")]),
    ("What country is Sella Marne a citizen of?", [S]),
    ("What country is Sella Marne a citizen of?", [J, S]),
    ("What country is Sella Marne a citizen of?", [S, T]),
    ("What country is Sella Marne a citizen of?", [J, S, T]),
    ("where does brannick live?", [("brannick", "city", "Selwick")]),
    ("where does brannick live?", [("brannick", "boss", "Ottoline"),
                                   ("brannick", "city", "Selwick")]),
    ("Where does Brannick live?", [("brannick", "boss", "Ottoline"),
                                   ("brannick", "city", "Selwick")]),
    ("whats pells city?", [("Pell", "city", "Varnholt")]),
    ("what's pells city?", [("Pell", "city", "Varnholt")]),
    ("what is pells city?", [("Pell", "city", "Varnholt")]),
    ("whats Pell's city?", [("Pell", "city", "Varnholt")]),
    ("Where do I live?", [("USER", "city", "Harlow Cross")]),
    ("Where do I live?", [("USER", "name", "Anselm"),
                          ("USER", "city", "Harlow Cross")]),
    ("What is my city?", [("USER", "name", "Anselm"),
                          ("USER", "city", "Harlow Cross")]),
]
for t, tr in CASES:
    f = B92.compose_n_hop(t, tr)
    c = L113C.frame_consumes_question(t, list(f[1]), tr) if f else None
    f2 = B73.compose_question(t, tr)
    c2 = L113C.frame_consumes_question(t, list(f2[1]), tr) if f2 else None
    print(f"{t!r} n={len(tr)} | nhop={f} consumes={c} | b73={f2} "
          f"consumes={c2} explicit={L113.is_explicit_question(t)}")


# ---------------------------------------------------------------- sketch
# NOT installed anywhere: a mention-guided walk used only to check whether
# the proposed fix-A shape would give a frame, and whether the existing
# 113c consumption gate still accepts it.
def guided_walk(question, triples):
    q = " ".join(str(question).split())
    ents = [x for s, _, o in triples for x in (s, o)]
    ment = B92._entity_mentions92(q, ents)
    if len(ment) != 1:
        return None
    mentioned = B92._relation_mentions92(q)
    cur, rels, seen = ment[0], [], set()
    while True:
        outs = [(r, o) for (s, r, o) in triples if s == cur]
        cand = list(dict.fromkeys(r for r, _ in outs if r in mentioned
                                  and r not in rels))
        if len(cand) != 1:
            break
        r1 = cand[0]
        mid = [o for (r, o) in outs if r == r1][-1]
        if mid in seen:
            return None
        seen.add(mid); rels.append(r1); cur = mid
    if not rels or any(r not in rels for r in mentioned):
        return None
    return (ment[0], rels)


print("\n-- guided-walk sketch (fix A shape) --")
import fable_redteam143_cases as RT  # noqa: E402
RTW = {"QAW": RT.QAW, "PW": RT.PW}
extra = [
    ("Who is Joren Hale married to?", RT.QAW),
    ("What country is Sella Marne a citizen of?", RT.QAW),
    ("What country is Dara Fenn a citizen of?", RT.PW),
    ("What country is Dara Fenner a citizen of?", RT.PW),
    ("What is the official language of the country of citizenship of the spouse of Bram Kite?",
     ["Bram Kite is married to Cora Lind", "Cora Lind is a citizen of Norland"]),
    ("What is the capital of the country of citizenship of the person married to Bram Kite?",
     ["Bram Kite is married to Cora Lind", "Cora Lind is a citizen of Norland"]),
    ("Who employs the person married to Bram Kite?", ["Bram Kite is married to Cora Lind"]),
]
for t, sents in extra:
    tr = []
    for s in sents:
        got = B92.hear_teach92(s.replace("Actually, ", ""))
        if got:
            tr = [x for x in tr if not (x[0] == got[0] and x[1] == got[1])] + [got]
    g = guided_walk(t, tr)
    c = L113C.frame_consumes_question(t, list(g[1]), tr) if g else None
    print(f"{t!r} | nhop={B92.compose_n_hop(t, tr)} | guided={g} consumes={c}")
for t, tr in CASES:
    g = guided_walk(t, tr)
    c = L113C.frame_consumes_question(t, list(g[1]), tr) if g else None
    print(f"{t!r} n={len(tr)} | guided={g} consumes={c}")
