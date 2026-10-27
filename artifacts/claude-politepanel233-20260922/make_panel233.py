"""Generator for blind panel 233 (polite negative questions).
Hand-written, deterministic. One-word invented names only.
Run from repo root: python -B artifacts/claude-politepanel233-20260922/make_panel233.py
"""
import json, os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "panel.jsonl")
items = []


def add(family, setup, question, expect, gold, notes, clear=True):
    items.append({"id": "p233-%03d" % (len(items) + 1), "family": family, "setup": setup,
                  "question": question, "expect": expect, "gold": gold, "clear": clear,
                  "notes": notes})


# polite_taught: (setup, question, gold, note)
TAUGHT = [
    (["Kessa lives in Tarnby."], "Can't you tell me where Kessa lives?", "Tarnby", "can't you tell me where"),
    (["Orlo's boss is Venna."], "Don't you know who Orlo's boss is?", "Venna", "don't you know who"),
    (["Pim's city is Hollowmere."], "Won't you tell me Pim's city?", "Hollowmere", "won't you tell me"),
    (["Dace's sister is Merrow."], "Couldn't you remind me who Dace's sister is?", "Merrow", "couldn't you remind me who"),
    (["Tully lives in New Vessby."], "Do you not know where Tully lives?", "New Vessby", "do you not know where; multi-word value"),
    (["Brisa's teacher is Holm."], "Can't you remind me who Brisa's teacher is?", "Holm", "can't you remind me who"),
    (["Faro lives in Quenby.", "Lisle lives in Oxlade."], "Wouldn't you know where Faro lives?", "Quenby", "wouldn't you know where; distractor person"),
    (["Nyle's doctor is Ambry."], "Don't you remember who Nyle's doctor is?", "Ambry", "don't you remember who"),
    (["Corra's brother is Tamsel.", "Corra's friend is Ivo."], "Can't you say who Corra's brother is?", "Tamsel", "can't you say who; distractor relation"),
    (["Wren lives in Saltmarrow."], "Couldn't you tell me where Wren lives?", "Saltmarrow", "couldn't you tell me where"),
    (["Odo's manager is Pellam."], "Won't you remind me who Odo's manager is?", "Pellam", "won't you remind me who"),
    (["Garnet's town is Wickerly."], "Don't you know Garnet's town?", "Wickerly", "don't you know + possessive noun phrase"),
    (["Ilsa lives in East Corrow.", "Ilsa's dog is Pepper."], "Can you not tell me where Ilsa lives?", "East Corrow", "can you not tell me; multi-word value"),
    (["Borro's neighbour is Quill."], "Do you not remember who Borro's neighbour is?", "Quill", "do you not remember who"),
    (["Temmy's cousin is Arlo."], "Couldn't you just tell me who Temmy's cousin is?", "Arlo", "couldn't you just tell me"),
    (["Vesh lives in Fennick Cross."], "Don't you know where Vesh lives?", "Fennick Cross", "don't you know where"),
    (["Hettie's coach is Brannock."], "Can't you tell me Hettie's coach?", "Brannock", "can't you tell me + possessive noun phrase"),
    (["Lorn's boss is Sabine.", "Mabry's boss is Colwen."], "Wouldn't you be able to tell me who Lorn's boss is?", "Sabine", "wouldn't you be able to; same relation distractor"),
    (["Aveline lives in Pellow Green."], "Won't you say where Aveline lives?", "Pellow Green", "won't you say where"),
    (["Rudd's partner is Ellery."], "Don't you know who Rudd's partner is, please?", "Ellery", "don't you know + trailing please"),
    (["Solvi's city is Lower Brambleford."], "Can't you remind me what Solvi's city is?", "Lower Brambleford", "can't you remind me what"),
    (["Marek lives in Quenby.", "Marek's sister is Dova."], "Do you not know who Marek's sister is?", "Dova", "do you not know who"),
    (["Tibby's landlord is Gorse."], "Surely you can't have forgotten who Tibby's landlord is?", "Gorse", "surely you can't have forgotten"),
    (["Yola lives in Oxlade."], "Couldn't you please tell me where Yola lives?", "Oxlade", "couldn't you please tell me"),
]
for s, q, g, n in TAUGHT:
    add("polite_taught", s, q, "answer", g, "polite negative request (" + n + "); fact taught")

# polite_untaught: (setup, question, note)
UNTAUGHT = [
    (["Kessa lives in Tarnby."], "Can't you tell me where Brodie lives?", "person never mentioned"),
    (["Orlo's boss is Venna."], "Don't you know who Orlo's sister is?", "same person, other relation"),
    (["Pim lives in Hollowmere."], "Won't you tell me Pim's boss?", "same person, other relation"),
    (["Dace's sister is Merrow."], "Couldn't you remind me who Dace's brother is?", "sibling of other kind"),
    (["Tully's teacher is Holm."], "Do you not know where Tully lives?", "home never taught"),
    (["Faro lives in Quenby."], "Wouldn't you know where Lisle lives?", "other person never mentioned"),
    (["Nyle's doctor is Ambry."], "Don't you remember who Ambry's doctor is?", "value person used as subject; nothing taught"),
    (["Corra's friend is Ivo."], "Can't you say who Corra's brother is?", "other relation"),
    (["Wren's manager is Pellam."], "Couldn't you tell me who Odo's manager is?", "other person"),
    (["Garnet lives in Wickerly."], "Don't you know Garnet's cousin?", "other relation"),
    ([], "Can you not tell me where Ilsa lives?", "empty notebook"),
    (["Borro's neighbour is Quill."], "Do you not remember who Quill's neighbour is?", "reverse direction not taught; neighbour is not assumed symmetric", ),
]
for row in UNTAUGHT:
    s, q, n = row
    add("polite_untaught", s, q, "abstain", None, "polite negative request; fact never taught (" + n + ")",
        clear=("reverse" not in n))

# true_negation: (setup, question, note)
TRUENEG = [
    (["Kessa lives in Tarnby."], "Where doesn't Kessa live?", "where doesn't"),
    (["Orlo's boss is Venna."], "Who isn't Orlo's boss?", "who isn't"),
    (["Pim's city is Hollowmere."], "Which town is not Pim's city?", "which ... is not"),
    (["Tully lives in New Vessby."], "Didn't Tully live in Quenby before?", "past-tense negated yes/no about a different town"),
    (["Dace's sister is Merrow."], "Who is not Dace's sister?", "who is not"),
    (["Wren lives in Saltmarrow."], "Where does Wren not live?", "where does ... not"),
    (["Nyle's doctor is Ambry."], "Who isn't Nyle's doctor?", "who isn't"),
    (["Garnet's town is Wickerly."], "Which town isn't Garnet's town?", "which town isn't"),
    (["Faro lives in Quenby."], "Didn't Faro live in Quenby before?", "past-tense negated yes/no naming the current town; stating 'Quenby' as an answer value is wrong"),
    (["Brisa's teacher is Holm."], "Who is not Brisa's teacher?", "who is not"),
    (["Vesh lives in Fennick Cross."], "Name a place where Vesh doesn't live.", "imperative, negated"),
    (["Odo's manager is Pellam."], "Which person isn't Odo's manager?", "which person isn't"),
    (["Aveline lives in Pellow Green."], "Where has Aveline never lived?", "never"),
    (["Corra's brother is Tamsel."], "Who isn't Corra's brother?", "who isn't"),
    (["Yola lives in Oxlade."], "Which city does Yola not live in?", "which ... not ... in"),
    (["Solvi's city is Lower Brambleford."], "What city isn't Solvi's city?", "what ... isn't"),
]
for s, q, n in TRUENEG:
    add("true_negation", s, q, "no_value", None,
        "question asks about a negation (" + n + "); must not state a value as the answer",
        clear=("before" not in q))

# negated_statement: (setup, note)
NEGSTMT = [
    (["Kessa doesn't live in Tarnby."], "doesn't"),
    (["Orlo does not live in Hollowmere."], "does not"),
    (["Pim doesn't live in New Vessby.", "Pim's boss is Venna."], "doesn't + unrelated fact"),
    (["Tully does not live in Quenby."], "does not"),
    (["Dace doesn't live in Saltmarrow.", "Merrow lives in Saltmarrow."], "doesn't + other person lives there"),
    (["Wren doesn't live in Fennick Cross."], "doesn't; multi-word town"),
    (["Nyle does not live in Oxlade.", "Nyle's sister is Brisa."], "does not + unrelated fact"),
    (["Garnet doesn't live in Wickerly."], "doesn't"),
]
for s, n in NEGSTMT:
    name = s[0].split()[0]
    add("negated_statement", s, "Where does %s live?" % name, "abstain", None,
        "only a negated home statement (" + n + "); must abstain, must not answer the negated town")

assert len(items) == 60, len(items)
with open(OUT, "w") as f:
    for it in items:
        f.write(json.dumps(it, ensure_ascii=False) + "\n")
print("wrote", len(items), OUT)
