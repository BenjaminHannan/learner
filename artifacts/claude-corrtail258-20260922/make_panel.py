"""Correction-tail panel 258: items held by hand; writes panel.jsonl deterministically and runs self-checks.

Run from the repo root:  python -B artifacts/claude-corrtail258-20260922/make_panel.py
All names are fictional. Schema fixed by the director's spec (2026-09-22).
"""
import json, re, sys
from pathlib import Path

OUT = Path(__file__).resolve().parent / "panel.jsonl"
FAMILIES = [("that_denial", 12), ("that_correction", 12), ("pure_denial_that", 10),
            ("other_tail_denial", 10), ("keep", 8), ("question_tail", 6),
            ("unstored_tail", 6), ("control", 16)]
CAUSE = ["that_denial", "that_correction", "pure_denial_that", "other_tail_denial"]
FIELDS = ["id", "family", "setup", "turn", "followup", "stated_facts", "target",
          "expect_gone", "expect_store", "gold_followup", "note"]
U = "USER"
ITEMS = []


def T(s, r, v):
    return [s, r, v]


def add(fam, setup, turn, followup, stated, target, gone, store, gold, note):
    ITEMS.append(dict(family=fam, setup=setup, turn=turn, followup=followup,
                      stated_facts=stated, target=target, expect_gone=gone,
                      expect_store=store, gold_followup=gold, note=note))


def den(fam, setup, turn, fu, stated, target, note):
    add(fam, setup, turn, fu, stated, target, [target],
        [x for x in stated if x != target], None, note)


def cor(fam, setup, turn, fu, stated, target, newv, note):
    new = [target[0], target[1], newv]
    add(fam, setup, turn, fu, stated, target, [target],
        [new] + [x for x in stated if x != target], newv, note)


# ---------------- that_denial (12) ----------------
F = "that_denial"
st = [T("Brannic Holt", "boss", "Elsbeth Marr"), T("Brannic Holt", "city", "Quillford")]
den(F, ["Brannic Holt's boss is Elsbeth Marr.", "Brannic Holt's city is Quillford."],
    "Brannic Holt's boss isn't Elsbeth Marr, that's ancient history.", "Who is Brannic Holt's boss?",
    st, st[0], "isn't + comma that's-clause; tags: that")
st = [T("Sefa Dunmore", "language", "Orlish")]
den(F, ["Sefa Dunmore's language is Orlish."],
    "Sefa Dunmore's language is not Orlish - that was years ago.", "What is Sefa Dunmore's language?",
    st, st[0], "is not + dash that-was clause; tags: that")
st = [T("Tobiah Rusk", "employer", "Glimmerside Foundry"), T("Tobiah Rusk", "job", "welder")]
den(F, ["Tobiah Rusk's employer is Glimmerside Foundry.", "Tobiah Rusk's job is welder."],
    "Tobiah Rusk's employer isn't Glimmerside Foundry; that is no longer true.", "What is Tobiah Rusk's employer?",
    st, st[0], "isn't + semicolon that-is clause; tags: that")
st = [T("Mirelle Asquith", "dog", "Tansy")]
den(F, ["Mirelle Asquith's dog is Tansy."],
    "mirelle asquith's dog isn't tansy, thats long gone.", "What is Mirelle Asquith's dog?",
    st, st[0], "lowercase, thats without apostrophe; tags: lower typo that")
st = [T("Corwin Blay", "sister", "Adda Blay")]
den(F, ["Corwin Blay's sister is Adda Blay."],
    "corwin blay's sister is not adda blay (that was a mix-up).", "Who is Corwin Blay's sister?",
    st, st[0], "lowercase, bracketed that-was clause; tags: lower that")
st = [T(U, "workplace", "Fennick Yard")]
den(F, ["My workplace is Fennick Yard."],
    "my workplace isn't fennick yard, that's from my old life.", "What is my workplace?",
    st, st[0], "lowercase first person, that's-clause; tags: lower first that")
st = [T(U, "boss", "Hollis Vane"), T(U, "city", "Pendrow")]
den(F, ["My boss is Hollis Vane.", "My city is Pendrow."],
    "My boss isn't Hollis Vane, which was only true last spring.", "Who is my boss?",
    st, st[0], "first person, which-was clause; tags: first that")
st = [T("Ysolde Farrow", "hometown", "Kestrel Hythe")]
den(F, ["Ysolde Farrow's hometown is Kestrel Hythe."],
    "Ysolde Farrow's hometown isn't Kestrel Hythe, that's not right at all.", "What is Ysolde Farrow's hometown?",
    st, st[0], "that's-not clause; tags: that")
st = [T("Dace Morrin", "cat", "Pumice")]
den(F, ["Dace Morrin's cat is Pumice."],
    "Dace Morrin's cat isn't Pumice, this is an old record.", "What is Dace Morrin's cat?",
    st, st[0], "this-is clause; tags: that")
st = [T("Linnea Stroud", "workplace", "Ashcombe Depot")]
den(F, ["Linnea Stroud's workplace is Ashcombe Depot."],
    "Linnea Stroud's workplace isn't Ashcombe Depot, that's old news.", "What is Linnea Stroud's workplace?",
    st, st[0], "spec example clause shape; tags: that")
st = [T("Garrick Ome", "job", "tanner")]
den(F, ["Garrick Ome's job is tanner."],
    "Garrick Ome's job isn't tanner (that was last year).", "What is Garrick Ome's job?",
    st, st[0], "spec example clause shape, bracketed; tags: that")
st = [T("Pell Harrowby", "brother", "Aldo Harrowby")]
den(F, ["Pell Harrowby's brother is Aldo Harrowby."],
    "pell harrowby's brother isnt aldo harrowby, which is outdated info.", "Who is Pell Harrowby's brother?",
    st, st[0], "lowercase, isnt without apostrophe, which-is clause; tags: lower typo that")

# ---------------- that_correction (12) ----------------
F = "that_correction"
st = [T("Rowan Tessik", "city", "Varnholm"), T("Rowan Tessik", "job", "cooper")]
cor(F, ["Rowan Tessik's city is Varnholm.", "Rowan Tessik's job is cooper.", "What is Rowan Tessik's city?"],
    "No, it's Brackmoor, that's outdated.", "What is Rowan Tessik's city?",
    st, st[0], "Brackmoor", "contextual correction, spec example clause shape; tags: ctx that")
st = [T("Imrie Kell", "boss", "Sabine Frome")]
cor(F, ["Imrie Kell's boss is Sabine Frome.", "Who is Imrie Kell's boss?"],
    "Nope, it's Dorian Quist now - that one's stale.", "Who is Imrie Kell's boss?",
    st, st[0], "Dorian Quist", "contextual correction, dash that-one's clause; tags: ctx that")
st = [T("Oona Lisk", "language", "Pelric")]
cor(F, ["Oona Lisk's language is Pelric.", "What is Oona Lisk's language?"],
    "no its merrow, that was before she moved.", "What is Oona Lisk's language?",
    st, st[0], "Merrow", "lowercase contextual, its without apostrophe, that-was clause; tags: ctx lower typo that")
st = [T(U, "employer", "Stellan Works")]
cor(F, ["My employer is Stellan Works.", "What is my employer?"],
    "Actually it's Brisk Cartage, that's an old job of mine.", "What is my employer?",
    st, st[0], "Brisk Cartage", "first-person contextual, that's-clause; tags: ctx first that")
st = [T(U, "dog", "Juniper")]
cor(F, ["My dog is Juniper.", "What is my dog?"],
    "no, it's rook, that was a typo.", "What is my dog?",
    st, st[0], "Rook", "lowercase first-person contextual, that-was clause; tags: ctx lower first that")
st = [T("Halden Crewe", "workplace", "Mossgate Library"), T("Halden Crewe", "city", "Tarrow")]
cor(F, ["Halden Crewe's workplace is Mossgate Library.", "Halden Crewe's city is Tarrow.", "What is Halden Crewe's workplace?"],
    "It's Ember Lane School actually; that was his previous post.", "What is Halden Crewe's workplace?",
    st, st[0], "Ember Lane School", "contextual, semicolon that-was clause; tags: ctx that")
st = [T("Veda Prynne", "boss", "Colm Asher")]
cor(F, ["Veda Prynne's boss is Colm Asher."],
    "Veda Prynne's boss is Ilse Marrow now, not Colm Asher - that's old.", "Who is Veda Prynne's boss?",
    st, st[0], "Ilse Marrow", "explicit now/not correction, spec example clause; tags: that")
st = [T("Tamsin Rook", "city", "Galloway Reach")]
cor(F, ["Tamsin Rook's city is Galloway Reach."],
    "Tamsin Rook's city is Hollowmere, not Galloway Reach, that's been wrong for ages.", "What is Tamsin Rook's city?",
    st, st[0], "Hollowmere", "explicit correction, that's-been clause; tags: that")
st = [T("Birch Allard", "job", "miller")]
cor(F, ["Birch Allard's job is miller."],
    "birch allard's job is glazier now, not miller; thats years out of date.", "What is Birch Allard's job?",
    st, st[0], "glazier", "lowercase explicit, thats without apostrophe; tags: lower typo that")
st = [T(U, "language", "Durvish"), T(U, "city", "Anselm")]
cor(F, ["My language is Durvish.", "My city is Anselm."],
    "My language is Solvic now, not Durvish, which was my first one.", "What is my language?",
    st, st[0], "Solvic", "first-person explicit, which-was clause; tags: first that")
st = [T("Kester Vail", "cat", "Nutmeg")]
cor(F, ["Kester Vail's cat is Nutmeg."],
    "Kester Vail's cat is Sorrel, not Nutmeg (that was the neighbour's).", "What is Kester Vail's cat?",
    st, st[0], "Sorrel", "explicit, bracketed that-was clause; tags: that")
st = [T("Ingrid Solway", "employer", "Coldwater Press")]
cor(F, ["Ingrid Solway's employer is Coldwater Press."],
    "Ingrid Solway's employer is Harbin Freight, not Coldwater Press; this is a fix for old info.", "What is Ingrid Solway's employer?",
    st, st[0], "Harbin Freight", "explicit, semicolon this-is clause; tags: that")

# ---------------- pure_denial_that (10) ----------------
F = "pure_denial_that"
st = [T("Nell Brisco", "boss", "Arlo Tenby")]
den(F, ["Nell Brisco's boss is Arlo Tenby.", "Who is Nell Brisco's boss?"],
    "That's not right, that's from ages ago.", "Who is Nell Brisco's boss?",
    st, st[0], "contextual pure denial, that's-clause; tags: ctx that")
st = [T("Fenwick Oley", "city", "Drumlow")]
den(F, ["Fenwick Oley's city is Drumlow.", "What is Fenwick Oley's city?"],
    "nope, thats stale", "What is Fenwick Oley's city?",
    st, st[0], "lowercase contextual, thats without apostrophe; tags: ctx lower typo that")
st = [T("Arden Soyle", "job", "chandler")]
den(F, ["Arden Soyle's job is chandler.", "What is Arden Soyle's job?"],
    "No, that was his old trade.", "What is Arden Soyle's job?",
    st, st[0], "contextual No + that-was clause; tags: ctx that")
st = [T("Mabry Quint", "language", "Hessic")]
den(F, ["Mabry Quint's language is Hessic.", "What is Mabry Quint's language?"],
    "wrong, that is out of date", "What is Mabry Quint's language?",
    st, st[0], "lowercase contextual, that-is clause; tags: ctx lower that")
st = [T(U, "sister", "Cleo Varda")]
den(F, ["My sister is Cleo Varda.", "Who is my sister?"],
    "That's incorrect, that was my old roommate.", "Who is my sister?",
    st, st[0], "first-person contextual, that-was clause; tags: ctx first that")
st = [T(U, "hometown", "Pellbrook")]
den(F, ["My hometown is Pellbrook.", "What is my hometown?"],
    "no thats wrong, that was where i worked", "What is my hometown?",
    st, st[0], "lowercase first-person contextual, thats without apostrophe; tags: ctx lower first typo that")
st = [T("Oswin Tarr", "dog", "Bramble")]
den(F, ["Oswin Tarr's dog is Bramble.", "What is Oswin Tarr's dog?"],
    "Not true, which was the case before.", "What is Oswin Tarr's dog?",
    st, st[0], "contextual, which-was clause; tags: ctx that")
st = [T("Liesl Harker", "workplace", "Crowmarsh Clinic"), T("Liesl Harker", "boss", "Edda Fane")]
den(F, ["Liesl Harker's workplace is Crowmarsh Clinic.", "Liesl Harker's boss is Edda Fane.", "What is Liesl Harker's workplace?"],
    "No - that's out of date.", "What is Liesl Harker's workplace?",
    st, st[0], "contextual, dash that's-clause, one other fact untouched; tags: ctx that")
st = [T("Quenby Ashe", "employer", "Tollgate Mills")]
den(F, ["Quenby Ashe's employer is Tollgate Mills.", "What is Quenby Ashe's employer?"],
    "Incorrect; this is an old record.", "What is Quenby Ashe's employer?",
    st, st[0], "contextual, semicolon this-is clause; tags: ctx that")
st = [T("Radley Voss", "brother", "Emrys Voss")]
den(F, ["Radley Voss's brother is Emrys Voss.", "Who is Radley Voss's brother?"],
    "That isn't right, that's history.", "Who is Radley Voss's brother?",
    st, st[0], "contextual, that's-clause; tags: ctx that")

# ---------------- other_tail_denial (10) ----------------
F = "other_tail_denial"
st = [T("Siward Colt", "employer", "Amberly Dairy")]
den(F, ["Siward Colt's employer is Amberly Dairy."],
    "Siward Colt's employer isn't Amberly Dairy, it's wrong now.", "What is Siward Colt's employer?",
    st, st[0], "spec example tail; tags: other")
st = [T("Wynne Palliser", "boss", "Gideon Hart")]
den(F, ["Wynne Palliser's boss is Gideon Hart."],
    "Wynne Palliser's boss isn't Gideon Hart, he retired.", "Who is Wynne Palliser's boss?",
    st, st[0], "comma he-clause; tags: other")
st = [T("Elspeth Grue", "city", "Noxbury")]
den(F, ["Elspeth Grue's city is Noxbury."],
    "Elspeth Grue's city is not Noxbury - she moved away.", "What is Elspeth Grue's city?",
    st, st[0], "dash she-clause; tags: other")
st = [T("Thane Iveson", "job", "farrier")]
den(F, ["Thane Iveson's job is farrier."],
    "thane iveson's job isnt farrier, he switched careers", "What is Thane Iveson's job?",
    st, st[0], "lowercase, isnt without apostrophe; tags: lower typo other")
st = [T("Brisa Candell", "cat", "Mothwing")]
den(F, ["Brisa Candell's cat is Mothwing."],
    "brisa candell's cat isn't mothwing, sadly", "What is Brisa Candell's cat?",
    st, st[0], "lowercase, spec example tail; tags: lower other")
st = [T(U, "workplace", "Tallis Hall")]
den(F, ["My workplace is Tallis Hall."],
    "My workplace isn't Tallis Hall, I left in June.", "What is my workplace?",
    st, st[0], "first person, I-clause; tags: first other")
st = [T(U, "language", "Corvic")]
den(F, ["My language is Corvic."],
    "my language isn't corvic, i mixed them up", "What is my language?",
    st, st[0], "lowercase first person, i-clause; tags: lower first other")
st = [T("Hesper Lowe", "sister", "Maud Lowe")]
den(F, ["Hesper Lowe's sister is Maud Lowe."],
    "Hesper Lowe's sister isn't Maud Lowe, they're cousins.", "Who is Hesper Lowe's sister?",
    st, st[0], "they're-clause; tags: other")
st = [T("Ambrose Keel", "dog", "Clover")]
den(F, ["Ambrose Keel's dog is Clover."],
    "Ambrose Keel's dog isn't Clover lol", "What is Ambrose Keel's dog?",
    st, st[0], "spec example tail; tags: other")
st = [T("Petra Yarrow", "hometown", "Wexmoor")]
den(F, ["Petra Yarrow's hometown is Wexmoor."],
    "Petra Yarrow's hometown is not Wexmoor, my mistake earlier.", "What is Petra Yarrow's hometown?",
    st, st[0], "my-mistake tail; tags: other")

# ---------------- keep (8) ----------------  expect_store / gold copied from the base run
F = "keep"
st = [T("Corin Ashdown", "boss", "Maren Toll")]
add(F, ["Corin Ashdown's boss is Maren Toll."],
    "Corin Ashdown's employer is Flintrow Brewery, which is a small brewery.", "What is Corin Ashdown's employer?",
    st, None, [], [T("Corin Ashdown", "boss", "Maren Toll")], None, "teach with which-is appositive; tags: that")
st = [T("Delphine Ravel", "city", "Sorrowby")]
add(F, ["Delphine Ravel's city is Sorrowby."],
    "Remind me of Delphine Ravel's city, that's all I need.", "What is Delphine Ravel's city?",
    st, None, [], [T("Delphine Ravel", "city", "Sorrowby")], "Sorrowby", "request with that's-clause; tags: that")
st = [T(U, "city", "Glenmoor")]
add(F, ["My city is Glenmoor."],
    "My sister is Ottilie Brand, this is my older sister.", "Who is my sister?",
    st, None, [], [T(U, "city", "Glenmoor")], None, "first-person teach with this-is clause; tags: first that")
st = [T("Ludo Fairweather", "cat", "Sprocket")]
add(F, ["Ludo Fairweather's cat is Sprocket."],
    "Ludo Fairweather's dog is Pepper, which is a beagle.", "What is Ludo Fairweather's dog?",
    st, None, [], [T("Ludo Fairweather", "cat", "Sprocket")], None, "teach with which-is appositive; tags: that")
st = [T("Jory Penhale", "job", "thatcher")]
add(F, ["Jory Penhale's job is thatcher."],
    "Thanks, that's really helpful.", "What is Jory Penhale's job?",
    st, None, [], [T("Jory Penhale", "job", "thatcher")], "thatcher", "chat with that's-clause; tags: that")
st = [T("Hale Winterbourne", "job", "fishmonger")]
add(F, ["Hale Winterbourne's job is fishmonger."],
    "Hale Winterbourne's workplace is Cinder Row Market, that's near the docks.", "What is Hale Winterbourne's workplace?",
    st, None, [], [T("Hale Winterbourne", "job", "fishmonger")], None, "teach with that's appositive; tags: that")
st = [T("Vesna Callow", "boss", "Rhodri Penn")]
add(F, ["Vesna Callow's boss is Rhodri Penn."],
    "Who is Vesna Callow's boss, which is the thing I forgot?", "Who is Vesna Callow's boss?",
    st, None, [], [T("Vesna Callow", "boss", "Rhodri Penn")], "Rhodri Penn", "question with which-is clause; tags: that")
st = [T("Nyssa Orme", "job", "weaver")]
add(F, ["Nyssa Orme's job is weaver."],
    "ok, that's cool, thanks", "What is Nyssa Orme's job?",
    st, None, [], [T("Nyssa Orme", "job", "weaver")], "weaver", "lowercase chat with that's-clause; tags: lower that")

# ---------------- question_tail (6) ----------------
F = "question_tail"
def qt(setup, turn, fu, stated, gold, note):
    add(F, setup, turn, fu, stated, None, [], list(stated), gold, note)
qt(["Aurel Dane's city is Fairholt."], "Is Aurel Dane's city still Fairholt, or is that old?",
   "What is Aurel Dane's city?", [T("Aurel Dane", "city", "Fairholt")], "Fairholt", "yes/no question with or-is-that tail; tags: that")
qt(["Beatrix Moll's boss is Fenn Oakes."], "Is Fenn Oakes still Beatrix Moll's boss, or has that changed?",
   "Who is Beatrix Moll's boss?", [T("Beatrix Moll", "boss", "Fenn Oakes")], "Fenn Oakes", "has-that-changed tail; tags: that")
qt(["Caspian Rue's job is cartwright."], "What is Caspian Rue's job, is that still cartwright?",
   "What is Caspian Rue's job?", [T("Caspian Rue", "job", "cartwright")], "cartwright", "wh-question plus is-that tail; tags: that")
qt(["My employer is Larkspur Mills."], "Is my employer still Larkspur Mills, or is that stale?",
   "What is my employer?", [T(U, "employer", "Larkspur Mills")], "Larkspur Mills", "first-person question tail; tags: first that")
qt(["Dorrit Venn's language is Asmic."], "doesnt dorrit venn speak asmic, or is that outdated?",
   "What is Dorrit Venn's language?", [T("Dorrit Venn", "language", "Asmic")], "Asmic", "lowercase, doesnt without apostrophe, spec example tail; tags: lower typo that")
qt(["Edlyn Carrow's dog is Wisp."], "Edlyn Carrow's dog is Wisp, is that still right?",
   "What is Edlyn Carrow's dog?", [T("Edlyn Carrow", "dog", "Wisp")], "Wisp", "statement plus spec example tail; tags: that")

# ---------------- unstored_tail (6) ----------------
F = "unstored_tail"
def ut(setup, turn, fu, stated, never, gold, note):
    add(F, setup, turn, fu, stated, None, [never], list(stated), gold, note)
ut(["Florian Mace's boss is Greta Sollis."], "Florian Mace's boss isn't Hamish Dowd, that was someone else.",
   "Who is Florian Mace's boss?", [T("Florian Mace", "boss", "Greta Sollis")], T("Florian Mace", "boss", "Hamish Dowd"),
   "Greta Sollis", "known person, other value, that-was clause; tags: that")
ut(["Gwendolyn Ashe's city is Carrowmere."], "Gwendolyn Ashe's city isn't Pellingford, it never was.",
   "What is Gwendolyn Ashe's city?", [T("Gwendolyn Ashe", "city", "Carrowmere")], T("Gwendolyn Ashe", "city", "Pellingford"),
   "Carrowmere", "known person, other value, it-clause; tags: other")
ut(["Ivo Brannock's job is cooper."], "Odile Quarrel's job isn't cooper, that's stale.",
   "What is Odile Quarrel's job?", [T("Ivo Brannock", "job", "cooper")], T("Odile Quarrel", "job", "cooper"),
   None, "unknown person, that's-clause; tags: that")
ut(["Jessamy Thorne's language is Vorric."], "jessamy thorne's language isnt belvic, thats someone else",
   "What is Jessamy Thorne's language?", [T("Jessamy Thorne", "language", "Vorric")], T("Jessamy Thorne", "language", "Belvic"),
   "Vorric", "lowercase known person, other value, no apostrophes; tags: lower typo that")
ut(["My boss is Anselm Grey."], "My boss isn't Perrin Holt, which was my old manager.",
   "Who is my boss?", [T(U, "boss", "Anselm Grey")], T(U, "boss", "Perrin Holt"),
   "Anselm Grey", "first person, other value, which-was clause; tags: first that")
ut(["Kaspar Lune's dog is Fidget."], "Marisol Keene's dog isn't Fidget - that's another dog.",
   "What is Marisol Keene's dog?", [T("Kaspar Lune", "dog", "Fidget")], T("Marisol Keene", "dog", "Fidget"),
   None, "unknown person, dash that's-clause; tags: that")

# ---------------- control (16) ----------------
F = "control"
st = [T("Nico Barrow", "boss", "Ula Crane")]
den(F, ["Nico Barrow's boss is Ula Crane."], "Nico Barrow's boss isn't Ula Crane.", "Who is Nico Barrow's boss?",
    st, st[0], "plain isn't denial; tags:")
st = [T("Perdita Hume", "city", "Wolverton Marsh")]
den(F, ["Perdita Hume's city is Wolverton Marsh."], "Perdita Hume's city is not Wolverton Marsh.", "What is Perdita Hume's city?",
    st, st[0], "plain is-not denial; tags:")
st = [T("Silas Fenner", "city", "Arbury")]
cor(F, ["Silas Fenner's city is Arbury."], "Silas Fenner's city is Cobham Rise, not Arbury.", "What is Silas Fenner's city?",
    st, st[0], "Cobham Rise", "plain explicit correction; tags:")
st = [T("Tovah Lind", "boss", "Mercer Bloom")]
cor(F, ["Tovah Lind's boss is Mercer Bloom.", "Who is Tovah Lind's boss?"], "No, it's Anka Weir.", "Who is Tovah Lind's boss?",
    st, st[0], "Anka Weir", "plain contextual correction; tags: ctx")
st = [T("Uriel Stave", "job", "potter")]
den(F, ["Uriel Stave's job is potter.", "What is Uriel Stave's job?"], "That's wrong.", "What is Uriel Stave's job?",
    st, st[0], "plain contextual denial; tags: ctx")
st = [T("Wilhelmina Dray", "city", "Hexam")]
add(F, ["Wilhelmina Dray's city is Hexam."], "Wilhelmina Dray's boss is Corvin Ash.", "Who is Wilhelmina Dray's boss?",
    st, None, [], st + [T("Wilhelmina Dray", "boss", "Corvin Ash")], "Corvin Ash", "plain teach; tags:")
st = [T("Xanthe Moor", "language", "Riddic")]
add(F, ["Xanthe Moor's language is Riddic."], "What is Xanthe Moor's language?", "What is Xanthe Moor's language?",
    st, None, [], list(st), "Riddic", "plain question; tags:")
st = [T(U, "city", "Oldcastle Fen")]
add(F, ["My city is Oldcastle Fen."], "My boss is Remy Gault.", "Who is my boss?",
    st, None, [], st + [T(U, "boss", "Remy Gault")], "Remy Gault", "plain first-person teach; tags: first")
st = [T("Yardley Pim", "city", "Scarrow")]
cor(F, ["Yardley Pim's city is Scarrow.", "What is Yardley Pim's city?"], "Wrong, it's Tilbury Ness.", "What is Yardley Pim's city?",
    st, st[0], "Tilbury Ness", "plain contextual correction; tags: ctx")
st = [T("Zelda Morrow", "employer", "Quayside Rope Works")]
cor(F, ["Zelda Morrow's employer is Quayside Rope Works."], "Zelda Morrow's employer is Hartwell Glass now, not Quayside Rope Works.",
    "What is Zelda Morrow's employer?", st, st[0], "Hartwell Glass", "plain now/not correction; tags:")
st = [T("Abel Fontaine", "dog", "Rusk")]
den(F, ["Abel Fontaine's dog is Rusk."], "Abel Fontaine's dog isn't Rusk.", "What is Abel Fontaine's dog?",
    st, st[0], "plain denial; tags:")
st = [T("Bettina Crowe", "city", "Lanmoor")]
add(F, ["Bettina Crowe's city is Lanmoor."], "Bettina Crowe's sister is Marla Crowe.", "Who is Bettina Crowe's sister?",
    st, None, [], st + [T("Bettina Crowe", "sister", "Marla Crowe")], "Marla Crowe", "plain teach; tags:")
st = [T(U, "sister", "Philippa Dane")]
add(F, ["My sister is Philippa Dane."], "Who is my sister?", "Who is my sister?",
    st, None, [], list(st), "Philippa Dane", "plain first-person question; tags: first")
st = [T("Cyprian Holm", "job", "roper")]
den(F, ["Cyprian Holm's job is roper."], "Cyprian Holm's job is not roper.", "What is Cyprian Holm's job?",
    st, st[0], "plain is-not denial; tags:")
st = [T("Dagny Rell", "language", "Ostic")]
den(F, ["Dagny Rell's language is Ostic.", "What is Dagny Rell's language?"], "That's incorrect.", "What is Dagny Rell's language?",
    st, st[0], "plain contextual denial; tags: ctx")
st = [T("Eamon Kilby", "workplace", "Brightwater Lab")]
add(F, ["Eamon Kilby's workplace is Brightwater Lab."], "What is Eamon Kilby's workplace?", "What is Eamon Kilby's workplace?",
    st, None, [], list(st), "Brightwater Lab", "plain question; tags:")

# ---------------- self-checks ----------------
SPEC_EXAMPLES = ["that's old news", "old news", "that was last year", "that's outdated", "that's old",
                 "it's wrong now", "not anymore", "she quit", "sadly", "lol", "btw",
                 "or is that outdated", "is that still right", "which is a bakery", "that's wrong"]


def tags(it):
    return set(it["note"].split("tags:")[1].split()) if "tags:" in it["note"] else set()


def norm(s):
    return s.lower().replace("’", "'")


def novel(it):
    t = norm(it["turn"])
    t2 = t.replace("'", "")
    return not any(e in t or e.replace("'", "") in t2 for e in SPEC_EXAMPLES)


def check():
    errs = []
    fams = [it["family"] for it in ITEMS]
    for f, n in FAMILIES:
        if fams.count(f) != n:
            errs.append(f"family {f}: {fams.count(f)} != {n}")
    order = [f for f, n in FAMILIES for _ in range(n)]
    if fams != order:
        errs.append("family block order wrong")
    turns = [it["turn"] for it in ITEMS]
    if len(set(turns)) != len(turns):
        errs.append("duplicate turn")
    rels = set()
    for i, it in enumerate(ITEMS):
        if list(it) != FIELDS[1:]:
            errs.append(f"{i}: fields")
        if not it["setup"]:
            errs.append(f"{i}: empty setup")
        blob = " ".join(it["setup"])
        for s, r, v in it["stated_facts"]:
            rels.add(r)
            for w in (s, v):
                if w != U and w not in blob:
                    errs.append(f"{i}: {w!r} not in setup")
        if it["target"] is not None and it["target"] not in it["stated_facts"]:
            errs.append(f"{i}: target not in stated_facts")
        tg = tags(it)
        if "lower" in tg and it["turn"] != it["turn"].lower():
            errs.append(f"{i}: tagged lower but not lowercase")
        if "typo" in tg and not re.search(r"\b(thats|doesnt|isnt|its|dont)\b", it["turn"].lower()):
            errs.append(f"{i}: tagged typo without apostrophe-less word")
        if "ctx" in tg and not it["setup"][-1].rstrip().endswith("?"):
            errs.append(f"{i}: ctx without final question")
        if it["family"] == "pure_denial_that" and "ctx" not in tg:
            errs.append(f"{i}: pure_denial_that must be ctx")
    if len(rels) < 6:
        errs.append(f"only {len(rels)} relations")
    q = {}
    for f in CAUSE:
        its = [it for it in ITEMS if it["family"] == f]
        lo = sum("lower" in tags(it) for it in its)
        fp = sum("first" in tags(it) for it in its)
        q[f] = (lo, fp)
        if lo < 3: errs.append(f"{f}: lower {lo} < 3")
        if fp < 2: errs.append(f"{f}: first {fp} < 2")
    typo = sum("typo" in tags(it) for it in ITEMS)
    if typo < 3: errs.append(f"typo {typo} < 3")
    tc = [it for it in ITEMS if it["family"] == "that_correction"]
    nctx = sum("ctx" in tags(it) for it in tc)
    if nctx < 5 or len(tc) - nctx < 5: errs.append(f"that_correction ctx {nctx}/explicit {len(tc)-nctx}")
    nov = {}
    for f, n in FAMILIES:
        k = sum(novel(it) for it in ITEMS if it["family"] == f)
        nov[f] = k
        if 2 * k < n: errs.append(f"{f}: novel wording {k}/{n} < half")
    return errs, dict(quota_lower_first=q, typo=typo, tc_ctx=nctx, tc_explicit=len(tc) - nctx,
                      novel=nov, relations=len(rels))


if __name__ == "__main__":
    errs, info = check()
    print(json.dumps(info))
    if errs:
        print("SELF-CHECK FAIL:", *errs, sep="\n  ")
        sys.exit(1)
    with open(OUT, "w") as fh:
        for k, it in enumerate(ITEMS, 1):
            row = {"id": f"t258-{k:03d}", **it}
            assert list(row) == FIELDS
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"SELF-CHECK OK; wrote {len(ITEMS)} items to {OUT.name}")
