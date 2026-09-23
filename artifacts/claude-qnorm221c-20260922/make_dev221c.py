#!/usr/bin/env python3
"""Writes dev221c.jsonl (221c dev cases, written from scratch; fictional names)."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "dev221c.jsonl"
rows = []


def add(fam, setup, q, gold, expect="rewrite"):
    rows.append({"id": f"d221c-{len(rows) + 1:03d}", "family": fam,
                 "setup": setup, "question": q, "gold": gold,
                 "expect": expect})


# --- contractions
add("contraction", ["Tamsin Orle's birthday is March 4."], "When's Tamsin Orle's birthday?", "March 4")
add("contraction", ["My boss is Pell Varrin."], "Who's my manager?", "Pell Varrin")
add("contraction", ["My mom is Sora Quill."], "Who's my mom?", "Sora Quill")
add("contraction", ["Dace Morrow's sister is Lune Morrow."], "Who's Dace Morrow's sister?", "Lune Morrow")
add("contraction", ["Kell Aubin's hometown is Farrowby."], "Where's Kell Aubin from?", "Farrowby")
add("contraction", ["Ossie Brandt's employer is Quillmark."], "Who's Ossie Brandt's employer?", "Quillmark")
add("contraction", ["Merit Vale's favorite color is teal."], "WHAT'S Merit Vale's favorite color?", "teal")
add("contraction", ["Juno Palk's birthday is May 2."], "When’s Juno Palk's birthday?", "May 2")
add("contraction", ["Rook Tanner's friend is Ely Moss.", "Rook Tanner's friend is Cato Wirth."], "Who're Rook Tanner's friends?", "Ely Moss; Cato Wirth")
add("contraction", ["Anselm Ruck's boss is Heda Crane."], "Who's the boss of Anselm Ruck?", "Heda Crane")
add("contraction", [], "When's Brisa Tolland's birthday?", "abstain")
add("contraction", ["Hester Lamb's best friend is Nim Oakes."], "Who's Hester Lamb's best friend?", "Nim Oakes")
# --- trailing fillers
add("filler", ["My birthday is June 9."], "When is my birthday again?", "June 9")
add("filler", ["Pell Ardent's boss is Vira Lusk."], "Who is Pell Ardent's boss now?", "Vira Lusk")
add("filler", ["Tove Harker's city is Glimmerton."], "Where does Tove Harker live, then?", "Glimmerton")
add("filler", ["Quade Ferris's job is baker."], "What is Quade Ferris's job exactly?", "baker")
add("filler", ["Ilse Brant's sister is Mora Brant."], "Who is Ilse Brant's sister, please?", "Mora Brant")
add("filler", ["Yara Holm's wife is Tessa Holm."], "Who is Yara Holm's wife, by the way?", "Tessa Holm")
add("filler", ["Corin Pask's employer is Bellweather."], "Where does Corin Pask work, anyway?", "Bellweather")
add("filler", ["My dad is Orrin Vell."], "Who is my dad again please?", "Orrin Vell")
add("filler", ["Lissa Crowe's coach is Barden Hale."], "Who is the coach of Lissa Crowe again?", "Barden Hale")
add("filler", [], "Who is Fenna Roath's boss again?", "abstain")
add("filler", ["Sol Imber's pet is a ferret named Pip."], "Who is Sol Imber's teacher now?", "abstain")
# --- leading fillers
add("lead", ["Garrick Onn's boss is Rhea Dunmore."], "So, who is Garrick Onn's boss?", "Rhea Dunmore")
add("lead", ["My sister is Wynne Marsh."], "um, who is my sister?", "Wynne Marsh")
add("lead", ["Petra Lusk's birthday is April 20."], "Hey, when's Petra Lusk's birthday?", "April 20")
# --- missing question mark
add("missing_q", ["Hollis Brae's boss is Nerys Fold."], "Who is Hollis Brae's boss", "Nerys Fold")
add("missing_q", ["Ansel Trow's city is Kestrelby."], "Where does Ansel Trow live", "Kestrelby")
add("missing_q", ["My mom is Delphine Ashe."], "who is my mom", "Delphine Ashe")
add("missing_q", ["Brin Coyle's birthday is July 7."], "when's Brin Coyle's birthday", "July 7")
# --- spaces and case
add("spaces_case", ["Emmet Swale's boss is Ronja Pike."], "who   is  Emmet Swale's boss?", "Ronja Pike")
add("spaces_case", ["Isolde Wray's teacher is Magnus Tolle."], "WHO IS Isolde Wray's teacher again?", "Magnus Tolle")
add("spaces_case", ["Caspar Neale's birthday is October 30."], "  When's   Caspar Neale's birthday  ?", "October 30")
# --- plural relation nouns (multi-valued)
add("plural", ["Garrow Blythe's friend is Ines Marl.", "Garrow Blythe's friend is Tobin Rusk."], "Who are Garrow Blythe's friends?", "Ines Marl; Tobin Rusk")
add("plural", ["Wren Castel's hobby is knitting."], "What are Wren Castel's hobbies?", "knitting")
add("plural", ["My cousin is Arlo Venn.", "My cousin is Bea Venn."], "Who are my cousins?", "Arlo Venn; Bea Venn")
add("plural", ["Mirela Strand's sister is Ona Strand.", "Mirela Strand's sister is Pia Strand."], "Who are Mirela Strand's sisters?", "Ona Strand; Pia Strand")
add("plural", ["Doran Kest's child is Lio Kest.", "Doran Kest's child is Mae Kest."], "Who are Doran Kest's children?", "Lio Kest; Mae Kest")
add("plural", ["Tilde Marr's neighbour is Hob Crane."], "Who are the neighbours of Tilde Marr?", "Hob Crane")
add("plural", ["Wick Sallow's colleague is Pen Arden.", "Wick Sallow's colleague is Rue Tamsin."], "Who are Wick Sallow's colleagues again?", "Pen Arden; Rue Tamsin")
add("plural", ["Nessa Brook's friend is Olan Drew."], "Who are Nessa Brook's friends?", "Olan Drew")
add("plural", [], "Who are Kaspar Imrie's friends?", "abstain")
add("plural", ["Faye Lorne's brother is Tam Lorne.", "Faye Lorne's brother is Ewan Lorne."], "Who're Faye Lorne's brothers?", "Tam Lorne; Ewan Lorne")
add("plural", ["My friend is Idris Pole.", "My friend is Juna Pole."], "who are my friends", "Idris Pole; Juna Pole")
# --- statements (never rewritten; reply + store must equal 221 byte for byte)
for s in ["So, Tarn Ivey's boss is Mel Orkin.", "Tarn Ivey's boss is Mel Orkin now.",
          "What a lovely garden Tarn Ivey has.", "Who knows.",
          "My friends are Ada Rill and Bo Rill.", "Hey, my birthday is August 3.",
          "Kip Ember's friend is Lark Sorrel, by the way.", "When Kip Ember visits, he brings bread.",
          "Where Kip Ember lives is Brackwater.", "Kip Ember's hobby is sailing again."]:
    add("statement", ["Tarn Ivey's sister is Nell Ivey."], s, "statement", expect="none")
# --- controls: question-shaped turns that must NOT be rewritten
add("control", ["Rafe Colby's boss is Anna Pym."], "Who is Rafe Colby's boss?", "Anna Pym", expect="none")
add("control", ["Rafe Colby's boss is Anna Pym."], "Who composed Right Now?", "abstain", expect="none")
add("control", ["Rafe Colby's boss is Anna Pym."], "Who are Rafe Colby's bosses?", "abstain", expect="none")
add("control", ["Rafe Colby's boss is Anna Pym."], "What's your name?", "self", expect="none")
add("control", ["Rafe Colby's boss is Anna Pym."], "How's it going?", "self", expect="none")
add("control", ["Rafe Colby's boss is Anna Pym."], "Is Rafe Colby's boss Anna Pym?", "yes", expect="none")

OUT.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
print(f"wrote {len(rows)} rows to {OUT}")
