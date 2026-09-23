#!/usr/bin/env python3
"""make_panel.py: write blind yes/no panel 293 (85 items). Deterministic."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "panel.jsonl"

def item(i, family, setup, question, expect, gold, note):
    return {"id": f"y293-{i:03d}", "family": family, "setup": setup,
            "question": question, "expect": expect, "gold": gold, "note": note}

def build():
    items = []
    # have_true 10 (001-010) expect yes
    items.append(item(1, "have_true", ["Brenna's boss is Kira."], "Does Brenna have a boss?", "yes", ["Kira"], "have_true yes; boss taught"))
    items.append(item(2, "have_true", ["Calla's dentist is Tovi."], "Has Calla got a dentist?", "yes", ["Tovi"], "have_true yes; dentist taught"))
    items.append(item(3, "have_true", ["Doria's sister is Mara."], "Does Doria have a sister?", "yes", ["Mara"], "have_true yes; sister taught"))
    items.append(item(4, "have_true", ["Elvin's coach is Dara."], "Has Elvin got a coach?", "yes", ["Dara"], "have_true yes; coach taught"))
    items.append(item(5, "have_true", ["Farah's doctor is Sela."], "Does Farah have a doctor?", "yes", ["Sela"], "have_true yes; doctor taught"))
    items.append(item(6, "have_true", ["Galen's friend is Nia."], "Has Galen got a friend?", "yes", ["Nia"], "have_true yes; friend taught"))
    items.append(item(7, "have_true", ["Anna Lee's boss is Joren."], "Does Anna Lee have a boss?", "yes", ["Joren"], "have_true yes; two-word subject"))
    items.append(item(8, "have_true", ["Ivor's dentist is Mary Bell."], "Has Ivor got a dentist?", "yes", ["Mary Bell"], "have_true yes; two-word value"))
    items.append(item(9, "have_true", ["Jessa's coach is Bram."], "Does Jessa have a coach?", "yes", ["Bram"], "have_true yes; coach taught"))
    items.append(item(10, "have_true", ["Kellen's sister is Tilda."], "Has Kellen got a sister?", "yes", ["Tilda"], "have_true yes; sister taught"))
    # have_unknown 8 (011-018) expect unknown
    items.append(item(11, "have_unknown", ["Liora's city is Branford.", "Liora's employer is HaldenWorks."], "Does Liora have a dentist?", "unknown", [], "have_unknown; dentist never taught for Liora"))
    items.append(item(12, "have_unknown", ["Maren's sister is Willa.", "Maren's city is Kelmar."], "Has Maren got a boss?", "unknown", [], "have_unknown; boss never taught for Maren"))
    items.append(item(13, "have_unknown", ["Nessa's coach is Orvin.", "Nessa's doctor is Pella."], "Does Nessa have a sister?", "unknown", [], "have_unknown; sister never taught for Nessa"))
    items.append(item(14, "have_unknown", ["Orin's friend is Yelda.", "Orin's birthplace is Alderby."], "Has Orin got a coach?", "unknown", [], "have_unknown; coach never taught for Orin"))
    items.append(item(15, "have_unknown", ["Pella's boss is Caldor.", "Pella's city is Sorwell."], "Does Pella have a doctor?", "unknown", [], "have_unknown; doctor never taught for Pella"))
    items.append(item(16, "have_unknown", ["Sara Quinn's mother is Beth.", "Sara Quinn's city is Tarnwick."], "Does Sara Quinn have a dentist?", "unknown", [], "have_unknown; two-word subject; dentist never taught"))
    items.append(item(17, "have_unknown", ["Peter Lark's city is Lornell.", "Peter Lark's employer is Granite Hall."], "Does Peter Lark have a boss?", "unknown", [], "have_unknown; two-word subject; boss never taught"))
    items.append(item(18, "have_unknown", ["Sanna's dentist is Essik.", "Sanna's friend is Verin."], "Does Sanna have a coach?", "unknown", [], "have_unknown; coach never taught for Sanna"))
    # live 10 (019-028) 5 yes 5 no
    items.append(item(19, "live", ["Toren's city is Branford."], "Does Toren live in Branford?", "yes", ["Branford"], "live yes; asked city equals stored"))
    items.append(item(20, "live", ["Ulla's city is Kelmar."], "Does Ulla live in Kelmar?", "yes", ["Kelmar"], "live yes; asked city equals stored"))
    items.append(item(21, "live", ["Anna Lee's city is Sorwell."], "Does Anna Lee live in Sorwell?", "yes", ["Sorwell"], "live yes; two-word subject"))
    items.append(item(22, "live", ["Vessa's city is Tarnwick."], "Does Vessa live in Tarnwick?", "yes", ["Tarnwick"], "live yes; asked city equals stored"))
    items.append(item(23, "live", ["Nora Fields's city is Lornell."], "Does Nora Fields live in Lornell?", "yes", ["Lornell"], "live yes; two-word subject"))
    items.append(item(24, "live", ["Wrenna's city is Casford."], "Does Wrenna live in Dunmere?", "no", ["Casford"], "live no; asked city differs; gold is stored city"))
    items.append(item(25, "live", ["Xella's city is Dunmere."], "Does Xella live in Casford?", "no", ["Dunmere"], "live no; asked city differs; gold is stored city"))
    items.append(item(26, "live", ["Mary Bell's city is Vessaly."], "Does Mary Bell live in Morwick?", "no", ["Vessaly"], "live no; two-word subject; gold is stored city"))
    items.append(item(27, "live", ["Yorin's city is Morwick."], "Does Yorin live in Petrich?", "no", ["Morwick"], "live no; asked city differs; gold is stored city"))
    items.append(item(28, "live", ["Ellen Marsh's city is Petrich."], "Does Ellen Marsh live in Branford?", "no", ["Petrich"], "live no; two-word subject; gold is stored city"))
    # work 8 (029-036) 4 yes 4 no
    items.append(item(29, "work", ["Zella's employer is HaldenWorks."], "Does Zella work at HaldenWorks?", "yes", ["HaldenWorks"], "work yes; asked employer equals stored"))
    items.append(item(30, "work", ["Dalen's employer is Bracken Labs."], "Does Dalen work for Bracken Labs?", "yes", ["Bracken Labs"], "work yes; asked employer equals stored"))
    items.append(item(31, "work", ["David Crane's employer is Cinder Mill."], "Does David Crane work at Cinder Mill?", "yes", ["Cinder Mill"], "work yes; two-word subject"))
    items.append(item(32, "work", ["Simon Drake's employer is Dovetail Co."], "Does Simon Drake work for Dovetail Co?", "yes", ["Dovetail Co"], "work yes; two-word subject"))
    items.append(item(33, "work", ["Gilda's employer is Elm Court Press."], "Does Gilda work at Foxglove Farm?", "no", ["Elm Court Press"], "work no; asked differs; gold is stored employer"))
    items.append(item(34, "work", ["Harlo's employer is Foxglove Farm."], "Does Harlo work for Granite Hall?", "no", ["Foxglove Farm"], "work no; asked differs; gold is stored employer"))
    items.append(item(35, "work", ["Laura Heath's employer is Granite Hall."], "Does Laura Heath work at Harborlight Books?", "no", ["Granite Hall"], "work no; two-word subject; gold is stored employer"))
    items.append(item(36, "work", ["Efra's employer is Ironbark Studio."], "Does Efra work for Juniper Works?", "no", ["Ironbark Studio"], "work no; asked differs; gold is stored employer"))
    # born 6 (037-042) 3 yes 3 no
    items.append(item(37, "born", ["Ilda's birthplace is Alderby."], "Does Ilda come from Alderby?", "yes", ["Alderby"], "born yes; asked place equals stored"))
    items.append(item(38, "born", ["Joren's birthplace is Brimwell."], "Was Joren born in Brimwell?", "yes", ["Brimwell"], "born yes; asked place equals stored"))
    items.append(item(39, "born", ["Clara Bloom's birthplace is Calside."], "Does Clara Bloom come from Calside?", "yes", ["Calside"], "born yes; two-word subject"))
    items.append(item(40, "born", ["Kessa's birthplace is Dunhollow."], "Does Kessa come from Elmwick?", "no", ["Dunhollow"], "born no; asked differs; gold is stored place"))
    items.append(item(41, "born", ["Lonan's birthplace is Elmwick."], "Was Lonan born in Farnell?", "no", ["Elmwick"], "born no; asked differs; gold is stored place"))
    items.append(item(42, "born", ["Henry Frost's birthplace is Farnell."], "Was Henry Frost born in Gorsefield?", "no", ["Farnell"], "born no; two-word subject; gold is stored place"))
    # is_multiword 8 (043-050) 4 yes 4 no
    items.append(item(43, "is_multiword", ["Megan Stone's boss is Kira."], "Is Megan Stone's boss Kira?", "yes", ["Kira"], "is_multiword yes; boss; two-word subject"))
    items.append(item(44, "is_multiword", ["Liora's mother is Olga Pierce."], "Is Olga Pierce Liora's mother?", "yes", ["Olga Pierce"], "is_multiword yes; mother; two-word value"))
    items.append(item(45, "is_multiword", ["Victor Hale's father is Joren."], "Is Victor Hale's father Joren?", "yes", ["Joren"], "is_multiword yes; father; two-word subject"))
    items.append(item(46, "is_multiword", ["Wendy Brooks's city is Branford."], "Is Wendy Brooks's city Branford?", "yes", ["Branford"], "is_multiword yes; city; two-word subject"))
    items.append(item(47, "is_multiword", ["Aaron Cliff's dentist is Tovi."], "Is Aaron Cliff's dentist Essik?", "no", ["Tovi"], "is_multiword no; dentist; two-word subject; gold is stored value"))
    items.append(item(48, "is_multiword", ["Calla's coach is Dara."], "Is Betty Wayne Calla's coach?", "no", ["Dara"], "is_multiword no; coach; two-word asked value; gold is stored value"))
    items.append(item(49, "is_multiword", ["Nora Fields's employer is HaldenWorks."], "Is Nora Fields's employer Bracken Labs?", "no", ["HaldenWorks"], "is_multiword no; employer; two-word subject; gold is stored value"))
    items.append(item(50, "is_multiword", ["Tara Moon's birthplace is Alderby."], "Is Tara Moon's birthplace Brimwell?", "no", ["Alderby"], "is_multiword no; birthplace; two-word subject; gold is stored value"))
    # is_of_form 6 (051-056) 3 yes 3 no
    items.append(item(51, "is_of_form", ["Ralla's boss is Kira."], "Is Kira the boss of Ralla?", "yes", ["Kira"], "is_of_form yes; asked value equals stored"))
    items.append(item(52, "is_of_form", ["Selda's mother is Wren."], "Is Wren the mother of Selda?", "yes", ["Wren"], "is_of_form yes; asked value equals stored"))
    items.append(item(53, "is_of_form", ["Paul Rivers's city is Branford."], "Is Branford the city of Paul Rivers?", "yes", ["Branford"], "is_of_form yes; two-word subject"))
    items.append(item(54, "is_of_form", ["Tilda's dentist is Tovi."], "Is Essik the dentist of Tilda?", "no", ["Tovi"], "is_of_form no; asked differs; gold is stored value"))
    items.append(item(55, "is_of_form", ["Ulma's coach is Dara."], "Is Bram the coach of Ulma?", "no", ["Dara"], "is_of_form no; asked differs; gold is stored value"))
    items.append(item(56, "is_of_form", ["Ruby Lane's father is Joren."], "Is Caldor the father of Ruby Lane?", "no", ["Joren"], "is_of_form no; two-word subject; gold is stored value"))
    # taken_back 6 (057-062)
    items.append(item(57, "taken_back", ["Verin's boss is Kira.", "Verin's boss isn't Kira."], "Is Kira Verin's boss?", "unknown", [], "taken_back denial removes fact; expect unknown"))
    items.append(item(58, "taken_back", ["Willa's city is Branford.", "Willa's city isn't Branford."], "Does Willa live in Branford?", "unknown", [], "taken_back denial removes fact; expect unknown"))
    items.append(item(59, "taken_back", ["Yelda's dentist is Tovi.", "Yelda's dentist isn't Tovi."], "Is Tovi Yelda's dentist?", "unknown", [], "taken_back denial removes fact; expect unknown"))
    items.append(item(60, "taken_back", ["Zoren's boss is Kira.", "No, Zoren's boss is Mara."], "Is Mara Zoren's boss?", "yes", ["Mara"], "taken_back correction to Mara; expect yes by new value"))
    items.append(item(61, "taken_back", ["Caldor's city is Branford.", "No, Caldor's city is Kelmar."], "Is Branford Caldor's city?", "no", ["Kelmar"], "taken_back correction to Kelmar; old value asked; expect no"))
    items.append(item(62, "taken_back", ["Dremma's employer is HaldenWorks.", "Actually, Dremma's employer is Bracken Labs."], "Does Dremma work for Bracken Labs?", "yes", ["Bracken Labs"], "taken_back correction to new employer; expect yes"))
    # is_single_control 8 (063-070) expect control
    items.append(item(63, "is_single_control", ["Fennor's boss is Kira."], "Is Fennor's boss Kira?", "control", [], "is_single_control; one-word names; base answers"))
    items.append(item(64, "is_single_control", ["Gremma's mother is Wren."], "Is Wren Gremma's mother?", "control", [], "is_single_control; one-word names; base answers"))
    items.append(item(65, "is_single_control", ["Harlo's father is Joren."], "Is Harlo's father Caldor?", "control", [], "is_single_control; one-word names; base answers"))
    items.append(item(66, "is_single_control", ["Ilda's city is Branford."], "Is Branford Ilda's city?", "control", [], "is_single_control; one-word names; base answers"))
    items.append(item(67, "is_single_control", ["Jessa's employer is HaldenWorks."], "Is Jessa's employer Bracken Labs?", "control", [], "is_single_control; one-word names; base answers"))
    items.append(item(68, "is_single_control", ["Kessa's birthplace is Alderby."], "Is Kessa's birthplace Alderby?", "control", [], "is_single_control; one-word names; base answers"))
    items.append(item(69, "is_single_control", ["Lonan's dentist is Tovi."], "Is Essik Lonan's dentist?", "control", [], "is_single_control; one-word names; base answers"))
    items.append(item(70, "is_single_control", ["Milda's coach is Dara."], "Is Dara Milda's coach?", "control", [], "is_single_control; one-word names; base answers"))
    # wh_control 8 (071-078) expect control
    items.append(item(71, "wh_control", ["Noren's boss is Kira."], "Who is Noren's boss?", "control", [], "wh_control; plain who question"))
    items.append(item(72, "wh_control", ["Ossa's city is Kelmar."], "Where does Ossa live?", "control", [], "wh_control; plain where question"))
    items.append(item(73, "wh_control", ["Perin's employer is Cinder Mill."], "Who is Perin's employer?", "control", [], "wh_control; plain who question"))
    items.append(item(74, "wh_control", ["Ralla's birthplace is Calside."], "Where was Ralla born?", "control", [], "wh_control; plain where question"))
    items.append(item(75, "wh_control", ["Selda's dentist is Tovi."], "Who is Selda's dentist?", "control", [], "wh_control; plain who question"))
    items.append(item(76, "wh_control", ["Tilda's coach is Bram."], "Who is Tilda's coach?", "control", [], "wh_control; plain who question"))
    items.append(item(77, "wh_control", ["Olga Pierce's boss is Kira."], "Who is Olga Pierce's boss?", "control", [], "wh_control; two-word subject"))
    items.append(item(78, "wh_control", ["Betty Wayne's city is Dunmere."], "Where does Betty Wayne live?", "control", [], "wh_control; two-word subject"))
    # statement_control 7 (079-085) expect control
    items.append(item(79, "statement_control", ["Ulma's boss is Kira."], "Ulma does love hiking.", "control", [], "statement_control; does-statement not stored"))
    items.append(item(80, "statement_control", ["Verin's dentist is Essik."], "Mira does love the rain.", "control", [], "statement_control; does-statement not stored"))
    items.append(item(81, "statement_control", ["Willa's coach is Orvin."], "Tomas has left the room.", "control", [], "statement_control; has-statement not stored"))
    items.append(item(82, "statement_control", ["Xella's friend is Yelda."], "Ana is happy today.", "control", [], "statement_control; is-statement not stored"))
    items.append(item(83, "statement_control", ["Yorin's city is Sorwell."], "Sanna has quickly packed her case.", "control", [], "statement_control; has-statement not stored"))
    items.append(item(84, "statement_control", ["Zella's employer is Ironbark Studio."], "Orin is kindly helping today.", "control", [], "statement_control; is-statement not stored"))
    items.append(item(85, "statement_control", ["Caldor's birthplace is Gorsefield."], "Pella does truly enjoy songs.", "control", [], "statement_control; does-statement not stored"))
    return items

def main():
    items = build()
    assert len(items) == 85, len(items)
    OUT.write_text("".join(json.dumps(it, ensure_ascii=False) + "\n" for it in items), encoding="utf-8")
    print(f"wrote {OUT} ({len(items)} items)")

if __name__ == "__main__":
    main()
