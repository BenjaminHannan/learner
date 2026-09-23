"""Generator for blind reader panel e235 (hand-written items, deterministic output).

Run from repo root:
  python3 -B artifacts/claude-earpanel235-20260922/make_panel.py
Writes artifacts/claude-earpanel235-20260922/panel.jsonl
Written blind: no code, relation tables, design docs or other panels were read.
"""
import json
import os

AL = {
    "boss": ["manager", "supervisor"],
    "city": ["lives in", "home city", "residence", "location", "home"],
    "sister": ["sibling"],
    "brother": ["sibling"],
    "workplace": ["employer", "works at", "works for", "company", "work"],
    "language": ["speaks", "language spoken"],
    "dog": ["dog name", "dog's name", "pet", "pet name"],
    "cat": ["cat name", "cat's name", "pet", "pet name"],
    "parrot": ["parrot name", "pet", "pet name"],
    "husband": ["spouse", "partner", "married to"],
    "wife": ["spouse", "partner", "married to"],
    "spouse": ["husband", "wife", "partner", "married to"],
    "mother": ["mom", "mum", "mum's name"],
    "father": ["dad"],
    "birthplace": ["born in", "place of birth", "hometown", "birth city"],
    "hometown": ["grew up in", "birthplace", "home town"],
    "school": ["college", "studies at", "goes to"],
    "job": ["occupation", "profession", "work"],
    "best friend": ["friend", "best mate"],
    "neighbor": ["neighbour"],
    "cousin": [],
    "daughter": ["child", "kid"],
    "son": ["child", "kid"],
}


def T(subject, relation, value):
    return {"act": "TEACH", "subject": subject, "relation": relation,
            "relation_aliases": AL[relation], "value": value}


def A(subject, relation, chain=None):
    return {"act": "ASK", "subject": subject, "relation": relation,
            "relation_aliases": AL[relation], "chain": chain}


def C(subject, r1, r2):
    # chain question: relation = the final relation asked about
    return A(subject, r2, [r1, r2])


# (turn, gold, clear, notes)
FAM = {}

FAM["plain_teach"] = [
    ("Kim's boss is Lee.", [T("Kim", "boss", "Lee")], True, ""),
    ("Marta lives in Brellin.", [T("Marta", "city", "Brellin")], True, ""),
    ("My sister is Ana.", [T("me", "sister", "Ana")], True, ""),
    ("Dovan works at Brightco.", [T("Dovan", "workplace", "Brightco")], True, ""),
    ("Pella speaks Norrish.", [T("Pella", "language", "Norrish")], True, "fictional language"),
    ("My brother is Tomas.", [T("me", "brother", "Tomas")], True, ""),
    ("Rin's husband is Karl.", [T("Rin", "husband", "Karl")], True, ""),
    ("Ossie's dog is called Biscuit.", [T("Ossie", "dog", "Biscuit")], True, ""),
    ("My boss is Greta.", [T("me", "boss", "Greta")], True, ""),
    ("Hal was born in Tarrow.", [T("Hal", "birthplace", "Tarrow")], True, ""),
    ("Juno's mother is Wenna.", [T("Juno", "mother", "Wenna")], True, ""),
    ("My cat is called Mitten.", [T("me", "cat", "Mitten")], True, ""),
    ("Brisa's wife is Lotte.", [T("Brisa", "wife", "Lotte")], True, ""),
    ("Fenn goes to Kellmoor College.", [T("Fenn", "school", "Kellmoor College")], True, ""),
    ("My best friend is Arlo.", [T("me", "best friend", "Arlo")], True, ""),
    ("Tavi is a plumber.", [T("Tavi", "job", "plumber")], True, "value is the job word; 'a plumber' also acceptable"),
    ("Sunny's brother is Pim.", [T("Sunny", "brother", "Pim")], True, ""),
    ("My neighbor is Mrs Oake.", [T("me", "neighbor", "Mrs Oake")], True, "title kept in value"),
    ("Ilse lives in Harrowby.", [T("Ilse", "city", "Harrowby")], True, ""),
    ("My dad is Bram.", [T("me", "father", "Bram")], True, ""),
    ("Coby works for Nettle & Finch.", [T("Coby", "workplace", "Nettle & Finch")], True, "company name with ampersand"),
    ("Zora's sister is Mae.", [T("Zora", "sister", "Mae")], True, ""),
    ("My son is Otto.", [T("me", "son", "Otto")], True, ""),
    ("Wes speaks Galvish.", [T("Wes", "language", "Galvish")], True, "fictional language"),
    ("Nell's cousin is Rafe.", [T("Nell", "cousin", "Rafe")], True, ""),
]

FAM["varied_teach"] = [
    ("Orla is Vic's boss.", [T("Vic", "boss", "Orla")], True, "reversed order: value first"),
    ("tamsin moved to brellin last year", [T("tamsin", "city", "brellin")], True, "lower-case; 'moved to' = now lives in"),
    ("Oh and Pia's got a brother called Jory.", [T("Pia", "brother", "Jory")], True, ""),
    ("My dog's name is Pip.", [T("me", "dog", "Pip")], True, ""),
    ("Dex works for Brightco now.", [T("Dex", "workplace", "Brightco")], True, ""),
    ("fyi my wife's name is Hester", [T("me", "wife", "Hester")], True, ""),
    ("Gil lives over in Quarrow these days.", [T("Gil", "city", "Quarrow")], True, ""),
    ("my mum's called Rosalind", [T("me", "mother", "Rosalind")], True, ""),
    ("Anya teaches at Fernhill School.", [T("Anya", "workplace", "Fernhill School")], True, "workplace; 'job: teacher' is implied but not the stated value"),
    ("Bex has a cat named Toffee.", [T("Bex", "cat", "Toffee")], True, ""),
    ("Corin's married to Elspeth.", [T("Corin", "spouse", "Elspeth")], True, "gender not stated, so spouse; husband/wife accepted as aliases"),
    ("yeah so Lorne's boss is a guy called Pritch", [T("Lorne", "boss", "Pritch")], True, ""),
    ("Mina grew up in Oldwick.", [T("Mina", "hometown", "Oldwick")], False, "saving is clear, but relation could be hometown or birthplace; must NOT be stored as current city"),
    ("i work at Pellam's Bakery", [T("me", "workplace", "Pellam's Bakery")], True, "possessive inside company name"),
    ("Sable speaks Ostrish fluently.", [T("Sable", "language", "Ostrish")], True, ""),
    ("Kip is Nora's little sister.", [T("Nora", "sister", "Kip")], True, "reversed order; 'little' is not part of the relation"),
    ("Bram's daughter is called Evie.", [T("Bram", "daughter", "Evie")], True, ""),
    ("Tully's been living in Marsh End since June.", [T("Tully", "city", "Marsh End")], True, "'Tully's' = Tully has, not possessive"),
    ("my best mate is Dunstan", [T("me", "best friend", "Dunstan")], True, ""),
    ("Quin's got a job at Hollis Motors.", [T("Quin", "workplace", "Hollis Motors")], True, ""),
    ("Ferris calls his parrot Mango.", [T("Ferris", "parrot", "Mango")], True, ""),
    ("Livvy's hubby is Dean.", [T("Livvy", "husband", "Dean")], True, "slang 'hubby'"),
    ("Ned lives in Pebbleford, by the way.", [T("Ned", "city", "Pebbleford")], True, ""),
    ("Yara works as a nurse.", [T("Yara", "job", "nurse")], True, ""),
    ("Suki's boss is Morrow and Morrow lives in Vessby.",
     [T("Suki", "boss", "Morrow"), T("Morrow", "city", "Vessby")], True, "two facts"),
    ("My sister is Ana and she lives in Tarrow.",
     [T("me", "sister", "Ana"), T("Ana", "city", "Tarrow")], True, "two facts; 'she' resolves to Ana"),
    ("Jem works at Brightco and his wife is Tilly.",
     [T("Jem", "workplace", "Brightco"), T("Jem", "wife", "Tilly")], True, "two facts; 'his' resolves to Jem"),
    ("my brother's called Hob and he lives in Crane Hill",
     [T("me", "brother", "Hob"), T("Hob", "city", "Crane Hill")], True, "two facts; 'he' resolves to Hob"),
    ("Ada's cat is Pudding, and her dog is Crumpet.",
     [T("Ada", "cat", "Pudding"), T("Ada", "dog", "Crumpet")], True, "two facts; 'her' resolves to Ada"),
    ("Rook was born in Dunmere but lives in Saltby now.",
     [T("Rook", "birthplace", "Dunmere"), T("Rook", "city", "Saltby")], True, "two facts; birthplace vs current city must stay separate"),
]

FAM["full_names"] = [
    ("Delia Marrow's boss is Otis Fenwick.", [T("Delia Marrow", "boss", "Otis Fenwick")], True, ""),
    ("Harriet Quell lives in Brellin.", [T("Harriet Quell", "city", "Brellin")], True, ""),
    ("My sister is Anna Bell Voss.", [T("me", "sister", "Anna Bell Voss")], True, "three-word value"),
    ("Tobias Wren works at Castlemoor Freight.", [T("Tobias Wren", "workplace", "Castlemoor Freight")], True, ""),
    ("Lucy Ann Farrow speaks Norrish.", [T("Lucy Ann Farrow", "language", "Norrish")], True, "three-word subject"),
    ("Ezra Kade's wife is Moira Kade.", [T("Ezra Kade", "wife", "Moira Kade")], True, "shared surname"),
    ("my boss is Pauline Dray", [T("me", "boss", "Pauline Dray")], True, ""),
    ("Gideon Pratt moved to Lower Esk.", [T("Gideon Pratt", "city", "Lower Esk")], True, "two-word town"),
    ("Rosa Delacourt's dog is called Sir Wiggles.", [T("Rosa Delacourt", "dog", "Sir Wiggles")], True, "two-word pet name"),
    ("Marcus Oyelaran is Nina Holt's brother.", [T("Nina Holt", "brother", "Marcus Oyelaran")], True, "reversed order"),
    ("My neighbour is Walter James Pym.", [T("me", "neighbor", "Walter James Pym")], True, "British spelling; three-word value"),
    ("Imogen Tate was born in Kestle Bay.", [T("Imogen Tate", "birthplace", "Kestle Bay")], True, ""),
    ("Felix Moor's husband is Arun Bassey.", [T("Felix Moor", "husband", "Arun Bassey")], True, ""),
    ("Clara Beth Hensley works for Brightwater Dental.", [T("Clara Beth Hensley", "workplace", "Brightwater Dental")], True, ""),
    ("My best friend is Joanna Reyes and she lives in Harlow Cross.",
     [T("me", "best friend", "Joanna Reyes"), T("Joanna Reyes", "city", "Harlow Cross")], True,
     "two facts; 'she' resolves to Joanna Reyes"),
]

FAM["questions"] = [
    ("Where does Marta live?", [A("Marta", "city")], True, ""),
    ("Who's Orla's boss?", [A("Orla", "boss")], True, ""),
    ("what's my sister's name", [A("me", "sister")], True, "no question mark"),
    ("Do you know where Dovan works?", [A("Dovan", "workplace")], True, "polite wrapper"),
    ("what language does Pella speak", [A("Pella", "language")], True, "no question mark"),
    ("Who is Rin married to?", [A("Rin", "spouse")], True, ""),
    ("where was Hal born", [A("Hal", "birthplace")], True, ""),
    ("What's my dog called?", [A("me", "dog")], True, ""),
    ("who's my boss", [A("me", "boss")], True, ""),
    ("Where does Tavi work?", [A("Tavi", "workplace")], True, ""),
    ("Who's Juno's mum?", [A("Juno", "mother")], True, ""),
    ("whats the name of Bex's cat", [A("Bex", "cat")], True, "missing apostrophe in 'whats'"),
    ("Can you tell me where Gil lives?", [A("Gil", "city")], True, ""),
    ("who is Nora's sister", [A("Nora", "sister")], True, ""),
    ("Does Ilse have a brother?", [A("Ilse", "brother")], False, "yes/no shape; a reader could treat it as an existence check rather than a lookup of the brother's name"),
    ("What does Yara do for a living?", [A("Yara", "job")], True, ""),
    ("Who's my dad?", [A("me", "father")], True, ""),
    ("which city does Fenn live in", [A("Fenn", "city")], True, ""),
    ("What school does Fenn go to?", [A("Fenn", "school")], True, ""),
    ("Tell me who Zora's sister is.", [A("Zora", "sister")], True, "command-shaped question ending in a full stop"),
    ("who's Harriet Quell's boss?", [A("Harriet Quell", "boss")], True, "full name"),
    ("Where does Tobias Wren work", [A("Tobias Wren", "workplace")], True, "full name, no question mark"),
    ("Remember who my best friend is?", [A("me", "best friend")], True, ""),
    ("Kip's brother - who is that again?", [A("Kip", "brother")], True, "topic first, question after a dash"),
    ("What's Livvy's husband's name?", [A("Livvy", "husband")], True, "single hop: 'husband's name' is the husband"),
]

FAM["chain_questions"] = [
    ("Where does Suki's boss live?", [C("Suki", "boss", "city")], True, ""),
    ("Where does my boss live?", [C("me", "boss", "city")], True, ""),
    ("What language does Rin's husband speak?", [C("Rin", "husband", "language")], True, ""),
    ("who is my sister's husband", [C("me", "sister", "husband")], True, "no question mark"),
    ("Where does Jem's wife work?", [C("Jem", "wife", "workplace")], True, ""),
    ("whats the name of my brother's dog", [C("me", "brother", "dog")], True, ""),
    ("Who's Delia Marrow's boss's boss?", [C("Delia Marrow", "boss", "boss")], True, "same relation twice; full name"),
    ("Where was Pia's brother born?", [C("Pia", "brother", "birthplace")], True, ""),
    ("Do you know where my mum lives?", [C("me", "mother", "city")], True, "polite wrapper"),
    ("Which company does Nell's cousin work for", [C("Nell", "cousin", "workplace")], True, "no question mark"),
    ("who is Lorne's boss married to", [C("Lorne", "boss", "spouse")], True, ""),
    ("What does my best friend do for work?", [C("me", "best friend", "job")], False, "'for work' could mean job title or workplace; job is gold, workplace defensible"),
    ("Where does Bram's daughter live?", [C("Bram", "daughter", "city")], True, ""),
    ("What's the name of Ada's neighbour's cat?", [C("Ada", "neighbor", "cat")], True, ""),
    ("Where does Vic's manager live", [C("Vic", "boss", "city")], True, "'manager' is an alias of boss"),
]

FAM["no_save"] = [
    ("I think Marta lives in Brellin.", [], True, "hedge"),
    ("maybe Dovan works at Brightco, not sure", [], True, "hedge"),
    ("Wren says Hal's boss is Petra.", [], True, "hearsay (per brief: do not save)"),
    ("apparently Gil moved to Quarrow", [], False, "hearsay/soft hedge; some people would save it as fact"),
    ("Tavi doesn't live in Vessby.", [], True, "negation"),
    ("Juno isn't Rafe's sister.", [], True, "negation"),
    ("If Anya moved to Harrowby she'd be happy.", [], True, "hypothetical"),
    ("What if my boss was Greta?", [], True, "hypothetical question, not a lookup"),
    ("hi how are you", [], True, "small talk"),
    ("thanks, that's really helpful!", [], True, "small talk"),
    ("Remind me to call Coby tomorrow.", [], True, "request"),
    ("can you set a timer for ten minutes", [], True, "request"),
    ("Orla is the best boss ever.", [], True, "opinion; does not say whose boss"),
    ("Brellin is such a lovely town.", [], True, "opinion"),
    ("Marta lives in Brellin?", [], False, "statement-shaped question: must not save; could reasonably be read as ASK (Marta, city)"),
    ("so Pella speaks Norrish?", [], False, "statement-shaped question: must not save; could reasonably be read as ASK (Pella, language)"),
    ("I might move to Tarrow next year.", [], True, "future possibility"),
    ("Sunny used to live in Oldwick.", [], False, "past residence, not current city; a 'former city' relation would be defensible"),
    ("Ossie wants to work at Brightco someday.", [], True, "wish"),
    ("i'm not sure if Brisa's wife is Lotte or Lena", [], True, "uncertain between two values"),
    ("Let's say Fenn's boss is Marlow.", [], True, "pretend / hypothetical setup"),
    ("ok cool", [], True, "small talk"),
    ("lol my dog is so silly", [], True, "opinion, no name given"),
    ("Did you know Hollis Motors is closing?", [], False, "news-style question; not a supported relation, though a reader might try to store something"),
    ("Wes probably speaks Galvish.", [], True, "hedge"),
]

FAM["corrections"] = [
    ("Actually, Marta lives in Vessby now.", [T("Marta", "city", "Vessby")], True, "correction"),
    ("No wait, Vic's boss is Ray.", [T("Vic", "boss", "Ray")], True, "correction"),
    ("sorry I meant my sister is Anya, not Ana", [T("me", "sister", "Anya")], True, "correction; the negated old value must not be saved"),
    ("oops, Dovan works at Brightline, not Brightco", [T("Dovan", "workplace", "Brightline")], True, "correction; the negated old value must not be saved"),
    ("correction: Pella speaks Ostrish", [T("Pella", "language", "Ostrish")], True, "correction"),
    ("Actually my dog's name is Pippin", [T("me", "dog", "Pippin")], True, "correction"),
    ("no, Rin's husband is Konrad", [T("Rin", "husband", "Konrad")], True, "correction"),
    ("I got that wrong earlier - Hal was born in Tarrowby.", [T("Hal", "birthplace", "Tarrowby")], True, "correction"),
    ("Scratch that, my boss is Nadia now.", [T("me", "boss", "Nadia")], True, "correction"),
    ("wait no Ilse lives in Harrowgate", [T("Ilse", "city", "Harrowgate")], True, "correction; no punctuation"),
    ("Not Tomas - my brother is Tobin.", [T("me", "brother", "Tobin")], True, "correction; negated old value first"),
    ("Actually Juno's mum is Wendeline, I mixed them up", [T("Juno", "mother", "Wendeline")], True, "correction"),
    ("Update: Coby works at Fairleigh Mills now.", [T("Coby", "workplace", "Fairleigh Mills")], True, "correction"),
    ("Hmm no, Nora's sister is Kit, not Kip.", [T("Nora", "sister", "Kit")], True, "correction; near-identical old and new names"),
    ("Let me fix that: Bex's cat is called Treacle.", [T("Bex", "cat", "Treacle")], True, "correction"),
]

COUNTS = {"plain_teach": 25, "varied_teach": 30, "full_names": 15, "questions": 25,
          "chain_questions": 15, "no_save": 25, "corrections": 15}


def main():
    rows, n = [], 0
    for fam, want in COUNTS.items():
        items = FAM[fam]
        assert len(items) == want, (fam, len(items))
        for turn, gold, clear, notes in items:
            for f in gold:
                assert f["subject"] == "me" or f["subject"] in turn, (turn, f)
                if f["act"] == "TEACH":
                    assert f["value"] in turn, (turn, f)
            n += 1
            rows.append({"id": f"e235-{n:03d}", "family": fam, "turn": turn,
                         "gold": gold, "clear": clear, "notes": notes})
    turns = [r["turn"] for r in rows]
    assert len(set(turns)) == len(turns), "duplicate turn"
    assert sum(1 for t, g, *_ in FAM["varied_teach"] if len(g) == 2) == 6
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "panel.jsonl")
    with open(out, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("wrote", len(rows), "items")


if __name__ == "__main__":
    main()
