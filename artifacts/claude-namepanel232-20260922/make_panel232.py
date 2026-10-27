"""Generator for blind panel 232 (multi-word names in verb sentences).
Hand-written, deterministic. All names/towns/companies/languages are invented.
Run from repo root: python -B artifacts/claude-namepanel232-20260922/make_panel232.py
"""
import json, os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "panel.jsonl")
items = []


def add(family, pair, nw, setup, question, writes, nowrite, expect, gold, notes, clear=True):
    items.append({
        "id": "n232-%03d" % (len(items) + 1), "family": family, "pair": pair,
        "name_words": nw, "setup": setup, "question": question,
        "expect_writes": writes, "expect_nowrite": nowrite, "expect": expect,
        "gold": gold, "clear": clear, "notes": notes,
    })


QTPL = {"lives in": "Where does {n} live?", "works at": "Where does {n} work?",
        "speaks": "What language does {n} speak?"}

# (one-word name, multi-word name, value, optional distractor sentence template using {n})
LIVES = [
    ("Anselm", "Anselm Rook", "Tarnby", None),
    ("Delphine", "Delphine Oakhart", "New Vessby", None),
    ("Corvin", "Iris Mae Colter", "Lower Brambleford", None),
    ("Wendeline", "Tobin de Grey", "Hollowmere", "{n}'s sister is Pella."),
    ("Rusk", "Rusk Hallowell", "Quenby", None),
    ("Ottilie", "Mara Ellis-Vane", "Saltmarrow", None),
    ("Faddon", "Faddon Pike", "East Corrow", "{n}'s dog is Biscuit."),
    ("Jessamy", "Jessamy Thorne", "Wickerly", None),
    ("Bram", "Bram van Oster", "Fennick Cross", None),
]
WORKS = [
    ("Harlen", "Harlen Voss", "Brightwater Mills", None),
    ("Sorrel", "Sorrel Anne Kittering", "Quillford Bakery", None),
    ("Pimm", "Pimm Ashdown", "Tallowfinch Supply", None),
    ("Lisbet", "Lisbet du Marrow", "Corrigan Freight", "{n}'s boss is Ondry."),
    ("Evander", "Evander Stroud", "Greyfen Labs", None),
    ("Nella", "Nella Hart-Loweby", "Pinecrest Clinic", None),
    ("Quint", "Quint Mallory", "Oddbury Books", None),
    ("Tamsin", "Tamsin Rae Holloway", "Marsh Lantern Works", None),
    ("Gideo", "Gideo Farrant", "Vellum", "{n}'s brother is Harro."),
]
SPEAKS = [
    ("Yarrow", "Yarrow Penhale", "Thessic", None),
    ("Cressida", "Cressida Lune", "Old Morvani", None),
    ("Aldo", "Aldo ten Brink", "Kelari", None),
    ("Mirelle", "Mirelle Joy Castellan", "Ostrenic", "{n}'s teacher is Duvessa."),
    ("Orrin", "Orrin Blackwood", "Pellish", None),
    ("Briony", "Briony Ashe-Carrow", "Sarnic", None),
    ("Caddock", "Caddock Wren", "High Quellan", None),
    ("Linnea", "Linnea Vostrikova", "Duvani", None),
    ("Theon", "Theon Marsh", "Vostri", "{n}'s friend is Kester."),
]

pair_no = 0
for family, rel, rows in (("lives_in", "lives in", LIVES), ("works_at", "works at", WORKS),
                          ("speaks", "speaks", SPEAKS)):
    for one, multi, val, dist in rows:
        pair_no += 1
        pid = "P%02d" % pair_no
        for name in (one, multi):
            setup = ["%s %s %s." % (name, rel, val)]
            if dist:
                setup.append(dist.format(n=name))
            nw = len(name.split())
            note = "one-word control" if name == one else "multi-word name in the same slot"
            if "-" in name:
                note += "; hyphenated surname counts as one word"
            if " de " in name or " du " in name or " van " in name or " ten " in name:
                note += "; lower-case particle inside the name"
            if dist:
                note += "; possessive distractor sentence (its write is not listed)"
            if " " in val:
                note += "; multi-word value"
            if name != one and not name.startswith(one):
                note += "; multi-word name does not share the one-word control's first name"
            add(family, pid, nw, setup, QTPL[rel].format(n=name), [[name, rel, val]],
                False, "answer", val, note)

# mixed: (rel, multi A, multi B, one-word A, one-word B, value A, value B, ask 'A' or 'B', share)
MIXED = [
    ("lives in", "Anselm Rook", "Anselm Vey", "Anselm", "Garrick", "Tarnby", "Oxlade", "B", "first name"),
    ("lives in", "Iris Rook", "Tobin Rook", "Iris", "Tobin", "Pellow Green", "Saltmarrow", "A", "surname"),
    ("works at", "Harlen Voss", "Harlen Quay", "Harlen", "Moss", "Brightwater Mills", "Dunmore Glass", "A", "first name"),
    ("works at", "Sorrel Kittering", "Ada Kittering", "Sorrel", "Ada", "Quillford Bakery", "Greyfen Labs", "B", "surname"),
    ("speaks", "Yarrow Penhale", "Yarrow Stent", "Yarrow", "Fitch", "Thessic", "Kelari", "B", "first name"),
    ("speaks", "Mara Ellis-Vane", "Pol Ellis-Vane", "Mara", "Pol", "Sarnic", "Old Morvani", "A", "hyphenated surname"),
    ("lives in", "Tobin de Grey", "Tobin de Marle", "Tobin", "Wystan", "Hollowmere", "New Vessby", "A", "first name + particle"),
    ("works at", "Iris Mae Colter", "Iris Mae Dunning", "Iris", "Maeve", "Corrigan Freight", "Pinecrest Clinic", "B", "first + middle name"),
    ("speaks", "Orrin Blackwood", "Linnet Blackwood", "Orrin", "Linnet", "Pellish", "Duvani", "A", "surname"),
]
for rel, ma, mb, oa, ob, va, vb, ask, share in MIXED:
    pair_no += 1
    pid = "P%02d" % pair_no
    for a, b, kind in ((oa, ob, "one"), (ma, mb, "multi")):
        setup = ["%s %s %s." % (a, rel, va), "%s %s %s." % (b, rel, vb)]
        target, gold, other = (a, va, vb) if ask == "A" else (b, vb, va)
        nw = len(target.split())
        if kind == "one":
            note = "one-word twin: two different one-word names; answer must not be %s" % other
        else:
            note = "two people share a %s; answer must not be %s" % (share, other)
        add("mixed", pid, nw, setup, QTPL[rel].format(n=target),
            [[a, rel, va], [b, rel, vb]], False, "answer", gold, note)

# traps: (setup, question, name_words, note)
TRAPS = [
    (["I think Anselm Rook lives in Tarnby."], "Where does Anselm Rook live?", 2, "hedge 'I think'"),
    (["I think Iris Mae Colter works at Quillford Bakery."], None, 3, "hedge 'I think', 3-word name"),
    (["Maybe Tobin de Grey speaks Kelari."], "What language does Tobin de Grey speak?", 3, "hedge 'Maybe', particle name"),
    (["Tom says Delphine Oakhart lives in New Vessby."], "Where does Delphine Oakhart live?", 2, "hearsay 'Tom says' (Tom is a one-word speaker, not the subject)"),
    (["Garrick told me Mara Ellis-Vane works at Greyfen Labs."], None, 2, "hearsay 'X told me'"),
    (["Harlen Voss doesn't live in Oxlade."], "Where does Harlen Voss live?", 2, "negation 'doesn't'"),
    (["Sorrel Anne Kittering does not speak Thessic."], None, 3, "negation 'does not', 3-word name"),
    (["Bram van Oster doesn't work at Corrigan Freight."], "Where does Bram van Oster work?", 3, "negation, particle name"),
    (["Yarrow Penhale lives in Wickerly?"], "Where does Yarrow Penhale live?", 2, "question shaped like a statement (ends in '?')"),
    (["Nella Hart-Loweby works at Pinecrest Clinic?"], None, 2, "question shaped like a statement, hyphenated surname"),
    (["the old baker lives in Fennick Cross."], "Where does the old baker live?", 3, "lower-case common-noun subject; name_words counts 'the old baker'"),
    (["the new nurse speaks Pellish."], None, 3, "lower-case common-noun subject"),
]
for setup, q, nw, note in TRAPS:
    add("traps", None, nw, setup, q, [], True, "abstain" if q else None, None,
        note + ("; question must be abstained" if q else "; no question, write check only"))

assert len(items) == 84, len(items)
with open(OUT, "w") as f:
    for it in items:
        f.write(json.dumps(it, ensure_ascii=False) + "\n")
print("wrote", len(items), OUT)
