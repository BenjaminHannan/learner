"""Generator for the blind small-talk panel 234 (hand-written items, no randomness).

Run from the repo root:
  python3 -B artifacts/claude-smalltalkpanel234-20260922/make_panel.py
Writes panel.jsonl next to this file. All names and towns are fictional.
"""
import json
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
items = []


def add(family, setup, turn, expect, gold=None, clear=True, notes=""):
    items.append({
        "id": "s234-%03d" % (len(items) + 1),
        "family": family,
        "setup": list(setup),
        "turn": turn,
        "expect": expect,
        "gold": gold,
        "clear": clear,
        "notes": notes,
    })


# ---- wellbeing (20): greeting and/or how-are-you aimed at the assistant ----
W = [
    ("Hi, how are you?", True, "textbook greeting + wellbeing"),
    ("hey there, how's it going", True, "lower-case, no question mark"),
    ("How are you doing today?", True, ""),
    ("How've you been?", True, "contraction"),
    ("Good morning! How are things?", True, ""),
    ("how r u", True, "text-speak"),
    ("hello", True, "bare greeting, no wellbeing question"),
    ("Hi there!", True, "bare greeting"),
    ("good evening, how are you tonight", True, ""),
    ("hey how are you", True, "no punctuation"),
    ("Hello! How is your day going?", True, "'your day' = the assistant's"),
    ("hiya, you doing ok?", True, "no 'how'"),
    ("How are you feeling today?", True, ""),
    ("whats up", True, "no apostrophe, no '?'"),
    ("Hey! How's your morning been?", True, ""),
    ("Hi, hope you're well. How are you?", True, ""),
    ("good afternoon", True, "bare greeting"),
    ("howdy, how are ya", True, "dialect spelling"),
    ("Hi! Are you doing alright?", False, "yes/no wellbeing; could be read as a status check"),
    ("hey, how's everything with you", True, ""),
]
for turn, clear, note in W:
    add("wellbeing", [], turn, "small_talk", None, clear, note)

# ---- people_wellbeing (12): asks about a PERSON, not the assistant ----
P = [
    ([], "How is Marta?", True, "no setup; must not answer about itself"),
    (["Marta lives in Fennick."], "How's Marta doing?", True, "setup does not answer wellbeing"),
    (["Oskar's job is baker."], "How's Oskar's new job going?", True, "job taught but 'how is it going' is not"),
    (["Priya's son is Dev."], "How are Priya's kids?", True, "kids question, one child taught"),
    ([], "hey how's Tomasz", True, "lower-case, greeting-free, no '?'"),
    (["Lina lives in Harrowgate."], "how is Lina getting on in Harrowgate", True, "town repeated in the turn"),
    ([], "How's Benedek been lately?", True, ""),
    (["Rufus's wife is Carla."], "How is Rufus's wife?", True, "relation taught, wellbeing not"),
    ([], "hi, how is Aunt Greta doing", False, "greeting + person; 'Aunt' title makes the name less clean"),
    (["Nadia's dog is Pepper."], "How's Nadia's dog?", True, "pet, not a person"),
    ([], "how are Wendell and Mae", True, "two people"),
    (["Ilse's school is Birchwood."], "How is Ilse's school going?", True, ""),
]
for setup, turn, clear, note in P:
    add("people_wellbeing", setup, turn, "not_small_talk", None, clear, note)

# ---- status (8): asks what the assistant is doing / which mode ----
S = [
    ("What are you doing right now?", True, ""),
    ("What mode are you in?", True, ""),
    ("Are you listening?", True, ""),
    ("what are you up to", False, "could be read as casual small talk; brief files it under status"),
    ("are you awake", True, "sleep-mode question"),
    ("What are you working on at the moment?", True, ""),
    ("Are you thinking right now?", True, ""),
    ("hey what are you doing", False, "greeting + status; casual phrasing"),
]
for turn, clear, note in S:
    add("status", [], turn, "not_small_talk", None, clear, note)

# ---- greeting_plus_question (8): greeting + a question the notebook answers ----
G = [
    (["Hugo lives in Pellmore."], "Hi! Where does Hugo live?", "Pellmore", True, ""),
    (["Sanna's boss is Ferris."], "hey, who is Sanna's boss?", "Ferris", True, ""),
    (["Ada lives in Quillby."], "Good morning, where does Ada live", "Quillby", True, "no '?'"),
    (["Joss's sister is Tamsin."], "hello! who's Joss's sister", "Tamsin", True, "contraction who's"),
    (["Corin lives in Wexham."], "Hi, how are you? Where does Corin live?", "Wexham", False,
     "greeting + wellbeing + real question; gold is Wexham; a small-talk reply alone is wrong; a friendly opener before the answer is fine"),
    (["Bea's doctor is Dr Lomax."], "hey there, who is Bea's doctor?", "Dr Lomax", True, "value has a title"),
    (["Milo lives in Stonebridge."], "hiya where does milo live", "Stonebridge", True, "lower-case name"),
    (["Petra's cousin is Anselm."], "Hello again! Who is Petra's cousin?", "Anselm", True, ""),
]
for setup, turn, gold, clear, note in G:
    add("greeting_plus_question", setup, turn, "answer", gold, clear, note)

# ---- plain_questions (8): contain 'how' but are not small talk ----
Q = [
    (["Kim lives in Brellin."], "How old is Kim?", "not_small_talk", None, True, "age untaught"),
    (["Rhea's boss is Lee."], "How does Rhea get to work?", "not_small_talk", None, True, "commute untaught"),
    (["Tobin lives in Marsh End."], "how many sisters does Tobin have", "not_small_talk", None, True, "untaught count"),
    (["Yara's brother is Omar."], "How tall is Yara?", "not_small_talk", None, True, "untaught"),
    (["Felix lives in Dunmore."], "How long has Felix lived in Dunmore?", "not_small_talk", None, True,
     "town taught, duration not"),
    (["Esme's age is 34."], "How old is Esme?", "answer", "34", False,
     "taught via the relation form 'age'; answering needs age<->how old mapping"),
    (["Gus's car is a blue van."], "how does Gus get around", "not_small_talk", None, False,
     "car taught but it does not strictly answer 'how does he get around'"),
    (["Nell lives in Arbury."], "How far is Arbury from here?", "not_small_talk", None, True, "untaught distance"),
]
for setup, turn, expect, gold, clear, note in Q:
    add("plain_questions", setup, turn, expect, gold, clear, note)

assert len(items) == 56, len(items)
with open(os.path.join(HERE, "panel.jsonl"), "w") as f:
    for it in items:
        f.write(json.dumps(it) + "\n")
print(Counter(i["family"] for i in items))
print(Counter(i["expect"] for i in items))
print("unclear:", sum(not i["clear"] for i in items))
