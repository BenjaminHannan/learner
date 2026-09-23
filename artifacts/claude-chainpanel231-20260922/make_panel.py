"""Generator for chain panel 231 (blind, hand-written items).
All names, towns, companies and languages are invented.
Run from repo root: python3 artifacts/claude-chainpanel231-20260922/make_panel.py
"""
import json, os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "panel.jsonl")

# (family, setup, question, expect, gold, hops, clear, notes)
A, X = "answer", "abstain"
items = []
def add(fam, setup, q, gold, hops, expect=A, clear=True, notes=""):
    items.append(dict(family=fam, setup=setup, question=q, expect=expect,
                      gold=gold, hops=hops, clear=clear, notes=notes))

# ---------------- 1 verb_2hop ----------------
F = "verb_2hop"
add(F, ["Tamsin Arlowe's boss is Gideon Pelk.", "Gideon Pelk lives in Tarrowby."],
    "Where does Tamsin Arlowe's boss live?", "Tarrowby", 2, notes="plain two-hop, full name")
add(F, ["Orla Venner's sister is Brisa Venner.", "Brisa Venner speaks Tessarine.", "Orla Venner speaks Quellish."],
    "What language does Orla's sister speak?", "Tessarine", 2, notes="first name only; distractor: Orla's own language")
add(F, ["Hollis Crane's husband is Marek Dovey.", "Marek Dovey works at Pellam Glassworks."],
    "Where does Hollis's husband work?", "Pellam Glassworks", 2, notes="works-at chain")
add(F, ["Juno Faircloth lives in Quenmoor.", "Juno Faircloth's neighbor is Ansel Brisk.", "Ansel Brisk lives in Ashkettle."],
    "Where does Juno Faircloth's neighbor live?", "Ashkettle", 2, notes="distractor: Juno's own town")
add(F, ["Petra Loam's cousin is Ivo Marchetti-Sands.", "Ivo Marchetti-Sands speaks Brennic.", "Wren Oddley speaks Ormathi."],
    "What language does Petra Loam's cousin speak?", "Brennic", 2, notes="hyphenated surname; unrelated person distractor")
add(F, ["Selby Rourke's mentor is Adaeze Holloway.", "Adaeze Holloway works at Quarrick Freight.", "Selby Rourke works at Marrowfield Dairy."],
    "Where does Selby's mentor work?", "Quarrick Freight", 2, notes="distractor: Selby's own workplace")
add(F, ["Nell Garrity's brother is Tobiah Garrity.", "Tobiah Garrity lives in Wendlecombe.", "Tobiah Garrity works at Ostley Printworks."],
    "Where does Nell Garrity's brother live?", "Wendlecombe", 2, notes="middle person has two different-kind facts; ask lives")
add(F, ["Cato Brennaway's wife is Lise Ferrand.", "Lise Ferrand speaks Solvarran.", "Lise Ferrand lives in Pellwick."],
    "What language does Cato's wife speak?", "Solvarran", 2, notes="speaks vs lives on same person")
add(F, ["Mirelle Kost's landlord is Barnaby Ugo.", "Barnaby Ugo works at Vannick Robotics.", "Mirelle Kost's dentist is Hana Stroop.", "Hana Stroop works at Lumhaven Studios."],
    "Where does Mirelle Kost's landlord work?", "Vannick Robotics", 2, notes="parallel distractor chain via another relation")

# ---------------- 2 possessive_2hop ----------------
F = "possessive_2hop"
add(F, ["Dorian Hale's boss is Fenna Coyle.", "Fenna Coyle lives in Drossany."],
    "What is Dorian Hale's boss's town?", "Drossany", 2, notes="'town' maps to lives-in")
add(F, ["Ysolde Brack's boss is Lachlan Merriweather.", "Lachlan Merriweather's boss is Oona Tillery."],
    "Who is Ysolde's boss's boss?", "Oona Tillery", 2, notes="same relation twice")
add(F, ["Kestrel Obi's sister is Rhona Obi.", "Rhona Obi's husband is Faris Quill.", "Kestrel Obi's husband is Dunstan Pryce."],
    "Who is Kestrel Obi's sister's husband?", "Faris Quill", 2, notes="distractor: Kestrel's own husband")
add(F, ["Bram Tolliver's coach is Sunniva Rask.", "Sunniva Rask speaks Kettish."],
    "What is Bram Tolliver's coach's language?", "Kettish", 2, notes="'language' maps to speaks")
add(F, ["Idris Maplethorpe's friend is Gwen Aldous.", "Gwen Aldous's brother is Corwin Aldous.", "Gwen Aldous lives in Ivelford."],
    "Who is Idris's friend's brother?", "Corwin Aldous", 2, notes="shared surname; distractor town")
add(F, ["Marta Svell's neighbor is Oswin Kade.", "Oswin Kade lives in Callisk.", "Marta Svell lives in Morrowdeep."],
    "What is Marta Svell's neighbor's town?", "Callisk", 2, notes="distractor: Marta's own town")
add(F, ["Quincy Adebayo-Fell's wife is Thora Linden.", "Thora Linden's mentor is Rafe Culloden."],
    "Who is Quincy Adebayo-Fell's wife's mentor?", "Rafe Culloden", 2, notes="hyphenated first-hop name")
add(F, ["Leocadia Pym's cousin is Aurel Stane.", "Aurel Stane speaks Dravonic.", "Aurel Stane works at Gorsebright Tiles."],
    "What is Leocadia's cousin's language?", "Dravonic", 2, notes="two facts on middle person, different kinds")
add(F, ["Emrys Talbot's dentist is Noor Haverill.", "Noor Haverill's husband is Silas Wendt.", "Emrys Talbot's boss is Silas Brandt."],
    "Who is Emrys Talbot's dentist's husband?", "Silas Wendt", 2, notes="near-name distractor Silas Brandt")

# ---------------- 3 of_form ----------------
F = "of_form"
add(F, ["Fiona Castell's boss is Harlan Voss.", "Harlan Voss lives in Sunderhollow."],
    "Where does the boss of Fiona Castell live?", "Sunderhollow", 2)
add(F, ["Ruben Achterberg's boss is Delphine Moor.", "Delphine Moor's sister is Celeste Moor."],
    "Who is the sister of Ruben's boss?", "Celeste Moor", 2, notes="mixed of + possessive")
add(F, ["Anouk Ferris's brother is Jory Ferris.", "Jory Ferris speaks Ilmese.", "Anouk Ferris speaks Varnic."],
    "What language does the brother of Anouk Ferris speak?", "Ilmese", 2, notes="distractor: Anouk's own language")
add(F, ["Talia Wren-Hoskins's husband is Morgan Tilde.", "Morgan Tilde works at Halvenworth Logistics."],
    "Where does the husband of Talia Wren-Hoskins work?", "Halvenworth Logistics", 2)
add(F, ["Benedek Sorrel's friend is Cressida Nkemelu.", "Cressida Nkemelu's boss is Ambrose Fitch.", "Benedek Sorrel's boss is Ulla Penhale."],
    "Who is the boss of Benedek's friend?", "Ambrose Fitch", 2, notes="distractor: Benedek's own boss")
add(F, ["Greer Mallinson's neighbor is Pax Oyelaran.", "Pax Oyelaran lives in Brindlecote.", "Pax Oyelaran works at Tindlerowe Bakery."],
    "What town does the neighbor of Greer Mallinson live in?", "Brindlecote", 2)
add(F, ["Soren Achebe's wife is Liesl Harrow.", "Liesl Harrow's brother is Evander Harrow."],
    "Who is the brother of the wife of Soren Achebe?", "Evander Harrow", 2, notes="double of-form")
add(F, ["Mabel Quist's mentor is Oren Bellweather.", "Oren Bellweather speaks Tessarine.", "Mabel Quist's coach is Ines Karlo.", "Ines Karlo speaks Kettish."],
    "Which language does the mentor of Mabel Quist speak?", "Tessarine", 2, notes="parallel distractor chain")
add(F, ["Ignatius Rowe's cousin is Delia Frome.", "Delia Frome works at Ostley Printworks."],
    "Where does the cousin of Ignatius Rowe work?", "Ostley Printworks", 2)

# ---------------- 4 three_hop ----------------
F = "three_hop"
add(F, ["Winifred Aske's boss is Callum Ostrander.", "Callum Ostrander's sister is Maren Ostrander.", "Maren Ostrander lives in Oskerwell."],
    "Where does Winifred's boss's sister live?", "Oskerwell", 3)
add(F, ["Jasper Kilby's wife is Ottoline Reyes-Hart.", "Ottoline Reyes-Hart's brother is Lucan Reyes-Hart.", "Lucan Reyes-Hart works at Vannick Robotics.", "Jasper Kilby works at Marrowfield Dairy."],
    "Where does Jasper Kilby's wife's brother work?", "Vannick Robotics", 3, notes="distractor: Jasper's workplace")
add(F, ["Prue Addington's friend is Halvard Nix.", "Halvard Nix's mentor is Zelda Crome.", "Zelda Crome speaks Ormathi."],
    "What language does Prue Addington's friend's mentor speak?", "Ormathi", 3)
add(F, ["Taddeo Lume's boss is Agnes Fairweather.", "Agnes Fairweather's boss is Rolf Imrie.", "Rolf Imrie's boss is Serafina Doyle."],
    "Who is Taddeo's boss's boss's boss?", "Serafina Doyle", 3, notes="same relation three times")
add(F, ["Keziah Monk's sister is Philippa Monk.", "Philippa Monk's husband is Arvid Strand.", "Arvid Strand lives in Tarrowby.", "Philippa Monk lives in Quenmoor."],
    "Where does the husband of Keziah Monk's sister live?", "Tarrowby", 3, notes="of + possessive; distractor: middle person's town")
add(F, ["Leopold Vance's neighbor is Imogen Tarn.", "Imogen Tarn's cousin is Bartholomew Esk.", "Bartholomew Esk works at Quarrick Freight."],
    "Where does Leopold Vance's neighbor's cousin work?", "Quarrick Freight", 3)
add(F, ["Oriana Beck's coach is Dmitri Halloran.", "Dmitri Halloran's wife is Solange Pitt.", "Solange Pitt's brother is Ewan Pitt."],
    "Who is Oriana's coach's wife's brother?", "Ewan Pitt", 3, notes="three person hops")
add(F, ["Cosmo Faraday's landlord is Tilde Ambrose.", "Tilde Ambrose's son is Ned Ambrose.", "Ned Ambrose speaks Solvarran.", "Tilde Ambrose speaks Brennic."],
    "What language does Cosmo Faraday's landlord's son speak?", "Solvarran", 3, notes="distractor: middle person's language")
add(F, ["Harriet Okonjo's brother is Felix Okonjo.", "Felix Okonjo's boss is Magda Stirling.", "Magda Stirling lives in Drossany."],
    "What is Harriet's brother's boss's town?", "Drossany", 3, notes="possessive 'town' form")

# ---------------- 5 user_chain ----------------
F = "user_chain"
add(F, ["My boss is Rosalind Kemp.", "Rosalind Kemp lives in Ashkettle."],
    "Where does my boss live?", "Ashkettle", 2)
add(F, ["My sister is Clementine Hart.", "Clementine Hart's husband is Bastian Orlow."],
    "Who is my sister's husband?", "Bastian Orlow", 2)
add(F, ["My friend is Ezra Pollard.", "Ezra Pollard works at Gorsebright Tiles.", "My brother is Milo Tennant.", "Milo Tennant works at Pellam Glassworks."],
    "Where does my friend work?", "Gorsebright Tiles", 2, notes="parallel distractor chain")
add(F, ["My neighbor is Ludmila Carrow.", "Ludmila Carrow speaks Ilmese."],
    "What language does my neighbor speak?", "Ilmese", 2)
add(F, ["My boss is Anselm Rook.", "Anselm Rook's boss is Viveka Lund.", "Viveka Lund lives in Callisk."],
    "Where does my boss's boss live?", "Callisk", 3)
add(F, ["My wife is Esme Dalgarno.", "Esme Dalgarno's brother is Rory Dalgarno.", "Rory Dalgarno works at Lumhaven Studios."],
    "Where does my wife's brother work?", "Lumhaven Studios", 3)
add(F, ["My mentor is Horace Wyle.", "Horace Wyle lives in Pellwick.", "Tobin Arkwright lives in Ivelford."],
    "What town does my mentor live in?", "Pellwick", 2, notes="unrelated person distractor")
add(F, ["My cousin is Saoirse Lambe.", "Saoirse Lambe's husband is Kofi Brandvold."],
    "Who's the husband of my cousin?", "Kofi Brandvold", 2, notes="of-form + contraction")
add(F, ["My coach is Gunnar Treece.", "Gunnar Treece speaks Varnic.", "My dentist is Aletta Moss.", "Aletta Moss speaks Dravonic."],
    "Which language does my dentist speak?", "Dravonic", 2, notes="asks second of two parallel chains")

# ---------------- 6 yes_no_chain ----------------
F = "yes_no_chain"
add(F, ["Valeria Dunn's boss is Osric Meade.", "Osric Meade lives in Wendlecombe."],
    "Does Valeria Dunn's boss live in Wendlecombe?", "yes", 2)
add(F, ["Tobias Wrenfield's boss is Mina Castellane.", "Mina Castellane lives in Morrowdeep.", "Tobias Wrenfield lives in Sunderhollow."],
    "Does Tobias's boss live in Sunderhollow?", "no", 2, notes="asked town is Tobias's own town (lure)")
add(F, ["Adela Frick's sister is Corinna Frick.", "Corinna Frick speaks Quellish."],
    "Does Adela's sister speak Quellish?", "yes", 2)
add(F, ["Neville Ashby's husband is Joaquin Tate.", "Joaquin Tate works at Halvenworth Logistics."],
    "Does Neville Ashby's husband work at Halvenworth Logistics?", "yes", 2)
add(F, ["Rhiannon Vale's neighbor is Duncan Ferro.", "Duncan Ferro lives in Brindlecote.", "Rhiannon Vale's cousin is Aisling Ferro.", "Aisling Ferro lives in Oskerwell."],
    "Does Rhiannon Vale's neighbor live in Oskerwell?", "no", 2, notes="asked town belongs to parallel chain (lure)")
add(F, ["Barnaby Keel's sister is Petronella Keel.", "Petronella Keel's husband is Lorcan Abernathy."],
    "Is Barnaby Keel's sister's husband Lorcan Abernathy?", "yes", 2)
add(F, ["Seraphine Otto's boss is Wendel Grise.", "Wendel Grise's wife is Maud Grise.", "Seraphine Otto's wife is Ilse Bramwell."],
    "Is Seraphine Otto's boss's wife Ilse Bramwell?", "no", 2, notes="asked name is Seraphine's own wife (lure)")
add(F, ["Crispin Yarrow's friend is Beatrix Lowe.", "Beatrix Lowe's brother is Anders Lowe.", "Anders Lowe lives in Tarrowby."],
    "Does Crispin Yarrow's friend's brother live in Tarrowby?", "yes", 3)
add(F, ["Olwen Pascoe's mentor is Thaddeus Rill.", "Thaddeus Rill lives in Callisk."],
    "Does the mentor of Olwen Pascoe live in Quenmoor?", "no", 2, notes="asked town not in setup; one residence assumed")

# ---------------- 7 casual ----------------
F = "casual"
add(F, ["Isolde Brannock's boss is Tiberius Wolde.", "Tiberius Wolde lives in Ivelford."],
    "where does isolde brannock's boss live", "Ivelford", 2, notes="all lowercase, no punctuation")
add(F, ["Hamish Coldwell's boss is Perpetua Ang.", "Perpetua Ang lives in Drossany."],
    "Where's Hamish's boss live?", "Drossany", 2, notes="where's contraction")
add(F, ["Liora Gaunt's sister is Fern Gaunt.", "Fern Gaunt lives in Ashkettle.", "Liora Gaunt lives in Pellwick."],
    "so what town does Liora's sister live in?", "Ashkettle", 2, notes="filler 'so'; distractor own town")
add(F, ["Desmond Achterlo's husband is Rufus Penn.", "Rufus Penn works at Tindlerowe Bakery."],
    "hey, where does desmond's husband work?", "Tindlerowe Bakery", 2, notes="greeting filler, lowercase name")
add(F, ["Marisol Eke's cousin is Jarrah Voight.", "Jarrah Voight speaks Kettish."],
    "what language does marisol's cousin speak", "Kettish", 2, notes="lowercase, no question mark")
add(F, ["My boss is Cordelia Fenwick.", "Cordelia Fenwick lives in Quenmoor."],
    "wait where does my boss live again?", "Quenmoor", 2, notes="user chain with filler")
add(F, ["Alaric Stroud's friend is Nadia Oshiro.", "Nadia Oshiro's brother is Kip Oshiro."],
    "who's alaric's friend's brother?", "Kip Oshiro", 2, notes="lowercase person-person chain")
add(F, ["Gemma Tallis's neighbor is Ruairi Cope.", "Ruairi Cope lives in Morrowdeep."],
    "Do you know where Gemma Tallis's neighbor lives?", "Morrowdeep", 2, notes="indirect question form")
add(F, ["Evadne Birch's boss is Lorne Mackie.", "Lorne Mackie works at Quarrick Freight.", "Evadne Birch works at Ostley Printworks."],
    "ok and where does evadne's boss work", "Quarrick Freight", 2, notes="filler, lowercase; distractor own workplace")

# ---------------- 8 traps (abstain) ----------------
F = "traps"
add(F, ["Sabine Holt's boss is Everard Quine.", "Sabine Holt lives in Callisk."],
    "Where does Sabine Holt's boss live?", None, 2, expect=X,
    notes="missing middle fact: boss stored, boss's town not; lure = Sabine's own town")
add(F, ["Ottilie Marsh's sister is Greta Marsh.", "Greta Marsh lives in Tarrowby."],
    "What language does Ottilie's sister speak?", None, 2, expect=X,
    notes="missing middle fact: sister's language not stored (town is)")
add(F, ["My boss is Ferdinand Aske.", "Ferdinand Aske speaks Brennic."],
    "Where does my boss work?", None, 2, expect=X,
    notes="missing middle fact on user chain: workplace not stored")
add(F, ["Clara Ingleby's boss is Rowan Petch.", "Rowan Petch lives in Wendlecombe."],
    "Where does Lysander Obuya's boss live?", None, 2, expect=X,
    notes="unknown person: Lysander Obuya never mentioned")
add(F, ["Mercer Doyle's brother is Hollis Doyle.", "Hollis Doyle works at Pellam Glassworks."],
    "Where does Mercer Doyle's cousin work?", None, 2, expect=X,
    notes="unknown middle: no cousin stored (brother is)")
add(F, ["Anneka Frost's boss is Julius Carne.", "Anneka Frost's mentor is Delyth Orme.", "Delyth Orme lives in Brindlecote."],
    "Where does Anneka Frost's boss live?", None, 2, expect=X,
    notes="different relation: town stored for mentor, not boss")
add(F, ["Bertil Nash's wife is Ramona Kell.", "Ramona Kell works at Sunderhollow Mills."],
    "Where does Bertil Nash's wife live?", None, 2, expect=X, clear=True,
    notes="different relation: works-at stored (company named after a town), lives-in not")
add(F, ["Cyrus Ellery's boss is Magnus Thwaite.", "Magnus Thwaite lives in Pellwick.", "Magnus Thwaite lives in Oskerwell."],
    "Where does Cyrus Ellery's boss live?", None, 2, expect=X, clear=False,
    notes="conflict: two towns for middle person; a human might treat the later line as a correction")
add(F, ["Dagny Rourke's sister is Linnea Rourke.", "Linnea Rourke lives in Quenmoor.", "Linnea Rourke lives in Ivelford.", "Dagny Rourke lives in Quenmoor."],
    "Does Dagny's sister live in Ivelford?", None, 2, expect=X, clear=False,
    notes="conflict: two towns for middle person, yes/no form")

# ---------------- write ----------------
fams = ["verb_2hop", "possessive_2hop", "of_form", "three_hop", "user_chain",
        "yes_no_chain", "casual", "traps"]
assert len(items) == 72, len(items)
for f in fams:
    assert sum(i["family"] == f for i in items) == 9, f
with open(OUT, "w") as fh:
    for n, it in enumerate(items, 1):
        assert 1 <= len(it["setup"]) <= 5
        if it["expect"] == "answer":
            assert it["gold"] is not None
            if it["gold"] not in ("yes", "no"):
                assert any(it["gold"] in s for s in it["setup"]), it
        rec = {"id": f"c231-{n:03d}", **it}
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
print("wrote", OUT, len(items))
