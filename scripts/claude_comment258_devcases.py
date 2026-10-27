#!/usr/bin/env python3
"""Exp 258 dev set (own wordings, fictional names; nothing copied from any
panel). Writes artifacts/claude-comment258-20260922/dev258.jsonl in the
corrtail258 item shape (11 fields) plus, on restart items only,
"restart": true and "extra": [[question, must_not_value, must_value]].

Families: that_denial, that_correction, pure_denial_that,
other_tail_denial, keep, question_tail, unstored_tail, control, restart.
Expectations are what a right answer is, not what any arm does.
"""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path("artifacts/claude-comment258-20260922/dev258.jsonl")
E, CI, L, PB = "employer", "city", "language", "place_of_birth"

ITEMS: list[dict] = []


def add(fam, setup, turn, follow, stated, target, gone, store, gold, note,
        **extra):
    it = {"family": fam, "setup": setup, "turn": turn, "followup": follow,
          "stated_facts": stated, "target": target, "expect_gone": gone,
          "expect_store": store, "gold_followup": gold, "note": note}
    it.update(extra)
    ITEMS.append(it)


def deny(fam, setup, turn, follow, stated, target, note, **kw):
    add(fam, setup, turn, follow, stated, target, [target],
        [f for f in stated if f != target], None, note, **kw)


def corr(fam, setup, turn, follow, stated, target, new, note, **kw):
    add(fam, setup, turn, follow, stated, target, [target],
        [new] + [f for f in stated if f != target], new[2], note, **kw)


# ---------------------------------------------------------------- that_denial (14)
deny("that_denial", ["Tirzah works at Oakhollow."],
     "Tirzah doesn't work at Oakhollow, that's ancient history.",
     "Where does Tirzah work?", [["Tirzah", E, "Oakhollow"]],
     ["Tirzah", E, "Oakhollow"], "verb, comma that's")
deny("that_denial", ["Brannoc lives in Stilby."],
     "Brannoc doesn't live in Stilby anymore - that was two years ago.",
     "Where does Brannoc live?", [["Brannoc", CI, "Stilby"]],
     ["Brannoc", CI, "Stilby"], "verb anymore, dash that was")
deny("that_denial", ["Quenna's boss is Harlan."],
     "Harlan isn't Quenna's boss (that changed in spring).",
     "Who is Quenna's boss?", [["Quenna", "boss", "Harlan"]],
     ["Quenna", "boss", "Harlan"], "reversed possessive, bracket that")
deny("that_denial", ["Morwen speaks Talvic."],
     "Morwen does not speak Talvic; that was a mix-up.",
     "What language does Morwen speak?", [["Morwen", L, "Talvic"]],
     ["Morwen", L, "Talvic"], "verb, semicolon that was")
deny("that_denial", ["Idony's manager is Crale."],
     "Idony's manager is not Crale, which was true last year.",
     "Who is Idony's manager?", [["Idony", "manager", "Crale"]],
     ["Idony", "manager", "Crale"], "possessive not, which was")
deny("that_denial", ["Pertwee was born in Lambsey."],
     "Pertwee wasn't born in Lambsey, thats a mistake.",
     "Where was Pertwee born?", [["Pertwee", PB, "Lambsey"]],
     ["Pertwee", PB, "Lambsey"], "wasn't born, thats typo")
deny("that_denial", ["Ottoline works at Crumbeck."],
     "ottoline doesnt work at crumbeck, thats old",
     "where does ottoline work?", [["Ottoline", E, "Crumbeck"]],
     ["Ottoline", E, "Crumbeck"], "lower typo, thats")
deny("that_denial", ["Sabeth lives in Gorran."],
     "sabeth no longer lives in gorran, that is out of date",
     "where does sabeth live?", [["Sabeth", CI, "Gorran"]],
     ["Sabeth", CI, "Gorran"], "lower, no longer, that is")
deny("that_denial", ["Vardis's teacher is Elwin."],
     "Elwin is not Vardis's teacher — that was his old school.",
     "Who is Vardis's teacher?", [["Vardis", "teacher", "Elwin"]],
     ["Vardis", "teacher", "Elwin"], "reversed, em dash that was")
deny("that_denial", ["Hollin works at Pegwell.", "Hollin lives in Ashmead."],
     "Hollin doesn't work at Pegwell, this is old information.",
     "Where does Hollin work?",
     [["Hollin", E, "Pegwell"], ["Hollin", CI, "Ashmead"]],
     ["Hollin", E, "Pegwell"], "verb, this is, second fact kept")
deny("that_denial", ["Corisande speaks Brevish."],
     "That's not true, Corisande doesn't speak Brevish, that was a joke.",
     "What language does Corisande speak?", [["Corisande", L, "Brevish"]],
     ["Corisande", L, "Brevish"], "deny prefix + verb + that was")
deny("that_denial", ["Neddy's boss is Prowse."],
     "Neddy's boss isn't Prowse, that's not right anymore.",
     "Who is Neddy's boss?", [["Neddy", "boss", "Prowse"]],
     ["Neddy", "boss", "Prowse"], "possessive isn't, that's not")
deny("that_denial", ["Wilmot lives in Tarrock."],
     "Wilmot doesn't live in Tarrock, that isnt current.",
     "Where does Wilmot live?", [["Wilmot", CI, "Tarrock"]],
     ["Wilmot", CI, "Tarrock"], "verb, that isnt typo")
deny("that_denial", ["My boss is Garrow."],
     "My boss isn't Garrow, that's old news.",
     "Who is my boss?", [["USER", "boss", "Garrow"]],
     ["USER", "boss", "Garrow"], "first: base has no first-person denial")

# ---------------------------------------------------------------- that_correction (12)
corr("that_correction", ["Emrys works at Dunkery.", "Where does Emrys work?"],
     "No, it's Felsham, that's the new place.", "Where does Emrys work?",
     [["Emrys", E, "Dunkery"]], ["Emrys", E, "Dunkery"],
     ["Emrys", E, "Felsham"], "ctx it's Z, that's")
corr("that_correction", ["Rowena lives in Pillock.", "Where does Rowena live?"],
     "Actually it's Marbury - that was her old town.",
     "Where does Rowena live?", [["Rowena", CI, "Pillock"]],
     ["Rowena", CI, "Pillock"], ["Rowena", CI, "Marbury"],
     "ctx actually it's Z, dash that was")
corr("that_correction", ["Thibault's boss is Anker.", "Who is Thibault's boss?"],
     "nope, it's Rennard, thats outdated", "who is thibault's boss?",
     [["Thibault", "boss", "Anker"]], ["Thibault", "boss", "Anker"],
     ["Thibault", "boss", "Rennard"], "ctx lower thats")
corr("that_correction", ["Gwenllian speaks Orvic.",
                         "What language does Gwenllian speak?"],
     "No, she speaks Saddish now (that was years ago).",
     "What language does Gwenllian speak?", [["Gwenllian", L, "Orvic"]],
     ["Gwenllian", L, "Orvic"], ["Gwenllian", L, "Saddish"],
     "ctx pronoun now, bracket that was")
corr("that_correction", ["Lucan works at Hebden.", "Where does Lucan work?"],
     "Wrong, it's Tolworth; which is where he moved.",
     "Where does Lucan work?", [["Lucan", E, "Hebden"]],
     ["Lucan", E, "Hebden"], ["Lucan", E, "Tolworth"],
     "ctx wrong it's Z, semicolon which is")
corr("that_correction", ["Ysolde lives in Brackwater."],
     "Actually, Ysolde lives in Cawthorne, not Brackwater, that's old.",
     "Where does Ysolde live?", [["Ysolde", CI, "Brackwater"]],
     ["Ysolde", CI, "Brackwater"], ["Ysolde", CI, "Cawthorne"],
     "explicit not W, that's")
corr("that_correction", ["Ambrin works at Kelloway."],
     "Ambrin doesn't work at Kelloway, she works at Rooksby, that was ages ago.",
     "Where does Ambrin work?", [["Ambrin", E, "Kelloway"]],
     ["Ambrin", E, "Kelloway"], ["Ambrin", E, "Rooksby"],
     "explicit deny + positive, that was")
corr("that_correction", ["Farris's manager is Tuck."],
     "Farris's manager isn't Tuck, it's Pomeroy - that's the old one.",
     "Who is Farris's manager?", [["Farris", "manager", "Tuck"]],
     ["Farris", "manager", "Tuck"], ["Farris", "manager", "Pomeroy"],
     "explicit possessive isn't, it's Z, dash that's")
corr("that_correction", ["Isolde speaks Carnic."],
     "No, Isolde speaks Vennic, not Carnic (this is recent).",
     "What language does Isolde speak?", [["Isolde", L, "Carnic"]],
     ["Isolde", L, "Carnic"], ["Isolde", L, "Vennic"],
     "explicit no + not W, bracket this is")
corr("that_correction", ["Petronel was born in Addleby."],
     "correction: petronel was born in Scarrow, not Addleby, thats a typo",
     "where was petronel born?", [["Petronel", PB, "Addleby"]],
     ["Petronel", PB, "Addleby"], ["Petronel", PB, "Scarrow"],
     "explicit lower thats")
corr("that_correction", ["Jory's sister is Kerensa.", "Who is Jory's sister?"],
     "No, her name is Merryn, that's a different person.",
     "Who is Jory's sister?", [["Jory", "sister", "Kerensa"]],
     ["Jory", "sister", "Kerensa"], ["Jory", "sister", "Merryn"],
     "ctx 'her name is Z': base shape not a correction (hard)")
corr("that_correction", ["Wendel works at Ruscombe.", "Where does Wendel work?"],
     "No, that's wrong, it's Lanyon, which is his new job.",
     "Where does Wendel work?", [["Wendel", E, "Ruscombe"]],
     ["Wendel", E, "Ruscombe"], ["Wendel", E, "Lanyon"],
     "ctx deny + it's Z + which is")

# ---------------------------------------------------------------- pure_denial_that (10)
for n, (s, r, v, setup, q, turn, note) in enumerate([
    ("Anwen", E, "Stoke Parva", "Anwen works at Stoke Parva.",
     "Where does Anwen work?", "That's wrong, that was last year.",
     "that's wrong + that was"),
    ("Brice", CI, "Hawkridge", "Brice lives in Hawkridge.",
     "Where does Brice live?", "That's not right - that's stale.",
     "that's not right + dash"),
    ("Cressida", "boss", "Moyle", "Cressida's boss is Moyle.",
     "Who is Cressida's boss?", "You're wrong, which is fine, that's old.",
     "you're wrong + which is"),
    ("Dunstan", L, "Perric", "Dunstan speaks Perric.",
     "What language does Dunstan speak?", "incorrect; that was ages ago",
     "lower incorrect; semicolon"),
    ("Elowen", PB, "Sturry", "Elowen was born in Sturry.",
     "Where was Elowen born?", "Not true (that was her brother).",
     "not true + bracket"),
    ("Fitch", "manager", "Groat", "Fitch's manager is Groat.",
     "Who is Fitch's manager?", "thats wrong, thats old info",
     "lower thats x2"),
    ("Galen", E, "Wexcombe", "Galen works at Wexcombe.",
     "Where does Galen work?", "That's incorrect — this is from before.",
     "em dash this is"),
    ("Hester", CI, "Loddon", "Hester lives in Loddon.",
     "Where does Hester live?", "No, that's not true, that was before she moved.",
     "no + that's not true + that was"),
    ("Ivo", E, "Marsden", "Ivo works at Marsden.",
     "Where does Ivo work?", "No, that's old news.",
     "no + that's (no denial phrase left: 252b reply to 'No.')"),
    ("Jessop", CI, "Pentire", "Jessop lives in Pentire.",
     "Where does Jessop live?", "nah, which was a while back",
     "nah + which was (no denial phrase left)"),
]):
    deny("pure_denial_that", [setup, q], turn, q, [[s, r, v]], [s, r, v],
         note + "; ctx")

# ---------------------------------------------------------------- other_tail_denial (4)
deny("other_tail_denial", ["Kitto works at Frome."],
     "Kitto doesn't work at Frome, sadly.", "Where does Kitto work?",
     [["Kitto", E, "Frome"]], ["Kitto", E, "Frome"], "other tail: sadly")
deny("other_tail_denial", ["Lowenna lives in Ruan."],
     "Lowenna doesn't live in Ruan anymore - she moved.",
     "Where does Lowenna live?", [["Lowenna", CI, "Ruan"]],
     ["Lowenna", CI, "Ruan"], "other tail: she moved")
deny("other_tail_denial", ["Mawgan's boss is Treloar."],
     "Treloar isn't Mawgan's boss, not anymore.", "Who is Mawgan's boss?",
     [["Mawgan", "boss", "Treloar"]], ["Mawgan", "boss", "Treloar"],
     "other tail: not anymore")
deny("other_tail_denial", ["Nonna speaks Elvic."],
     "Nonna does not speak Elvic lol", "What language does Nonna speak?",
     [["Nonna", L, "Elvic"]], ["Nonna", L, "Elvic"], "other tail: lol")

# ---------------------------------------------------------------- keep (12): expectations copied from 252b's run
KEEP = [
    (["Oriel lives in Pendle."], "Oriel works at Quantock, which is a bakery.",
     "Where does Oriel work?", "appositive teach, which is"),
    (["Piran works at Treen."], "Piran lives in Mullion, that's by the sea.",
     "Where does Piran live?", "teach + that's"),
    (["Rozenn lives in Arvor."], "Rozenn's boss is Kerne, which was a surprise.",
     "Who is Rozenn's boss?", "possessive teach + which was"),
    (["Senara works at Lelant."], "Thanks, that's helpful.",
     "Where does Senara work?", "chat thanks + that's"),
    (["Talan lives in Zennor."], "Good, this is going well.",
     "Where does Talan live?", "chat + this is"),
    (["Ulla works at Hayle."], "Where does Ulla work, that is the question.",
     "Where does Ulla work?", "wh question + that is (no ?)"),
    (["Veryan speaks Kernic."], "Veryan speaks Kernic, that is right.",
     "What language does Veryan speak?", "repeat teach + that is right"),
    (["Wenna lives in Porth."], "Okay, that's fine.",
     "Where does Wenna live?", "chat okay + that's fine"),
    (["Yestin works at Carne."], "Yestin's sister is Delen, that's her twin.",
     "Who is Yestin's sister?", "teach + that's"),
    (["Zennor lives in Bodmin."], "Hmm, that is interesting.",
     "Where does Zennor live?", "filler + that is"),
    (["Austell works at Lanner."], "Tell me about Austell, that would help.",
     "Where does Austell work?", "tell me + that (not an opener)"),
    (["Borlase lives in Gwithian."], "Borlase was born in Hendra, which is inland.",
     "Where was Borlase born?", "born teach + which is"),
]
for setup, turn, q, note in KEEP:
    add("keep", setup, turn, q, [], None, [], [], None,
        note + "; expectations = 252b byte-identical")

# ---------------------------------------------------------------- question_tail (8)
for setup, stated, turn, q, note in [
    (["Cador works at Polwin."], [["Cador", E, "Polwin"]],
     "Doesn't Cador work at Polwin, or is that outdated?",
     "Where does Cador work?", "negative question + or is that"),
    (["Demelza lives in Trura."], [["Demelza", CI, "Trura"]],
     "Demelza lives in Trura, is that still right?",
     "Where does Demelza live?", "statement + is that?"),
    (["Enys's boss is Polkin."], [["Enys", "boss", "Polkin"]],
     "Isn't Polkin Enys's boss, that's what you said?",
     "Who is Enys's boss?", "isn't question + that's ?"),
    (["Fenella speaks Lornic."], [["Fenella", L, "Lornic"]],
     "fenella doesnt speak lornic - thats outdated?",
     "What language does Fenella speak?", "lower typo statement shape + ?"),
    (["Gerens was born in Brea."], [["Gerens", PB, "Brea"]],
     "Wasn't Gerens born in Brea (that's what I heard)?",
     "Where was Gerens born?", "wasn't + bracket + ?"),
    (["Hedra works at Sennen."], [["Hedra", E, "Sennen"]],
     "Is it true that Hedra doesn't work at Sennen, that's old news",
     "Where does Hedra work?", "is it true lead, no ?"),
    (["Ives's manager is Colan."], [["Ives", "manager", "Colan"]],
     "So Ives's manager is not Colan anymore, which was last year?",
     "Who is Ives's manager?", "so + negated statement + ?"),
    (["Jago lives in Crantock."], [["Jago", CI, "Crantock"]],
     "Does Jago still live in Crantock, or is that outdated?",
     "Where does Jago live?", "does + or is that"),
]:
    add("question_tail", setup, turn, q, stated, stated[0], [], stated,
        stated[0][2], note)

# ---------------------------------------------------------------- unstored_tail (6)
for setup, stated, turn, q, note in [
    (["Kenwyn works at Truthall."], [["Kenwyn", E, "Truthall"]],
     "Kenwyn doesn't work at Godolphin, that's outdated.",
     "Where does Kenwyn work?", "known person, other value"),
    (["Lamorna lives in Paul."], [["Lamorna", CI, "Paul"]],
     "Merryn doesn't live in Paul, that was last year.",
     "Where does Lamorna live?", "unknown person, same value"),
    (["Madron's boss is Trewin."], [["Madron", "boss", "Trewin"]],
     "Pascoe isn't Madron's boss (that's old news).",
     "Who is Madron's boss?", "reversed, other value, bracket"),
    (["Nancarrow speaks Ruthic."], [["Nancarrow", L, "Ruthic"]],
     "nancarrow doesnt speak dornic, thats wrong",
     "What language does Nancarrow speak?", "lower typo other value"),
    (["Pendeen was born in Ludgvan."], [["Pendeen", PB, "Ludgvan"]],
     "Pendeen wasn't born in Towednack - which is a common mix-up.",
     "Where was Pendeen born?", "other value, dash which is"),
    (["Quintrell works at Kea."], [["Quintrell", E, "Kea"]],
     "Rosewarne doesn't work at Kea, this is a mistake.",
     "Where does Quintrell work?", "unknown person, this is"),
]:
    add("unstored_tail", setup, turn, q, stated, None, [], stated,
        stated[0][2], note)

# ---------------------------------------------------------------- control (8): no tail
deny("control", ["Sithney works at Breage."], "Sithney doesn't work at Breage.",
     "Where does Sithney work?", [["Sithney", E, "Breage"]],
     ["Sithney", E, "Breage"], "plain verb denial")
corr("control", ["Tregear lives in Mylor.", "Where does Tregear live?"],
     "No, it's Flushing.", "Where does Tregear live?",
     [["Tregear", CI, "Mylor"]], ["Tregear", CI, "Mylor"],
     ["Tregear", CI, "Flushing"], "ctx correction")
deny("control", ["Udy's boss is Pengelly.", "Who is Udy's boss?"],
     "That's wrong.", "Who is Udy's boss?", [["Udy", "boss", "Pengelly"]],
     ["Udy", "boss", "Pengelly"], "ctx denial")
corr("control", ["Veale speaks Ormic."],
     "Actually, Veale speaks Tamric, not Ormic.",
     "What language does Veale speak?", [["Veale", L, "Ormic"]],
     ["Veale", L, "Ormic"], ["Veale", L, "Tamric"], "explicit correction")
add("control", ["Warleggan lives in Luxulyan."], "Where does Warleggan live?",
    "Whose city is Luxulyan?", [["Warleggan", CI, "Luxulyan"]], None, [],
    [["Warleggan", CI, "Luxulyan"]], "Warleggan", "question")
add("control", ["Yeo works at Lostwithiel."], "Yeo lives in Fowey.",
    "Where does Yeo live?", [["Yeo", E, "Lostwithiel"]], None, [],
    [["Yeo", E, "Lostwithiel"], ["Yeo", CI, "Fowey"]], "Fowey", "teach")
deny("control", ["Zelah's manager is Probus."], "Probus isn't Zelah's manager.",
     "Who is Zelah's manager?", [["Zelah", "manager", "Probus"]],
     ["Zelah", "manager", "Probus"], "reversed possessive denial")
add("control", ["My name is Kitto Roskear."], "Actually, my name is Jowan.",
    "no", [], None, [], [], None, "user name confirm flow")

# ---------------------------------------------------------------- restart (5)
deny("restart", ["Arthek works at Probus Mill."],
     "Arthek doesn't work at Probus Mill, that's outdated.",
     "Where does Arthek work?", [["Arthek", E, "Probus Mill"]],
     ["Arthek", E, "Probus Mill"], "restart; that denial; reverse asks",
     restart=True,
     extra=[["Who works at Probus Mill?", "Arthek", None],
            ["Whose employer is Probus Mill?", "Arthek", None]])
deny("restart", ["Bosvenna lives in Carbis.", "Where does Bosvenna live?"],
     "That's wrong, that's old news.", "Where does Bosvenna live?",
     [["Bosvenna", CI, "Carbis"]], ["Bosvenna", CI, "Carbis"],
     "restart; pure denial + that", restart=True,
     extra=[["Who lives in Carbis?", "Bosvenna", None]])
corr("restart", ["Chynoweth's boss is Rodda.", "Who is Chynoweth's boss?"],
     "No, it's Hocking, that's outdated.", "Who is Chynoweth's boss?",
     [["Chynoweth", "boss", "Rodda"]], ["Chynoweth", "boss", "Rodda"],
     ["Chynoweth", "boss", "Hocking"], "restart; ctx correction + that",
     restart=True, extra=[["Who is Chynoweth's boss?", "Rodda", "Hocking"]])
corr("restart", ["Dellow speaks Morvic."],
     "Dellow doesn't speak Morvic, he speaks Tallic (that was school).",
     "What language does Dellow speak?", [["Dellow", L, "Morvic"]],
     ["Dellow", L, "Morvic"], ["Dellow", L, "Tallic"],
     "restart; explicit correction + bracket", restart=True,
     extra=[["What language does Dellow speak?", "Morvic", "Tallic"]])
deny("restart", ["Eddy's teacher is Jewell."],
     "Jewell is not Eddy's teacher; which was a long time ago.",
     "Who is Eddy's teacher?", [["Eddy", "teacher", "Jewell"]],
     ["Eddy", "teacher", "Jewell"], "restart; reversed + which was",
     restart=True, extra=[["Who is Eddy's teacher?", "Jewell", None]])


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    turns = set()
    lines = []
    for n, it in enumerate(ITEMS, 1):
        assert it["turn"] not in turns, it["turn"]
        turns.add(it["turn"])
        row = {"id": f"d258-{n:03d}"}
        row.update(it)
        lines.append(json.dumps(row, ensure_ascii=False))
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    fams = {}
    for it in ITEMS:
        fams[it["family"]] = fams.get(it["family"], 0) + 1
    print(len(ITEMS), fams)


if __name__ == "__main__":
    main()
