#!/usr/bin/env python3
"""Exp 255b M1 generator: fixedtext.jsonl for the two blind grammar graders.

- Every CHANGED template with slots (T30-T60 pattern rules) is rendered 5
  times: an old 138m-shaped line is built with fresh fictional fillers
  drawn from the sealed seed and passed through the real
  claude_fix255b_text.rewrite255b (the id it returns must be the template's).
  A slot template whose new text cannot vary (T54, T59) and every
  fixed-string template (T01-T29) has exactly one possible text, so it is
  rendered ONCE (five copies would be identical; deviation reported).
- Every UNCHANGED swept template (U01-...) is rendered once with fillers.
Output rows: {"id", "template_id", "text"}; order shuffled by the seed.

usage: claude_255b_m1gen.py <out.jsonl>
"""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import claude_fix255_text as T255  # noqa: E402 (old-form structure, read-only)
import claude_fix255b_text as T  # noqa: E402 (the rewriter under test)

SEED = 2550923  # sealed with PASSMARKS; never changed after the seal

# fictional fillers only
PEOPLE = ["Brannoc", "Liesl", "Oriane", "Tavik", "Maelis", "Corvane",
          "Isbet", "Dorwin", "Pellam", "Quilla", "Rennick", "Sabeth",
          "Talwyn", "Ulla", "Venn", "Wistan", "Ysolt", "Zarek", "Ammet",
          "Fenwyn", "Galen Thorne", "Mirelle Quast", "Odo", "Hesk"]
PLACES = ["Brell", "Varn", "Keldmoor", "Ostwick", "Fallowmere",
          "Quellmouth", "Dunmarrow", "Lisk", "Tarnholt", "Ember Cross"]
JOBS = ["fisher", "baker", "carpenter", "potter", "weaver", "ferrier"]
PERSON_RELS = ["boss", "sister", "friend", "mother", "brother", "teacher"]
PHRASES = ["hello", "good night", "I am the queen of Varn",
           "we sail at dawn", "Brannoc is my hero", "my name",
           "the moon is made of cheese", "hello there", "three cheers",
           "Liesl wins"]


class G:
    def __init__(self, rng):
        self.r = rng
        self.used: set[str] = set()

    def reset(self):
        """Called before every render: no name repeats inside one text."""
        self.used = set()

    def p(self):
        name = self.r.choice([x for x in PEOPLE if x not in self.used])
        self.used.add(name)
        return name

    def fact(self, allow_user=True):
        r = self.r
        subj = "USER" if allow_user and r.random() < 0.35 else self.p()
        kind = r.random()
        if kind < 0.4:
            rel, val = r.choice(PERSON_RELS), self.p()
        elif kind < 0.7:
            rel, val = "city", r.choice(PLACES)
        else:
            rel, val = "job", r.choice(JOBS)
        return subj, rel, val

    def fs(self, allow_user=True):
        s, rel, v = self.fact(allow_user)
        return f"{s}'s {rel} is {v}"

    def n(self, lo=0, hi=9):
        return self.r.randint(lo, hi)

    def turn(self):
        return str(self.n(1, 30)) if self.r.random() < 0.6 else "?"


def old_forms(g: G) -> dict:
    r = g.r
    modes = sorted(T255.MODE_NEW)
    return {
        "T30_MODE": lambda: (f"Right now I am back in {r.choice(modes)} mode,"
                             f" waiting for your next turn."),
        "T31_SAYECHO": lambda: (r.choice(PHRASES)
                                + r.choice([". ", " "])
                                + "(I'm treating that as pretend, so I "
                                  "won't save it.)"),
        "T32_FIRST": lambda: f"The first thing you taught me was: {g.fs()}.",
        "T33_LAST": lambda: (f"The last thing you taught me was: {g.fs()}, "
                             f"in turn {g.turn()}."),
        "T34_FORGOT": lambda: ("I forgot: " + "; ".join(
            g.fs() for _ in range(r.choice([1, 1, 2]))) +
            f". You asked me to forget it in turn {g.turn()}. The old row is "
            "kept but retired."),
        "T35_CORRECTED": lambda: "You corrected: " + "; ".join(
            (lambda s3: f"{r.choice(['USER', s3[0]])}'s "
             f"{r.choice(PERSON_RELS)} from {s3[1]} to {s3[2]}")(
                 r.sample(PEOPLE, 3)) for _ in range(r.choice([1, 1, 2])))
        + ".",
        "T36_SRCTOLD": lambda: (f"You told me: USER's {r.choice(PERSON_RELS)}"
                                f" is {g.p()}."),
        "T37_SRCPUT": lambda: (lambda b: f"I put together things you told me:"
                               f" USER's boss is {b}. {b}'s city is "
                               f"{r.choice(PLACES)}.")(g.p()),
        "T38_FACTS": lambda: (f"I know {g.n(0, 14)} facts you taught me. I "
                              f"also hold {g.n(0, 3)} web row, which I do "
                              f"not believe."),
        "T39_PEOPLE": lambda: (lambda ns: f"I know {len(ns)} people: "
                               + ", ".join(ns) + ".")(sorted(
                                   r.sample(PEOPLE, g.n(1, 5))
                                   + (["USER"] if r.random() < 0.5 else []))),
        "T40_WEBN": lambda: (f"Yes. I hold {g.n(1, 12)} quarantined web row."
                             f" I filed it but I do not believe it."),
        "T41_SLEPTN": lambda: f"Yes. I have slept {g.n(1, 12)} times.",
        "T42_SLEEPDERIVED": lambda: (f"None. {g.n(0, 12)} of my facts are "
                                     f"sleep-derived."),
        "T43_TURNS": lambda: f"We have had {g.n(0, 9)} turns.",
        "T44_ANSWERED": lambda: f"I have answered {g.n(0, 12)} questions.",
        "T45_SAVEDN": lambda: f"I saved {g.n(0, 12)} times through our turns.",
        "T46_REFUSED0": lambda: (f"No. I understood all {g.n(1, 12)} turns; "
                                 f"I asked for clarification 0 times."),
        "T47_REFUSEDN": lambda: (f"Yes, {g.n(1, 12)} times I asked for "
                                 f"clarification instead of saving."),
        "T48_GUESSES": lambda: (f"{g.n(0, 12)} guesses are waiting for your "
                                f"approval."),
        "T49_RULES": lambda: f"{g.n(0, 12)} of my facts came from rules.",
        "T50_BARECOUNT": lambda: f"{g.n(0, 14)}.",
        "T51_DREAM": lambda: (f"I do not dream. I have slept {g.n(0, 4)} "
                              f"times and hold {g.n(0, 4)} sleep-derived "
                              f"facts."),
        "T52_YESTERDAY": lambda: ("I have no record of yesterday. My log "
                                  "starts with our first turn here and holds "
                                  f"{g.n(1, 9)} turns."),
        "T53_NOBODYELSE": lambda: ("Nobody besides you has spoken to me. All "
                                   f"{g.n(1, 12)} turns are yours."),
        "T54_C5NOTURN": lambda: "You did, in turn ?.",
        "T55_UNSURE": lambda: "I am unsure about: " + "; ".join(r.sample([
            f"{g.p()}'s {r.choice(PERSON_RELS)} (never taught)",
            f"USER's {r.choice(PERSON_RELS)} (never taught)",
            "the web row (quarantined, not believed)",
            f"{g.n(1, 4)} proposed rows waiting for your approval"],
            r.choice([1, 2, 3]))) + ".",
        "T56_DONTKNOWEX": lambda: ("I say I do not know instead of guessing. "
                                   "Like when you asked: Who is "
                                   f"{g.p()}'s {r.choice(PERSON_RELS)}?"),
        "T57_JUSTBEFORE": lambda: (lambda a, b, rel: (
            f"Just before that, in turn {g.n(1, 20)}, you asked: " + r.choice(
                [f"Who is {a}'s {rel}? I replied: {a}'s {rel} is {b}.",
                 f"{a}'s {rel} is {b}. I replied: Saved: {a}'s {rel} is "
                 f"{b}."])))(g.p(), g.p(), r.choice(PERSON_RELS)),
        "T58_UPDATEDUSER": lambda: (f"Updated: USER's {r.choice(PERSON_RELS)}"
                                    f" is {g.p()} (it was {g.p()})."),
        "T59_NOTSAVED": lambda: ("I could NOT save that: the notebook "
                                 f"reported a problem (E{g.n(10, 99)})."),
        "T60_NEWUNSTORED": lambda: (
            f"You told me something new about {g.p()}'s "
            f"{r.choice(PERSON_RELS)} that I could not store. I can take one "
            "fact at a time — could you say it again as one fact?"),
    }


def unchanged_forms(g: G) -> dict:
    r = g.r
    rel = lambda: r.choice(PERSON_RELS)  # noqa: E731
    return {
        "U01_ALREADY": lambda: "I already have that.",
        "U02_NONAME": lambda: ("You never told me your name, so I do not "
                               "know it."),
        "U03_DONTKNOWREL": lambda: f"I don't know {g.p()}'s {rel()}.",
        "U04_THANKS": lambda: "You're welcome!",
        "U05_NOBODYWHOSE": lambda: (f"I don't know anyone whose {rel()} is "
                                    f"{g.p()}."),
        "U06_YOURNAME": lambda: f"Your name is {g.p()}.",
        "U07_MAKER": lambda: "Ben built me.",
        "U08_NONAMEYET": lambda: "I don't know your name yet.",
        "U09_WHAT": lambda: ("I'm a small program that keeps what you teach "
                             "me in a notebook and answers from it. When I "
                             "don't know something, I say so instead of "
                             "guessing."),
        "U10_APOLOGY": lambda: "No worries!",
        "U11_DONTHAVE": lambda: (f"I don't have {g.p()} as {g.p()}'s "
                                 f"{rel()}."),
        "U12_NOTHINGSAID": lambda: "I haven't said anything yet.",
        "U13_UNKNOWNNAME": lambda: f"I don't know anyone called {g.p()}.",
        "U14_WHICHONE": lambda: (f"{g.p()}'s {rel()} is {g.p()} and {g.p()}."
                                 f" Which one do you mean?"),
        "U15_CHANGEQ": lambda: (f"I have {g.p()}'s {rel()} as {g.p()}. Do you"
                                f" want me to change it to {g.p()}?"),
        "U16_CHANGENAME": lambda: (f"I have your name as {g.p()}. Do you want"
                                   f" me to change it to {g.p()}?"),
        "U17_HERE": lambda: ("I'm here and ready to learn. Tell me something,"
                             " or ask me about what you've told me."),
        "U18_HIHERE": lambda: ("Hi! I'm here and ready to learn. Tell me "
                               "something, or ask me about what you've told "
                               "me."),
        "U19_NAME": lambda: "My name is Premonition.",
        "U20_FAVOURITES": lambda: "I do not have favourites.",
        "U21_LAUGH": lambda: "Haha, nice!",
        "U22_BYE": lambda: "Bye!",
        "U23_ACK": lambda: "Got it!",
        "U24_SAVED": lambda: f"Saved: {T255.user_np(g.fs())}.",
        "U25_SAVEDALSO": lambda: (lambda s3, rr: f"Saved: {s3[0]}'s {rr} is"
                                  f" {s3[1]}. (I also have {s3[2]}.)")(
                                      r.sample(PEOPLE, 3),
                                      r.choice(["friend", "sister"])),
        "U26_UPDATED": lambda: (f"Updated: {g.p()}'s {rel()} is {g.p()} "
                                f"(it was {g.p()})."),
        "U27_FORGOTTEN": lambda: f"Forgotten: {g.p()}'s {rel()}.",
        "U28_FORGOTTENONE": lambda: f"Forgotten: {g.p()}'s {rel()} {g.p()}.",
        "U29_NOTAUGHT": lambda: "You haven't taught me anything yet.",
        "U30_NORECORD": lambda: ("I have no record of that, so I do not know "
                                 "it."),
        "U31_HEARSAY": lambda: ("Do you know that yourself, or did you hear "
                                "it somewhere? I only save facts you tell me "
                                "directly."),
        "U32_NOTSLEPT": lambda: "Nothing. I have not slept yet.",
        "U33_NOTFORGOT": lambda: ("I haven't forgotten anything you taught "
                                  "me."),
        "U34_CITYNOTSURE": lambda: ("I have no record of that city, so I "
                                    "cannot be sure."),
        "U35_NOTHINGOPEN": lambda: ("Nothing is open. Every question you "
                                    "asked was answered."),
        "U36_ALLFROMYOU": lambda: "No. Every taught fact came from you.",
        "U37_NOWEB": lambda: "I haven't filed anything from the web.",
        "U38_DONTKNOWCALLED": lambda: (f"I do not know that. I don't know "
                                       f"anyone called {g.p()}."),
        "U39_NOWHY": lambda: ("You never told me why. I only store what you "
                              "state, not reasons."),
        "U40_NOOPINIONS": lambda: "I have no opinions.",
        "U41_AGE": lambda: ("I don't have an age. I'm a program, so I don't "
                            "measure my life in years."),
        "U42_HOME": lambda: ("I don't live anywhere. I'm a program that runs"
                             " on a computer and keeps a notebook file."),
        "U43_LEARN": lambda: ('I learn when you tell me facts in plain '
                              'sentences, like "Kim lives in Oslo." I save '
                              'each one and answer from my notes.'),
        "U44_NAMEYES": lambda: "Yes, my name is Premonition.",
        "U45_NAMENO": lambda: "No, my name is Premonition.",
        "U46_NOTNEG": lambda: (lambda s2, rr: f"OK, {s2[0]}'s {rr} is not "
                               f"{s2[1]}. I don't have another {rr} for "
                               f"{s2[0]}.")(r.sample(PEOPLE, 2), rel()),
        "U47_PRETEND": lambda: ("OK, I'll treat that as pretend, so I won't "
                                "save it."),
        "U48_DESCRIPTION": lambda: (lambda a: "That sounds like a "
                                    "description, not a name, so I didn't "
                                    f"save it. What is {a}'s mother's name?"
                                    )(g.p()),
        "U49_NOTWAITING": lambda: "I wasn't waiting for an answer.",
        "U50_NOTCATCH": lambda: "I didn't catch anything.",
        "U51_LEFTIT": lambda: "Okay, I left it as it was.",
        "U52_YESNO": lambda: (lambda a, p: r.choice(["Yes", "No"]) +
                              f", {a}'s city is {p}.")(g.p(),
                                                        r.choice(PLACES)),
        "U53_SOURCETOLD": lambda: f"You told me: {g.fs(False)}.",
        "U54_FALLTHROUGH": lambda: ("I didn't understand that. Could you say "
                                    "it another way?"),
        "U55_ONLYONLINE": lambda: ("No. Web rows are quarantined and never "
                                   "answer questions. Only what you teach me "
                                   "answers."),
        "U56_NOTHINGNEW": lambda: "Nothing new was installed while sleeping.",
        "U57_EMPTYLOG": lambda: ("Just before that I did nothing; the log is "
                                 "empty."),
    }


def main(argv) -> int:
    out = Path(argv[0])
    rng = random.Random(SEED)
    g = G(rng)
    rows = []
    forms = old_forms(g)
    rule_ids = [t for t, _p, _f in T255.RULES]
    assert set(rule_ids) == set(forms), set(rule_ids) ^ set(forms)
    # fixed-string changed templates: once each
    done = set()
    for old, (tid, new255) in T255.EXACT.items():
        if tid in done:
            continue
        # 255b: T02 renders the new Part A text; every other fixed
        # string renders exactly as 255
        new = T.T02_NEW_255B if tid == "T02_Q2" else new255
        got, gt = T.rewrite255b(old)
        assert gt == tid and got == new, (tid, got, new)
        rows.append({"template_id": tid, "text": new, "kind": "changed"})
        done.add(tid)
    # slot templates: 5 distinct renders (once when the text cannot vary)
    for tid in rule_ids:
        texts, tries = [], 0
        while len(texts) < 5 and tries < 400:
            tries += 1
            g.reset()
            new, gt = T.rewrite255b(forms[tid]())
            if gt == tid and new not in texts:
                texts.append(new)
        assert texts, tid
        for t in texts:
            rows.append({"template_id": tid, "text": t, "kind": "changed"})
    for uid, fn in unchanged_forms(g).items():
        g.reset()
        t = fn()
        assert T.rewrite255b(t)[1] is None, (uid, t)
        rows.append({"template_id": uid, "text": t, "kind": "unchanged"})
    rng.shuffle(rows)
    with out.open("w", encoding="utf-8") as fh:
        for i, row in enumerate(rows, 1):
            fh.write(json.dumps({"id": f"r{i:03d}",
                                 "template_id": row["template_id"],
                                 "text": row["text"]},
                                ensure_ascii=False) + "\n")
    nch = sum(r["kind"] == "changed" for r in rows)
    print(f"wrote {len(rows)} rows ({nch} changed-template renders, "
          f"{len(rows) - nch} unchanged) -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
