#!/usr/bin/env python3
"""Exp 241b unit tests: 241's tests unchanged plus the 241b tests at the
end (brief a-f, the confirm-match version, the caches).

Exp 241 unit tests: morphology, reader, parse-back, render, brake.

Run: python3 -B scripts/claude_mouth241b_test.py   (exit 0 = all pass)
Fictional names only.
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import claude_mouth241b_morph as M  # noqa: E402
import claude_mouth241b_reader as RD  # noqa: E402
import claude_mouth241b_parse as P  # noqa: E402
import claude_mouth241b_say as S  # noqa: E402
import claude_mouth241b_brake as B  # noqa: E402

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


# ---------------------------------------------------------------- 241b
def _fr(act, subj, path, **kw):
    role = "user" if subj == "USER" else "third"
    d = {"act": act, "subject": {"text": subj, "role": role}, "path": path,
         "notes": []}
    d.update(kw)
    return d


def _agent_render(fr, records=None):
    import claude_loop241b_agent as A
    return A.render_line(P.legacy(fr), records or [], [])


TAIL = "so I can only follow the chain this far."


@t
def b241_broken_chain_any_value_type():
    cases = [
        ("boss", "Ana Vell", "Mira Tonn's boss is Ana Vell. I have nothing "
         "saved about Ana Vell, " + TAIL),
        ("employer", "Krellwur Press", "Mira Tonn's employer is Krellwur "
         "Press. I have nothing saved about Krellwur Press, " + TAIL),
        ("age", "34", "Mira Tonn's age is 34. I have nothing saved about "
         "that, " + TAIL),
        ("date of birth", "4 March 1990", "Mira Tonn's date of birth is "
         "4 March 1990. I have nothing saved about that, " + TAIL),
        ("pet", "hamster", "Mira Tonn's pet is a hamster. I have nothing "
         "saved about that, " + TAIL),
    ]
    for rel, v, want in cases:
        r = _agent_render(_fr("BROKEN_CHAIN", "Mira Tonn", [rel],
                              values=[v]))
        eq(r["route"], "A")
        eq(r["text"], want)
        assert "someone" not in r["text"]
        # the frozen abstain anchor is kept, no clarify bit is added
        assert "i can only follow" in r["text"].lower()
        assert "don't know" not in r["text"].lower()


@t
def b241_conflict_value_rendering():
    cases = [
        ("godfather", "Tomas", "shethgean", "My notes say Mira's godfather "
         "is Tomas. Do you want me to change it to Shethgean?"),
        ("godfather", "Tomas", "van Dorn", "My notes say Mira's godfather "
         "is Tomas. Do you want me to change it to van Dorn?"),
        ("car", "red hatchback", "electric van", "My notes say Mira's car "
         "is a red hatchback. Do you want me to change it to an electric "
         "van?"),
        ("age", "6", "72", "My notes say Mira's age is 6. Do you want me to "
         "change it to 72?"),
        ("occupation", "baker", "umpire", "My notes say Mira is a baker. Do "
         "you want me to change it to an umpire?"),
        ("city", "Oslo", "bergen", "My notes say Mira lives in Oslo. Do you "
         "want me to change it to Bergen?"),
    ]
    for rel, old, new, want in cases:
        fr = _fr("CONFLICT", "Mira", [rel], old_value=old, new_value=new)
        r = _agent_render(fr)
        eq(r["route"], "A")
        eq(r["text"], want)
        eq(fr["new_value"], new)  # the stored value is never changed
        eq(r["frame"]["new_value"], new)
    fr = _fr("CONFLICT", "USER", ["instrument"], old_value="oboe",
             new_value="euphonium")
    eq(_agent_render(fr)["text"], "My notes say your instrument is the "
       "oboe. Do you want me to change it to the euphonium?")


@t
def b241_cap_name_rules():
    eq(S.cap_name("shethgean"), "Shethgean")
    eq(S.cap_name("van dorn"), "van dorn")       # particle exemption
    eq(S.cap_name("de la Vell"), "de la Vell")
    eq(S.cap_name("McKay"), "McKay")             # internal capitals kept
    eq(S.cap_name("Ana Vell"), "Ana Vell")


@t
def b241_agreement():
    r = _agent_render(_fr("FORGOTTEN_ONE", "Mira", ["favorite food"],
                          values=["noodles"]))
    eq(r["text"], "OK, I've forgotten that Mira's favorite food is noodles.")
    r = _agent_render(_fr("FORGOTTEN_ONE", "USER", ["notable work"],
                          values=["The Quiet Tide"]))
    eq(r["text"], "OK, I've forgotten that your notable work is The Quiet "
       "Tide.")
    fr = {"act": "REVERSE", "subject": {"text": "", "role": "third"},
          "path": ["favorite food"], "values": ["noodles"],
          "subjects": ["Mira Tonn"], "notes": []}
    r = _agent_render(fr)
    eq(r["route"], "A")
    eq(r["text"], "Noodles are the favorite food of Mira Tonn.")
    fr["values"] = ["economics"]
    fr["path"] = ["major"]
    eq(_agent_render(fr)["text"], "Economics is the major of Mira Tonn.")
    fr["values"] = ["Kell Books"]
    fr["path"] = ["employer"]
    eq(_agent_render(fr)["text"], "Kell Books is the employer of Mira Tonn.")
    rs = RD.readings("Noodles are the favorite food of Mira Tonn.")
    assert any(x["X"] == "Mira Tonn" and x["Y"] == "Noodles" for x in rs), rs


def _list_recs(fr):
    return [{"kind": "answer", "status": "OK",
             "relations": list(fr["path"]),
             "fields": {"multi": True,
                        "trail": list(range(len(fr["values"]))),
                        "answer": P._join_and(fr["values"])}}]


@t
def b241_repeated_items_said_once():
    fr = _fr("ANSWER_LIST", "Mira", ["hobby"], values=["rowing", "rowing"])
    eq(_agent_render(fr, _list_recs(fr))["text"], "Mira's hobby is rowing.")
    fr = _fr("ANSWER_LIST", "Mira", ["hobby"],
             values=["rowing", "chess", "rowing"])
    eq(_agent_render(fr, _list_recs(fr))["text"],
       "Mira's hobbies are rowing and chess.")
    fr = _fr("YESNO_NO", "Mira", ["hobby"], values=["rowing", "rowing"])
    eq(_agent_render(fr)["text"], "No, Mira's hobby is rowing.")
    fr = _fr("SAVED", "Mira", ["toy"], values=["kite"],
             also_have=["kite", "yo-yo", "yo-yo"])
    eq(_agent_render(fr)["text"],
       "Saved: Mira's toy is a kite. (I also have a yo-yo.)")


@t
def b241_self_people_you_word():
    # the base's 173 rewrite shows the user as 'you' in place: it is the
    # user, said 'you' and listed first (241 capitalised it mid-list)
    eq(render("I know 3 people: Orkdra, you, purkva.")[0],
       "I know three people: you, Orkdra and Purkva.")
    eq(render("I know 2 people: USER, Orkdra.")[0],
       "I know two people: you and Orkdra.")


@t
def b241_ambiguous():
    eq(S.ambiguous_names(["Mira Tonn (E0012)", "Mira Vell (E0450)"]),
       ["Mira Tonn", "Mira Vell"])
    eq(S.ambiguous_names(["Mira Tonn (E0012)", "mira tonn (E0450)"]), None)
    fr = {"act": "AMBIGUOUS", "subject": {"text": "Mira", "role": "third"},
          "path": [], "choices": ["Mira Tonn (E0012)", "Mira Vell (E0450)",
                                  "Mira Oss (E0007)"]}
    r = _agent_render(fr)
    eq(r["route"], "A")
    eq(r["text"], "I know more than one Mira: Mira Tonn, Mira Vell and Mira "
       "Oss. Which one do you mean?")
    fr["choices"] = ["Mira Tonn (E0012)", "Mira Tonn (E0450)"]
    leg = P.legacy(fr)
    r = _agent_render(fr)
    eq(r["route"], "passthrough")
    eq(r["text"], leg)
    import claude_loop241b_agent as A
    eq(r["why"], A.AMBIGUOUS_IDENTICAL)


@t
def b241_ambiguous_identical_counted_by_mixin():
    import claude_loop241b_agent as A

    class Base:
        def turn(self, text):
            return [text]

    class L(A.Mouth241bMixin, Base):
        pass

    fr = {"act": "AMBIGUOUS", "subject": {"text": "Mira", "role": "third"},
          "path": [], "choices": ["Mira Tonn (E0012)", "Mira Tonn (E0450)"]}
    lp = L()
    out = lp.turn(P.legacy(fr))
    eq(out, [P.legacy(fr)])
    eq(lp.mouth241b_stats["ambiguous_identical"], 1)
    eq(lp.mouth241b_stats["passthrough"], 1)


@t
def b241_confirm_match_version():
    import claude_confirm241b as C
    eq(C.norm_value("The  Euphonium"), "euphonium")
    assert C.confirm_match("the euphonium", "My instrument is euphonium.")
    assert C.confirm_match("Shethgean", "Mira's godfather is shethgean.")
    assert C.confirm_match("an electric van", "Mira's car is electric van.")
    assert not C.confirm_match("Bergen", "Mira lives in Oslo.")
    assert not C.confirm_match("", "anything")
    # verbatim values: same answer as the frozen `new_val in sent`
    for v, sent in [("Bergen", "Mira lives in Bergen."),
                    ("72", "Mira is 72."), ("Oslo", "Mira lives in Bergen.")]:
        eq(C.confirm_match(v, sent), v in sent)


@t
def b241_bounded_finders_match_regex():
    import random
    import re
    r = random.Random(5)
    alpha = "ab A.'-1 "
    for _ in range(20000):
        t = "".join(r.choice(alpha) for _ in range(r.randint(0, 14)))
        p = "".join(r.choice(alpha.strip()) for _ in range(r.randint(1, 3)))
        for ci in (False, True):
            rx = B._rx_bounded(p, re.I if ci else 0)
            eq(B._find_bounded(t, p, ci), rx.search(t) is not None)
        eq(B._slot_found(t, p), B._rx_slot(p).search(t) is not None)
        eq(B._sub_bounded_ci(t, p, "Q"),
           B._rx_bounded(p, re.I).sub("Q", t))


@t
def b241_shape_cache_equals_reader():
    """Every rule-7 answer through the caches equals the uncached reader
    on a set of statements that share shapes."""
    subs = ["Mira", "Ana Vell", "Kell Books", "Tomas", "Oslo", "Bergen",
            "Silas Wendt", "The Quiet Tide", "van Dorn"]
    tmpl = ["{X} lives in {Y}.", "{X}'s boss is {Y}.",
            "The city of {X} is {Y}.", "{Y} is the mother of {X}.",
            "{Y} owns {X}.", "{X}'s city is {Y}."]
    rels = ["city", "boss", "city", "mother", "owner", "city"]
    for tp, rel in zip(tmpl, rels):
        for x in subs:
            for y in subs:
                st = tp.format(X=x, Y=y)
                got = B.round_trip_cached(st, rel, x, y, None)
                want = RD.round_trip_ok(st, rel, x, y, None)
                eq(bool(got[0]), bool(want[0]))


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
