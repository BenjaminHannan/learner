#!/usr/bin/env python3
"""Exp 241 unit tests: morphology, reader, parse-back, render, brake.

Run: python3 -B scripts/claude_mouth241_test.py   (exit 0 = all pass)
Fictional names only.
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_mouth241_morph as M  # noqa: E402
import claude_mouth241_reader as RD  # noqa: E402
import claude_mouth241_parse as P  # noqa: E402
import claude_mouth241_say as S  # noqa: E402
import claude_mouth241_brake as B  # noqa: E402

TESTS = []


def t(fn):
    TESTS.append(fn)
    return fn


def eq(a, b):
    assert a == b, f"{a!r} != {b!r}"


def render(line, records=None, names=()):
    """Parse + render + brake, same path as the agent (no agent import)."""
    fr = P.parse(line, records)
    if fr is None:
        return line, "passthrough"
    if fr.get("path") and fr["act"] not in ("UNKNOWN_ENTITY", "AMBIGUOUS"):
        row = S.row_for(fr["path"][-1])
        if row is None:
            return line, "passthrough"
        fr["_row"] = row
    pre = P.NOTE_DROPPED * len(fr.get("notes") or [])
    for c in S.candidates(fr):
        ok, _ = B.check(fr, c, names, legacy=line[len(pre):])
        if ok:
            return pre + c, "A"
    return line, "legacy"


# ---------------------------------------------------------------- morph
@t
def morph_articles():
    eq(M.with_article("baker"), "a baker")
    eq(M.with_article("engineer"), "an engineer")
    eq(M.with_article("hour"), "an hour")
    eq(M.with_article("university"), "a university")
    eq(M.with_article("honest judge"), "an honest judge")


@t
def morph_lists():
    eq(M.join_list([]), "")
    eq(M.join_list(["Odo"]), "Odo")
    eq(M.join_list(["Odo", "Ivy"]), "Odo and Ivy")
    eq(M.join_list(["Odo", "Ivy", "Ash"]), "Odo, Ivy and Ash")


@t
def morph_counts():
    eq(M.num_text(0), "zero")
    eq(M.num_text(7), "seven")
    eq(M.num_text(12), "12")
    eq(M.count_phrase(1, "person", "people"), "one person")
    eq(M.count_phrase(3, "person", "people"), "three people")
    eq(M.count_phrase(1, "fact"), "one fact")
    eq(M.count_phrase(14, "fact"), "14 facts")
    eq(M.times_phrase(1), "once")


@t
def morph_possessive_plural():
    eq(M.possessive("Mira"), "Mira's")
    eq(M.possessive("Silas"), "Silas's")
    assert M.ends_sxz("Felix") and M.ends_sxz("Juniper Lane Books")
    assert not M.ends_sxz("Mira")
    eq(M.plural("sister"), "sisters")
    eq(M.plural("city"), "cities")
    eq(M.plural("child"), "children")


@t
def morph_finish():
    eq(M.finish("hello there"), "Hello there.")
    eq(M.finish("It is in Washington, D.C.."), "It is in Washington, D.C.")


# ---------------------------------------------------------------- reader
@t
def reader_round_trip():
    ok, why = RD.round_trip_ok("Mira lives in Oslo.", "city", "Mira", "Oslo")
    assert ok, why
    ok, why = RD.round_trip_ok("Silas Wendt owns Juniper Lane Books.",
                               "owner", "Juniper Lane Books", "Silas Wendt")
    assert ok, why
    ok, _ = RD.round_trip_ok("Juniper Lane Books owns Silas Wendt.",
                             "owner", "Juniper Lane Books", "Silas Wendt")
    assert not ok, "reversed owner must fail the round trip"
    ok, why = RD.round_trip_ok("you live in Lima.", "city", RD.USER, "Lima")
    assert ok, why


# ---------------------------------------------------------------- parse
@t
def parse_lossless():
    lines = [
        "Saved: Mira's city is Oslo.",
        "I have Mira's city as Oslo. Do you want me to change it to Bergen?",
        "Forgotten: Mira's city.",
        "Forgotten: Kai's sister Ula.",
        "I don't have Kai's sister Zed.",
        "I don't know Mira's mother.",
        "I don't know your city yet.",
        "I don't know anyone called Zed.",
        "Yes, Wren's friend is Odo.",
        "No, Wren's friend is Odo, Ivy and Ash.",
        "Not that I know of. I have Odo and Ivy as Wren's friend.",
        "Silas's mother is Ana.",
        "I know 2 people: Max, Silas.",
        "I know 1 people: USER.",
        "We have had 4 turns.",
        "(I dropped my earlier question.) Saved: Jon's job is baker.",
    ]
    for ln in lines:
        fr = P.parse(ln)
        assert fr is not None, ln
        eq(P.legacy(fr), ln)
    assert P.parse("Hello! How can I help?") is None


@t
def parse_self_people_user():
    fr = P.parse("I know 1 people: USER.")
    eq(fr["act"], "SELF_PEOPLE")
    eq(fr["count"], 1)
    eq(fr["names"], ["USER"])


# ---------------------------------------------------------------- render
@t
def render_director_case():
    # director input 2026-09-22: count agreement + USER -> "you"
    eq(render("I know 1 people: USER.")[0], "I know one person: you.")
    eq(render("I know 3 people: Max, USER, Silas.")[0],
       "I know three people: you, Max and Silas.")
    eq(render("I know 0 people: .")[0], "You haven't told me about anyone yet.")


@t
def render_acts():
    cases = {
        "Saved: Mira's city is Oslo.": "Saved: Mira lives in Oslo.",
        "Forgotten: Mira's city.": "OK, I've forgotten where Mira lives.",
        "Silas's mother is Ana.": "The mother of Silas is Ana.",
        "Saved: Jon's job is baker.": "Saved: Jon is a baker.",
        "Saved: Juniper Lane Books's owner is Silas Wendt.":
            "Saved: Silas Wendt owns Juniper Lane Books.",
        "I have Mira's city as Oslo. Do you want me to change it to Bergen?":
            "My notes say Mira lives in Oslo. Do you want me to change it "
            "to Bergen?",
        "I don't know your city yet.": "I don't know where you live yet.",
    }
    for src, want in cases.items():
        got, route = render(src)
        eq(route, "A")
        eq(got, want)


@t
def render_list_needs_record():
    rec = [{"kind": "answer", "status": "OK", "relations": ["friend"],
            "fields": {"multi": True, "trail": [1, 2, 3],
                       "answer": "Odo, Ivy and Ash"}}]
    eq(render("Wren's friend is Odo, Ivy and Ash.", rec)[0],
       "Wren's friends are Odo, Ivy and Ash.")


@t
def render_unknown_entity_verbatim():
    got, _ = render("I don't know anyone called my sister.")
    eq(got, "I don't know anyone called my sister.")


@t
def render_note_prefix_kept():
    got, route = render("(I dropped my earlier question.) Saved: Mira's city "
                        "is Oslo.")
    eq(route, "A")
    eq(got, "(I dropped my earlier question.) Saved: Mira lives in Oslo.")


# ---------------------------------------------------------------- brake
@t
def brake_blocks_bad_text():
    fr = P.parse("Saved: Mira's city is Oslo.")
    fr["_row"] = S.row_for("city")
    leg = "Saved: Mira's city is Oslo."
    ok, _ = B.check(fr, "Saved: Mira lives in Oslo.", (), legacy=leg)
    assert ok
    for bad in ("Saved: Mira lives in Bergen.",       # wrong value
                "Saved: Oslo lives in Mira.",          # reversed
                "Mira probably lives in Oslo.",        # banned hedge
                "Saved: Mira and Ivo live in Oslo."):  # invented name
        ok, _ = B.check(fr, bad, ("Ivo",), legacy=leg)
        assert not ok, bad


@t
def brake_numbers():
    fr = P.parse("We have had 4 turns.")
    ok, _ = B.check(fr, "We have had four turns.", (), legacy="We have had 4 turns.")
    assert ok
    ok, _ = B.check(fr, "We have had five turns.", (), legacy="We have had 4 turns.")
    assert not ok


@t
def render_the_names():
    # 238 class MISSING_ARTICLE_THE (closed list of 'the' names)
    eq(render("Netherlands's capital is Amsterdam.")[0],
       "The capital of the Netherlands is Amsterdam.")
    eq(render("Saved: Tom's city is United States.")[0],
       "Saved: Tom lives in the United States.")


@t
def render_abbreviations_and_initials():
    # periods inside names are not sentence ends; 'you' inside a title
    # is not the user
    cases = {
        "Saved: iPhoto's developer is Apple Inc..":
            "Saved: Apple Inc. developed iPhoto.",
        "I have Tom's city as Washington, D.C.. Do you want me to change "
        "it to Oslo?": "My notes say Tom lives in Washington, D.C. Do you "
                       "want me to change it to Oslo?",
        "Saved: Harry Potter's author is J. K. Rowling.":
            "Saved: J. K. Rowling wrote Harry Potter.",
        "Saved: Within You Without You's performer is The Beatles.":
            "Saved: The Beatles performed Within You Without You.",
    }
    for src, want in cases.items():
        got, route = render(src)
        eq(route, "A")
        eq(got, want)
    eq(M.finish("it is Visual Basic .NET"), "It is Visual Basic .NET.")


@t
def render_count_noun_values_and_plural_names():
    eq(render("Saved: Mira's pet is hamster.")[0],
       "Saved: Mira's pet is a hamster.")
    eq(render("Yes, Mira's instrument is cello.")[0],
       "Yes, Mira's instrument is the cello.")
    eq(render("Saved: Juniper Lane Books's owner is Silas Wendt.")[0],
       "Saved: Silas Wendt owns Juniper Lane Books.")
    eq(render("Juniper Lane Books's city is Oslo.")[0],
       "The city of Juniper Lane Books is Oslo.")
    eq(render("Yes, Jon's occupation is herbalist.")[0],
       "Yes, Jon is an herbalist.")


def main() -> int:
    fails = 0
    for fn in TESTS:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception:  # noqa: BLE001
            fails += 1
            print(f"FAIL {fn.__name__}")
            traceback.print_exc()
    print(f"{len(TESTS) - fails}/{len(TESTS)} passed")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
