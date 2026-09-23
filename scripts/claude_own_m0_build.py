"""Builder for own-M0: conversational-mouth training pairs (CPU only).

Input: checked reply record (talker120-style) + user_turn + tag.
Output row: {"record": {...}, "user_turn": ..., "tag": ..., "reply": ...}
Reply uses slot tokens <S1> (owner), <V1> (value), <R1> (relation phrase);
no literal names appear in reply text.

Statuses: OK, UNKNOWN, ABSTAIN, CLARIFY, SAVED, FORGOT.
Tags: ANSWER, ACK_SAVE, ABSTAIN, CLARIFY, FORGOT_ACK, WHOSE.
WHOSE rows carry status CLARIFY (ask-whose; Ben's our-policy rule).

Filter: claude_own_m0_check.check_row. Failing rows are dropped + counted.
Modes: build (default), --verify (fresh re-check + Pm0.1-Pm0.4), --selftest.
"""
import argparse
import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__))))
from claude_own_m0_check import check_row, TALKER120_BLOCK  # noqa: E402

SEED_TRAIN = 20260923
SEED_DEV = 20260924

# ---------------- pools (all fictional; disjointness asserted in main) ----
TRAIN_OWNERS = [
    "Aldo", "Bren", "Calsa", "Dain", "Effa", "Fenn", "Grell", "Hobb",
    "Ilsa", "Joss", "Kebb", "Lorn", "Mabs", "Noll", "Ossa", "Porlo",
    "Quill", "Renn", "Sella", "Tonn", "Uffa", "Voll", "Wessa", "Xan",
    "Yorlo", "Zellin", "Cressa", "Dullo", "Emric", "Folla", "Gissa",
    "Harko", "Imsa", "Jullo", "Kempo", "Lissa", "Mullo", "Orla",
    "Pim", "Rulon", "Sara", "Tello", "Ulmira", "Vessa", "Willo",
    "Xolla", "Yessa", "Zuro", "Bella", "Corso", "Dessie", "Furno",
    "Gallo", "Hessa", "Ildo", "Jessie", "Kirra", "Lullo", "Morna",
    "Nello", "Ostin", "Prillo", "Ressa", "Sillo",
]
DEV_OWNERS = [
    "Abbo", "Brullo", "Cillo", "Drallo", "Ello", "Frilla", "Grullo",
    "Hrallo", "Illo", "Jrallo", "Krallo", "Lrallo", "Mrillo", "Nrallo",
    "Orillo", "Prallo", "Qrillo", "Rrallo", "Srillo", "Trallo",
    "Urillo", "Vrallo", "Wrillo", "Xrallo", "Yrillo", "Zrallo",
    "Abella", "Brella", "Crella", "Drella", "Erella", "Frella",
    "Grella", "Hrella", "Irella", "Jrella", "Krella", "Lrella",
    "Mrella", "Nrella",
]
TRAIN_VALUES = [
    "Ander", "Borto", "Cilla", "Dorio", "Enna", "Forlo", "Gunda",
    "Hillo", "Inna", "Jorlo", "Killa", "Lando", "Milla", "Norto",
    "Olla", "Pardo", "Quilla", "Rorto", "Silla", "Tordo", "Ulla",
    "Vorto", "Willa", "Xordo", "Ylla", "Zorto", "Andor", "Bellie",
    "Cort", "Della", "Entor", "Fella", "Gort", "Hella", "Intor",
    "Jella", "Kort", "Lella", "Mentor2", "Nella", "Ontor", "Pellie",
    "Qort", "Rella", "Sortor", "Tella", "Urtor", "Vella", "Wortor",
    "Xella", "Yrtor", "Zella", "Ansel", "Borto2", "Cresel", "Dorto",
    "Ensel", "Forta", "Gesel", "Horta", "Insel", "Jorta", "Kesel",
    "Lorta",
]
DEV_VALUES = [
    "Avallo", "Bvallo", "Cvallo", "Dvallo", "Evallo", "Fvallo",
    "Gvallo", "Hvallo", "Ivallo", "Jvallo", "Kvallo", "Lvallo",
    "Mvallo", "Nvallo", "Ovallo", "Pvallo", "Qvallo", "Rvallo",
    "Svallo", "Tvallo", "Uvallo", "Vvallo", "Wvallo", "Xvallo",
    "Yvallo", "Zvallo", "Avella", "Bvella", "Cvella", "Dvella",
    "Evella", "Fvella", "Gvella", "Hvella", "Ivella", "Jvella",
    "Kvella", "Lvella", "Mvella", "Nvella",
]
TRAIN_PLACES = [
    "Rook", "Vell", "Ostport", "Nortown", "Millford", "Cinderbay",
    "Aldermoor", "Fenwick", "Gullhaven", "Harborlight", "Inkwell",
    "Juniper", "Kestrel", "Larkspur", "Mossbank", "Nettlefield",
    "Oakhollow", "Pebbleton", "Quarryside", "Reedmarsh", "Salthaven",
    "Thistledown", "Umberford", "Willowmere",
]
DEV_PLACES = [
    "Ashford2", "Briarfield", "Cloverbrook", "Dunmore", "Elmsworth",
    "Foxglove", "Glenhaven", "Heathmoor", "Ivybridge", "Jaspervale",
    "Knottsford", "Lindenholt", "Maplegrove", "Nixholm", "Owlerbar",
    "Ploverst",
]
THING_VALUES = {
    "favorite_color": ["blue", "green", "red", "amber", "violet"],
    "hobby": ["chess", "knitting", "sailing", "archery", "pottery"],
    "favorite_food": ["noodles", "plums", "honey", "cheese", "melon"],
    "sport": ["tennis", "rowing", "cycling", "skating", "darts"],
}

# (key, noun for R1, kind). Nouns mirror say_forms.json relation nouns.
PERSON_RELS = [
    ("mother", "mother"), ("father", "father"), ("sister", "sister"),
    ("brother", "brother"), ("spouse", "spouse"), ("friend", "friend"),
    ("boss", "boss"), ("teacher", "teacher"), ("doctor", "doctor"),
    ("neighbour", "neighbour"), ("cousin", "cousin"), ("aunt", "aunt"),
    ("uncle", "uncle"), ("mentor", "mentor"),
]
PLACE_RELS = [
    ("city", "city"), ("hometown", "hometown"), ("country", "country"),
    ("school", "school"), ("work_location", "workplace"),
]
THING_RELS = [
    ("favorite_color", "favorite color"), ("hobby", "hobby"),
    ("favorite_food", "favorite food"), ("sport", "sport"),
]

# ---------------- reply templates (slots kept; ASCII only) -----------------
T_OK = [
    "Yep, <S1>'s <R1> is <V1>.",
    "Yeah, <S1>'s <R1> is <V1>.",
    "Sure, <S1>'s <R1> is <V1>.",
    "Right, <S1>'s <R1> is <V1>.",
    "Okay, <S1>'s <R1> is <V1>.",
    "Ah, that's easy. <S1>'s <R1> is <V1>.",
    "Oh nice, <S1>'s <R1> is <V1>.",
    "<S1>'s <R1> is <V1>. Happy to help!",
    "The answer is <V1>. That's <S1>'s <R1>.",
    "It's <V1>. <S1>'s <R1>, I mean.",
    "<V1>, that's who. <S1>'s <R1>.",
    "I've got <V1> down as <S1>'s <R1>.",
    "I remember this one. <S1>'s <R1> is <V1>.",
    "Oh, I know this. <S1>'s <R1> is <V1>.",
    "That's <V1>. <S1>'s <R1>.",
    "<S1>'s <R1>? That's <V1>.",
    "Yeah! <S1>'s <R1> is <V1>.",
    "The <R1> of <S1> is <V1>.",
    "So <S1>'s <R1> is <V1>. Anything else?",
    "From what you told me, <S1>'s <R1> is <V1>.",
    "You told me <S1>'s <R1> is <V1>, and here it is.",
    "Yep, it's <V1>. That's <S1>'s <R1>.",
    "<V1> it is. <S1>'s <R1>.",
    "Sure thing, <S1>'s <R1> is <V1>.",
    "Gotcha. <S1>'s <R1> is <V1>.",
    "Yeah, that's <V1>. <S1>'s <R1>.",
    "Oh yeah, <S1>'s <R1> is <V1>.",
    "Right then, <S1>'s <R1> is <V1>.",
    "Okay then, <S1>'s <R1> is <V1>.",
    "Nice one. <S1>'s <R1> is <V1>.",
    "Great question. <S1>'s <R1> is <V1>.",
    "Thanks for asking. <S1>'s <R1> is <V1>.",
    "Here you go. <S1>'s <R1> is <V1>.",
    "Here it is. <S1>'s <R1> is <V1>.",
    "And the answer is <V1>. <S1>'s <R1>.",
    "Lovely question. <S1>'s <R1> is <V1>.",
    "Glad you asked. <S1>'s <R1> is <V1>.",
    "Sure, I have that. <S1>'s <R1> is <V1>.",
    "Yeah, I have it. <S1>'s <R1> is <V1>.",
    "Yep, I have that one. <S1>'s <R1> is <V1>.",
    "Oh sure, <S1>'s <R1> is <V1>.",
    "Ah right, <S1>'s <R1> is <V1>.",
    "Fantastic question. <S1>'s <R1> is <V1>.",
    "Awesome, <S1>'s <R1> is <V1>.",
    "Wonderful. <S1>'s <R1> is <V1>.",
    "Perfect, <S1>'s <R1> is <V1>.",
    "Sweet, <S1>'s <R1> is <V1>.",
    "Yeah, <S1>'s <R1> is <V1>. Want me to remember anything else about <S1>?",
    "Yep, <S1>'s <R1> is <V1>. Anything else you want to know about <S1>?",
    "<S1>'s <R1> is <V1>. What else can I tell you?",
    "<S1>'s <R1> is <V1>. Shall I keep going?",
]
T_SAVED = [
    "Got it, <S1>'s <R1> is <V1>. I've saved that.",
    "Nice, noted. <S1>'s <R1> is <V1>.",
    "Saved. <S1>'s <R1> is <V1>.",
    "Done. I've saved that <S1>'s <R1> is <V1>.",
    "Okay, saved. <S1>'s <R1> is <V1>.",
    "Got it. <S1>'s <R1> is <V1>, stored.",
    "Noted! <S1>'s <R1> is <V1>.",
    "Thanks, I've got it. <S1>'s <R1> is <V1>, saved.",
    "Great, saved. <S1>'s <R1> is <V1>.",
    "Perfect, noted. <S1>'s <R1> is <V1>.",
    "Yep, saved. <S1>'s <R1> is <V1>.",
    "Yeah, I've stored that. <S1>'s <R1> is <V1>.",
    "Sure, noted. <S1>'s <R1> is <V1>.",
    "Oh nice, saved. <S1>'s <R1> is <V1>.",
    "Happy to save that. <S1>'s <R1> is <V1>, noted.",
    "Done deal. <S1>'s <R1> is <V1>, saved.",
    "Right, got it saved. <S1>'s <R1> is <V1>.",
    "Okay then, noted. <S1>'s <R1> is <V1>.",
    "Sweet, saved. <S1>'s <R1> is <V1>.",
    "Awesome, noted. <S1>'s <R1> is <V1>.",
    "Wonderful, saved. <S1>'s <R1> is <V1>.",
    "Fantastic, noted. <S1>'s <R1> is <V1>.",
    "Lovely, saved. <S1>'s <R1> is <V1>.",
    "Glad to save that. <S1>'s <R1> is <V1>, noted.",
    "Thanks for telling me. <S1>'s <R1> is <V1>, saved.",
    "Got it, and saved. <S1>'s <R1> is <V1>.",
    "Noted and saved. <S1>'s <R1> is <V1>.",
    "I've written that down and saved it. <S1>'s <R1> is <V1>.",
    "That's written down. <S1>'s <R1> is <V1>, saved.",
    "Stored! <S1>'s <R1> is <V1>.",
    "Saved it. <S1>'s <R1> is <V1>.",
    "Okay, I've stored that. <S1>'s <R1> is <V1>.",
    "Sure thing, saved. <S1>'s <R1> is <V1>.",
    "Yeah, noted it. <S1>'s <R1> is <V1>, saved.",
    "Yep, written down. <S1>'s <R1> is <V1>.",
    "Oh sure, saved. <S1>'s <R1> is <V1>.",
    "Ah, noted. <S1>'s <R1> is <V1>, saved.",
    "Right then, saved. <S1>'s <R1> is <V1>.",
    "Just saved that. <S1>'s <R1> is <V1>.",
    "All saved. <S1>'s <R1> is <V1>.",
    "And saved. <S1>'s <R1> is <V1>. Thanks!",
    "Got it, saved. <S1>'s <R1> is <V1>. Want me to remember anything else about <S1>?",
    "Nice, saved. <S1>'s <R1> is <V1>. Anything else to note about <S1>?",
    "Noted, <S1>'s <R1> is <V1>. What else?",
    "Saved! <S1>'s <R1> is <V1>. Shall I keep going?",
    "Stored, <S1>'s <R1> is <V1>. Anything else you want me to hold onto?",
    "Okay, that's saved. <S1>'s <R1> is <V1>.",
    "Great, that's noted. <S1>'s <R1> is <V1>.",
    "Perfect, that's stored. <S1>'s <R1> is <V1>.",
    "Done, <S1>'s <R1> is <V1>. Saved and sound.",
]
T_UNKNOWN_P = [
    "Hmm, I don't know who <S1>'s <R1> is yet.",
    "Oh, I'm not sure who <S1>'s <R1> is.",
    "Sorry, I have no idea who <S1>'s <R1> is.",
    "I don't know that one. Who <S1>'s <R1> is hasn't come up.",
    "Hmm, that's blank for me. I don't know who <S1>'s <R1> is.",
    "I can't say who <S1>'s <R1> is. You haven't told me.",
    "No clue, sorry. I don't know who <S1>'s <R1> is.",
    "Oh, I don't know who <S1>'s <R1> is. Want to tell me?",
    "Hmm, I'm not certain who <S1>'s <R1> is yet.",
    "I haven't got anything on that. I don't know who <S1>'s <R1> is.",
    "That's one I don't know. Who is <S1>'s <R1>?",
    "Sorry, no idea on that. Who <S1>'s <R1> is, I mean.",
    "Oh dear, I don't know who <S1>'s <R1> is.",
    "Honestly, I have no idea who <S1>'s <R1> is.",
    "Hmm, you haven't told me who <S1>'s <R1> is, so I don't know.",
    "I don't know who <S1>'s <R1> is, sorry!",
    "Not sure on that one. I don't know who <S1>'s <R1> is.",
    "I couldn't say who <S1>'s <R1> is. Nothing on that.",
    "Who <S1>'s <R1> is? I don't know, sorry.",
    "Ah, I don't know who <S1>'s <R1> is yet.",
]
T_UNKNOWN_L = [
    "Hmm, I don't know where <S1>'s <R1> is yet.",
    "Oh, I'm not sure where <S1>'s <R1> is.",
    "Sorry, I have no idea where <S1>'s <R1> is.",
    "I don't know that one. Where <S1>'s <R1> is hasn't come up.",
    "Hmm, that's blank for me. I don't know where <S1>'s <R1> is.",
    "I can't say where <S1>'s <R1> is. You haven't told me.",
    "No clue, sorry. I don't know where <S1>'s <R1> is.",
    "Oh, I don't know where <S1>'s <R1> is. Want to tell me?",
    "Hmm, I'm not certain where <S1>'s <R1> is yet.",
    "I haven't got anything on that. I don't know where <S1>'s <R1> is.",
    "That's one I don't know. Where is <S1>'s <R1>?",
    "Sorry, no idea on that. Where <S1>'s <R1> is, I mean.",
    "Oh dear, I don't know where <S1>'s <R1> is.",
    "Honestly, I have no idea where <S1>'s <R1> is.",
    "Hmm, you haven't told me where <S1>'s <R1> is, so I don't know.",
]
T_UNKNOWN_T = [
    "Hmm, I don't know what <S1>'s <R1> is yet.",
    "Oh, I'm not sure what <S1>'s <R1> is.",
    "Sorry, I have no idea what <S1>'s <R1> is.",
    "I don't know that one. What <S1>'s <R1> is hasn't come up.",
    "Hmm, that's blank for me. I don't know what <S1>'s <R1> is.",
    "I can't say what <S1>'s <R1> is. You haven't told me.",
    "No clue, sorry. I don't know what <S1>'s <R1> is.",
    "Oh, I don't know what <S1>'s <R1> is. Want to tell me?",
    "Hmm, I'm not certain what <S1>'s <R1> is yet.",
    "I haven't got anything on that. I don't know what <S1>'s <R1> is.",
    "That's one I don't know. What is <S1>'s <R1>?",
    "Sorry, no idea on that. What <S1>'s <R1> is, I mean.",
    "Oh dear, I don't know what <S1>'s <R1> is.",
    "Honestly, I have no idea what <S1>'s <R1> is.",
    "Hmm, you haven't told me what <S1>'s <R1> is, so I don't know.",
]
T_ABSTAIN_P = [
    "Hmm, I don't know who that is, so I can't say who <S1>'s <R1> is.",
    "Sorry, I don't know who <S1>'s <R1> is. I have nothing on that.",
    "Oh, I'm not sure. I don't know who <S1>'s <R1> is.",
    "I have no idea who <S1>'s <R1> is, sorry.",
    "Hmm, that's blank. I don't know who <S1>'s <R1> is.",
    "I can't say, sorry. I don't know who <S1>'s <R1> is.",
    "No idea at all. I don't know who <S1>'s <R1> is.",
    "Oh, I don't know who <S1>'s <R1> is. Could you tell me more?",
    "Hmm, not certain here. I don't know who <S1>'s <R1> is.",
    "I haven't got that one. I don't know who <S1>'s <R1> is.",
    "Sorry, that hasn't come up. I don't know who <S1>'s <R1> is.",
    "Honestly no idea. I don't know who <S1>'s <R1> is.",
    "Hmm, I don't know who <S1>'s <R1> is, and I can't say.",
    "Not sure, sorry. I don't know who <S1>'s <R1> is.",
    "I couldn't say. I don't know who <S1>'s <R1> is.",
    "Ah, I don't know who <S1>'s <R1> is. Nothing on that.",
]
T_ABSTAIN_L = [
    "Hmm, I don't know where that is, so I can't say where <S1>'s <R1> is.",
    "Sorry, I don't know where <S1>'s <R1> is. I have nothing on that.",
    "Oh, I'm not sure. I don't know where <S1>'s <R1> is.",
    "I have no idea where <S1>'s <R1> is, sorry.",
    "Hmm, that's blank. I don't know where <S1>'s <R1> is.",
    "I can't say, sorry. I don't know where <S1>'s <R1> is.",
    "No idea at all. I don't know where <S1>'s <R1> is.",
    "Oh, I don't know where <S1>'s <R1> is. Could you tell me more?",
    "Hmm, not certain here. I don't know where <S1>'s <R1> is.",
    "I haven't got that one. I don't know where <S1>'s <R1> is.",
    "Sorry, that hasn't come up. I don't know where <S1>'s <R1> is.",
    "Honestly no idea. I don't know where <S1>'s <R1> is.",
    "Hmm, I don't know where <S1>'s <R1> is, and I can't say.",
    "Not sure, sorry. I don't know where <S1>'s <R1> is.",
    "I couldn't say. I don't know where <S1>'s <R1> is.",
    "Ah, I don't know where <S1>'s <R1> is. Nothing on that.",
]
T_ABSTAIN_T = [
    "Hmm, I don't know what that is, so I can't say what <S1>'s <R1> is.",
    "Sorry, I don't know what <S1>'s <R1> is. I have nothing on that.",
    "Oh, I'm not sure. I don't know what <S1>'s <R1> is.",
    "I have no idea what <S1>'s <R1> is, sorry.",
    "Hmm, that's blank. I don't know what <S1>'s <R1> is.",
    "I can't say, sorry. I don't know what <S1>'s <R1> is.",
    "No idea at all. I don't know what <S1>'s <R1> is.",
    "Oh, I don't know what <S1>'s <R1> is. Could you tell me more?",
    "Hmm, not certain here. I don't know what <S1>'s <R1> is.",
    "I haven't got that one. I don't know what <S1>'s <R1> is.",
    "Sorry, that hasn't come up. I don't know what <S1>'s <R1> is.",
    "Honestly no idea. I don't know what <S1>'s <R1> is.",
    "Hmm, I don't know what <S1>'s <R1> is, and I can't say.",
    "Not sure, sorry. I don't know what <S1>'s <R1> is.",
    "I couldn't say. I don't know what <S1>'s <R1> is.",
    "Ah, I don't know what <S1>'s <R1> is. Nothing on that.",
]
T_FORGOT_P = [
    "Okay, I've forgotten who <S1>'s <R1> is.",
    "Done, I've forgotten who <S1>'s <R1> was.",
    "Sure, I've forgotten who <S1>'s <R1> is now.",
    "Okay, forgotten. I no longer hold who <S1>'s <R1> is.",
    "Right, that's forgotten. Who <S1>'s <R1> is, I mean.",
    "Yep, forgotten. I don't hold who <S1>'s <R1> is anymore.",
    "Yeah, I've wiped that. Who <S1>'s <R1> is, forgotten.",
    "Okay then, forgotten. Who <S1>'s <R1> is has gone.",
    "Sure thing, I've forgotten who <S1>'s <R1> is.",
    "Oh sure, that's forgotten now. Who <S1>'s <R1> is, I mean.",
    "Ah, forgotten. I no longer have who <S1>'s <R1> is.",
    "Nice, that's cleared. I've forgotten who <S1>'s <R1> is.",
    "Great, forgotten. Who <S1>'s <R1> is has gone from my notes.",
    "Perfect, I've forgotten who <S1>'s <R1> was.",
    "Thanks, and forgotten. Who <S1>'s <R1> is, I mean.",
    "Happy to forget that. Who <S1>'s <R1> is, gone.",
]
T_FORGOT_L = [
    "Okay, I've forgotten where <S1>'s <R1> is.",
    "Done, I've forgotten where <S1>'s <R1> was.",
    "Sure, I've forgotten where <S1>'s <R1> is now.",
    "Okay, forgotten. I no longer hold where <S1>'s <R1> is.",
    "Right, that's forgotten. Where <S1>'s <R1> is, I mean.",
    "Yep, forgotten. I don't hold where <S1>'s <R1> is anymore.",
    "Yeah, I've wiped that. Where <S1>'s <R1> is, forgotten.",
    "Okay then, forgotten. Where <S1>'s <R1> is has gone.",
    "Sure thing, I've forgotten where <S1>'s <R1> is.",
    "Oh sure, that's forgotten now. Where <S1>'s <R1> is, I mean.",
    "Ah, forgotten. I no longer have where <S1>'s <R1> is.",
    "Nice, that's cleared. I've forgotten where <S1>'s <R1> is.",
    "Great, forgotten. Where <S1>'s <R1> is has gone from my notes.",
    "Perfect, I've forgotten where <S1>'s <R1> was.",
    "Thanks, and forgotten. Where <S1>'s <R1> is, I mean.",
    "Happy to forget that. Where <S1>'s <R1> is, gone.",
]
T_FORGOT_T = [
    "Okay, I've forgotten what <S1>'s <R1> is.",
    "Done, I've forgotten what <S1>'s <R1> was.",
    "Sure, I've forgotten what <S1>'s <R1> is now.",
    "Okay, forgotten. I no longer hold what <S1>'s <R1> is.",
    "Right, that's forgotten. What <S1>'s <R1> is, I mean.",
    "Yep, forgotten. I don't hold what <S1>'s <R1> is anymore.",
    "Yeah, I've wiped that. What <S1>'s <R1> is, forgotten.",
    "Okay then, forgotten. What <S1>'s <R1> is has gone.",
    "Sure thing, I've forgotten what <S1>'s <R1> is.",
    "Oh sure, that's forgotten now. What <S1>'s <R1> is, I mean.",
    "Ah, forgotten. I no longer have what <S1>'s <R1> is.",
    "Nice, that's cleared. I've forgotten what <S1>'s <R1> is.",
    "Great, forgotten. What <S1>'s <R1> is has gone from my notes.",
    "Perfect, I've forgotten what <S1>'s <R1> was.",
    "Thanks, and forgotten. What <S1>'s <R1> is, I mean.",
    "Happy to forget that. What <S1>'s <R1> is, gone.",
]
T_CLARIFY = [
    "Hmm, which <S1> do you mean? I've got a couple of them.",
    "Sorry, which <S1> are you asking about?",
    "Oh, who do you mean by <S1>? There is more than one.",
    "Could you say which <S1> you mean?",
    "Hmm, I'm not sure which <S1> you mean. Can you clarify?",
    "Which <S1> is it? What did you have in mind?",
    "Sorry, who exactly do you mean by <S1>?",
    "Oh, there are two <S1>s here. Which one do you mean?",
    "Hmm, what do you mean by <S1>? Which one?",
    "Can you tell me which <S1> you mean?",
    "Sorry, I'm not sure who <S1> is here. Which one?",
    "Which <S1> do you have in mind? I want to be sure.",
    "Oh, which <S1>? I know more than one.",
    "Hmm, who is <S1> to you? Which one do you mean?",
    "What do you mean by <S1>, exactly? Which one?",
    "Sorry, could you clarify which <S1> you mean?",
    "Which <S1>, sorry? There are a couple.",
    "Oh dear, which <S1> do you mean? I don't want to mix them up.",
    "Hmm, I know two people called <S1>. Which one?",
    "Who do you mean, exactly? Which <S1>?",
    "Sorry, what <S1> are we talking about? Which one?",
    "Okay, which <S1> shall I look at? Who do you mean?",
    "Right, who do you mean by <S1>? Which one is it?",
    "Gotcha, but which <S1>? I want to get the right one.",
    "Sure, but which <S1> do you mean? Who is it?",
    "Yeah, which <S1>? Can you say a bit more?",
    "Yep, who do you mean by <S1>? Which one?",
    "Ah, which <S1> is that? Who do you mean?",
    "Oh nice, but which <S1>? Who are we talking about?",
    "Great, which <S1> do you mean? I want to be sure.",
    "Thanks, and which <S1> is it? Who do you mean?",
    "Perfect, but which <S1>? Who is it, exactly?",
    "Just to be sure, which <S1> do you mean?",
    "Let me be sure here. Which <S1> do you mean?",
    "Hmm, which <S1> are we talking about? Who is it?",
    "Sorry, which <S1>? What else can you tell me so I pick right?",
    "Oh, who is <S1>? I mean, which one are you after?",
    "Which <S1> would that be? Who do you have in mind?",
    "Hmm, sure, but which <S1>? Who do you mean?",
    "Okay, who is <S1>? Which one shall I answer about?",
    "Right, what do you mean by <S1>? Which person?",
    "Which <S1> are you after? I know two, I mean.",
    "Sorry, who? Which <S1> are you asking about?",
    "Hmm, <S1>? Which one do you mean, who is it?",
    "Oh, <S1>? Who do you mean exactly? Which one?",
    "Which <S1> did you have in mind? Who is it?",
]
T_WHOSE = [
    "Whose <R1> do you mean? Yours, or someone else's?",
    "Oh, whose <R1> is this? Is it yours?",
    "Hmm, whose <R1> are we talking about? Yours?",
    "Sorry, whose <R1> do you mean here? Yours or another's?",
    "Whose <R1> is it? I want to be sure before I save anything.",
    "Okay, whose <R1>? Is that yours, or someone else's?",
    "Right, whose <R1> are we talking about? Can you say?",
    "Hmm, is that your <R1>, or whose <R1> is it?",
    "Whose <R1> do you have in mind? Yours?",
    "Oh, I want to get this right. Whose <R1> is it?",
    "Sorry, whose <R1>? Yours, or a friend's?",
    "Whose <R1> shall I note? Yours or someone else's?",
    "Hmm, whose <R1> is this about? Is it yours?",
    "Okay, but whose <R1>? I don't want to mix that up.",
    "Whose <R1> are we saving here? Yours?",
    "Gotcha, but whose <R1> do you mean? Yours?",
    "Sure, but whose <R1> is it? Yours or someone else's?",
    "Yeah, whose <R1>? Can you tell me who it belongs to?",
    "Yep, whose <R1> are we talking about? Yours?",
    "Ah, whose <R1> is that? Is it yours?",
    "Oh nice, but whose <R1> is it? Yours?",
    "Great question, but whose <R1>? Yours or another's?",
    "Thanks, and whose <R1> is this? Is it yours?",
    "Perfect, but whose <R1> do you mean? Yours?",
    "Just to be sure, whose <R1> is it? Yours?",
    "Let me be sure here. Whose <R1> are we talking about?",
    "Hmm, whose <R1>? Yours, or someone in your group?",
    "Sorry, whose <R1> is it? I want to save it for the right person.",
    "Oh, whose <R1>? Is that yours to tell, or someone else's?",
    "Whose <R1> would that be? Yours?",
    "Hmm, sure, but whose <R1>? Who does it belong to?",
    "Okay, whose <R1> shall I answer about? Yours?",
    "Right, whose <R1> do you mean? Who is it for?",
    "Which group's <R1> is it? I mean, whose <R1>?",
    "Sorry, who does this <R1> belong to? I mean, whose is it?",
    "Hmm, <R1>? Whose <R1> is it, yours?",
    "Oh, a <R1>? Whose <R1>, sorry? Yours?",
    "Whose <R1> did you have in mind? Is it yours?",
    "How should I note this <R1>? I mean, whose <R1> is it?",
    "Can you say whose <R1> this is? Yours, or another's?",
    "Who is this <R1> for? I mean, whose <R1>?",
    "Is this about your <R1>? I mean, whose <R1> is it?",
    "Whose <R1> are you telling me about? Yours?",
    "Whose <R1> should I keep? Yours or someone else's?",
    "Hmm, who owns this <R1>? Whose is it, yours?",
    "Sorry to ask, but whose <R1> is it? Yours?",
]
# ---------------- user_turn frames ---------------------------------------
# {n} owner literal, {nl} owner lowercased, {r} relation surface,
# {v} value literal, {vl} value lowercased.
Q_FRAMES = {
    "person": [
        "who is {n}'s {r}?", "Who is {n}'s {r}?", "what is {n}'s {r}",
        "tell me {n}'s {r}", "{n}'s {r}?", "do u know {n}'s {r}",
        "whos {n}'s {r}", "who is {nl}'s {r}", "{nl}'s {r}?",
        "hey who is {n}'s {r} btw", "remind me: {n}'s {r}",
        "who is {n}'s {r} btw",
    ],
    "place": [
        "where is {n}'s {r}?", "Where is {n}'s {r}?", "what is {n}'s {r}",
        "tell me {n}'s {r}", "{n}'s {r}?", "do u know {n}'s {r}",
        "where is {nl}'s {r}", "{nl}'s {r}?", "hey where is {n}'s {r}",
        "remind me: {n}'s {r}", "what {r} is {n} from",
        "where does {n} live btw",
    ],
    "thing": [
        "what is {n}'s {r}?", "What is {n}'s {r}?", "whats {n}'s {r}",
        "tell me {n}'s {r}", "{n}'s {r}?", "do u know {n}'s {r}",
        "what is {nl}'s {r}", "{nl}'s {r}?", "hey what is {n}'s {r}",
        "remind me: {n}'s {r}", "what {r} does {n} like",
        "fav {r} of {n}?",
    ],
}
TELL_FRAMES = [
    "{n}'s {r} is {v}", "btw {n}'s {r} is {v}", "{nl}'s {r} is {v}",
    "just so u know, {n}'s {r} is {v}", "fyi {n}'s {r} is {v}",
    "{n}'s {r} is {v} btw", "oh btw {n}'s {r} is {v}",
    "hey, {n}'s {r} is {v}", "so {n}'s {r} is {v}",
    "quick note: {n}'s {r} is {v}", "{n}'s {r}? its {v}",
    "for {n}, {r} is {v}",
]
SHORT_FRAMES = [
    "{n}?", "tell me about {n}", "what about {n}", "and {n}?",
    "{n}...?", "u know {n}?", "more on {n} pls", "who is {n}",
    "{n} pls", "hmm {n}", "wait, {n}?", "tell me abt {n}",
]
FORGET_FRAMES = [
    "forget {n}'s {r}", "pls forget {n}'s {r}", "wipe {n}'s {r}",
    "i want u to forget {n}'s {r}", "forget what i said about {n}'s {r}",
    "can u forget {n}'s {r}", "drop {n}'s {r} from memory",
    "erase {n}'s {r}", "forget {nl}'s {r} pls", "unremember {n}'s {r}",
]
WHOSE_FRAMES = [
    "our {r} is {v}", "we have a {r} named {v}", "our {r}'s name is {v}",
    "we just got a {r}, {v}", "btw our {r} is {v}", "our {r} is {v} btw",
    "we call our {r} {v}", "ours is {v}, the {r}", "our {r}: {v}",
    "hey our {r} is {v}",
]

STATUS_TAG = {
    "OK": "ANSWER", "SAVED": "ACK_SAVE", "UNKNOWN": "ABSTAIN",
    "ABSTAIN": "ABSTAIN", "CLARIFY": "CLARIFY", "FORGOT": "FORGOT_ACK",
}

TRAIN_COUNTS = {"OK": 7000, "SAVED": 3000, "UNKNOWN": 3000,
                "ABSTAIN": 2000, "CLARIFY": 1500, "WHOSE": 1000,
                "FORGOT": 2500}
DEV_COUNTS = {"OK": 350, "SAVED": 150, "UNKNOWN": 150, "ABSTAIN": 100,
              "CLARIFY": 100, "WHOSE": 50, "FORGOT": 100}
REPLIES_PER_COMBO = 5


def pick_rel(rng, two_hop, force_kind=None):
    if force_kind is None:
        c = rng.random()
        if c < 0.55:
            force_kind = "person"
        elif c < 0.8:
            force_kind = "place"
        else:
            force_kind = "thing"
    if force_kind == "person":
        if two_hop:
            r1 = rng.choice(PERSON_RELS)
            r2 = rng.choice(PERSON_RELS)
            return ([r1[0], r2[0]], r1[1] + "'s " + r2[1], "person")
        r = rng.choice(PERSON_RELS)
        return ([r[0]], r[1], "person")
    if force_kind == "place":
        r = rng.choice(PLACE_RELS)
        return ([r[0]], r[1], "place")
    r = rng.choice(THING_RELS)
    return ([r[0]], r[1], "thing")


def pick_value(rng, kind, relkey, owners, values, places):
    if kind == "person":
        v = rng.choice(values)
        while v in owners:
            v = rng.choice(values)
        return v
    if kind == "place":
        return rng.choice(places)
    return rng.choice(THING_VALUES[relkey])


def templates_for(status, kind):
    if status == "OK":
        return T_OK
    if status == "SAVED":
        return T_SAVED
    if status == "UNKNOWN":
        return {"person": T_UNKNOWN_P, "place": T_UNKNOWN_L,
                "thing": T_UNKNOWN_T}[kind]
    if status == "ABSTAIN":
        return {"person": T_ABSTAIN_P, "place": T_ABSTAIN_L,
                "thing": T_ABSTAIN_T}[kind]
    if status == "FORGOT":
        return {"person": T_FORGOT_P, "place": T_FORGOT_L,
                "thing": T_FORGOT_T}[kind]
    if status == "CLARIFY":
        return T_CLARIFY
    if status == "WHOSE":
        return T_WHOSE
    raise ValueError(status)


def build_split(counts, owners, values, places, seed):
    rng = random.Random(seed)
    rows = []
    drops = {}
    combos = set()
    tid = [0]

    def trail(n):
        ids = []
        for _ in range(n):
            tid[0] += 1
            ids.append("M0%05d" % tid[0])
        return ids

    def make_combo(status, kcycle):
        for _ in range(200):
            two = status in ("OK", "UNKNOWN") and rng.random() < 0.2
            # UNKNOWN/ABSTAIN/FORGOT draw kinds in strict rotation so no
            # kind's template list dominates the status share (Pm0.2).
            force = ["person", "place", "thing"][kcycle[0] % 3] \
                if status in ("UNKNOWN", "ABSTAIN", "FORGOT") else None
            if force is not None:
                kcycle[0] += 1
            rels, phrase, kind = pick_rel(rng, two, force)
            owner = rng.choice(owners)
            if status == "WHOSE":
                val = rng.choice(values + places)
                key = ("WHOSE", tuple(rels), val)
            elif status in ("OK", "SAVED"):
                val = pick_value(rng, kind, rels[0], [owner], values,
                                 places)
                key = (owner, tuple(rels), val)
            else:
                val = None
                key = (owner, tuple(rels), status)
            if key not in combos:
                combos.add(key)
                return owner, rels, phrase, kind, val
        raise RuntimeError("combo space exhausted")

    def make_record(status, owner, rels, phrase, kind, val):
        src = rng.choice(["taught", "taught", "inferred"])
        if status == "OK":
            return {"kind": "answer", "status": "OK", "name": owner,
                    "relations": rels,
                    "fields": {"answer": val, "trail": trail(len(rels)),
                               "source": src}}
        if status == "SAVED":
            return {"kind": "answer", "status": "SAVED", "name": owner,
                    "relations": rels,
                    "fields": {"answer": val, "trail": trail(len(rels)),
                               "source": "taught"}}
        if status == "UNKNOWN":
            return {"kind": "answer", "status": "UNKNOWN", "name": owner,
                    "relations": rels,
                    "fields": {"subject": owner, "relation": rels[-1],
                               "hop": len(rels), "trail": [],
                               "source": "taught"}}
        if status == "ABSTAIN":
            return {"kind": "answer", "status": "ABSTAIN", "name": owner,
                    "relations": rels,
                    "fields": {"reason": "no record of that",
                               "source": "taught"}}
        if status == "FORGOT":
            return {"kind": "answer", "status": "FORGOT", "name": owner,
                    "relations": rels,
                    "fields": {"subject": owner, "relation": rels[-1],
                               "hop": len(rels), "source": "taught"}}
        if status == "CLARIFY":
            c1 = rng.choice(values)
            c2 = rng.choice(values)
            while c2 == c1:
                c2 = rng.choice(values)
            i1, i2 = trail(2)
            return {"kind": "answer", "status": "CLARIFY", "name": owner,
                    "relations": rels,
                    "fields": {"name": owner,
                               "choices": "%s (%s), %s (%s)" % (c1, i1,
                                                               c2, i2),
                               "ids": [i1, i2], "source": "taught"}}
        if status == "WHOSE":
            return {"kind": "answer", "status": "CLARIFY", "name": "our",
                    "relations": rels,
                    "fields": {"owner_phrase": "our",
                               "relation": rels[-1],
                               "stated_value": val, "source": "taught"}}
        raise ValueError(status)

    def make_turn(status, owner, phrase, kind, val):
        fmt = {"n": owner, "nl": owner.lower(), "r": phrase,
               "v": val or "", "vl": (val or "").lower()}
        if status == "OK" or status == "UNKNOWN" or status == "ABSTAIN":
            return rng.choice(Q_FRAMES[kind]).format(**fmt)
        if status == "SAVED":
            return rng.choice(TELL_FRAMES).format(**fmt)
        if status == "CLARIFY":
            return rng.choice(SHORT_FRAMES).format(**fmt)
        if status == "FORGOT":
            return rng.choice(FORGET_FRAMES).format(**fmt)
        if status == "WHOSE":
            return rng.choice(WHOSE_FRAMES).format(**fmt)
        raise ValueError(status)

    block = tuple(owners) + tuple(values) + tuple(places) + tuple(
        w for vs in THING_VALUES.values() for w in vs)
    for status, n in counts.items():
        tag = "WHOSE" if status == "WHOSE" else STATUS_TAG[
            status if status != "WHOSE" else "CLARIFY"]
        ncombo = n // REPLIES_PER_COMBO
        counters = {}
        made = 0
        ci = 0
        kcycle = [0]
        while made < n:
            owner, rels, phrase, kind, val = make_combo(status, kcycle)
            ci += 1
            for _ in range(REPLIES_PER_COMBO):
                if made >= n:
                    break
                lst = templates_for(status, kind)
                # round-robin per template list: uniform shares (Pm0.2).
                key = (status, id(lst))
                idx = counters.get(key, 0)
                counters[key] = idx + 1
                tmpl = lst[idx % len(lst)]
                rec = make_record(status, owner, rels, phrase, kind, val)
                turn = make_turn(status, owner, phrase, kind, val)
                bad = check_row(dict(rec, tag=tag), tmpl, block)
                if bad:
                    for r in bad:
                        drops[r] = drops.get(r, 0) + 1
                    continue
                rows.append({"record": rec, "user_turn": turn, "tag": tag,
                             "reply": tmpl})
                made += 1
    return rows, drops, combos


def write_jsonl(path, rows):
    with open(path, "w") as f:
        for o in rows:
            f.write(json.dumps(o) + "\n")


def load_jsonl(path):
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def stats_of(rows):
    from collections import Counter
    by_status = Counter()
    by_tag = Counter()
    by_reply_status = {}
    for o in rows:
        s = o["record"]["status"]
        by_status[s] += 1
        by_tag[o["tag"]] += 1
        by_reply_status.setdefault(s, Counter())[o["reply"]] += 1
    return by_status, by_tag, by_reply_status


def verify(adir):
    train = load_jsonl(os.path.join(adir, "train.jsonl"))
    dev = load_jsonl(os.path.join(adir, "dev.jsonl"))
    pools = json.load(open(os.path.join(adir, "pools.json")))
    block = tuple(pools["block"])
    ok = True
    for name, rows in (("train", train), ("dev", dev)):
        fails = 0
        for o in rows:
            rec = dict(o["record"])
            rec["tag"] = o["tag"]
            if check_row(rec, o["reply"], block):
                fails += 1
        print("Pm0.1 %s: rows=%d refails=%d" % (name, len(rows), fails))
        ok &= (fails == 0)
    for name, rows in (("train", train), ("dev", dev)):
        _, _, brs = stats_of(rows)
        for s, c in sorted(brs.items()):
            n = sum(c.values())
            top, topn = c.most_common(1)[0]
            share = 100.0 * topn / n
            ndist = len(c)
            print("Pm0.2/0.3 %s %s: n=%d distinct=%d top=%.2f%%" % (
                name, s, n, ndist, share))
            if topn / n > 0.03:
                ok = False
            if ndist < 40:
                ok = False
    tn = {o["record"]["name"] for o in train if o["tag"] != "WHOSE"}
    dn = {o["record"]["name"] for o in dev if o["tag"] != "WHOSE"}
    print("Pm0.4: train_names=%d dev_names=%d inter=%d" % (
        len(tn), len(dn), len(tn & dn)))
    ok &= (len(tn & dn) == 0)
    tc = {(o["tag"], o["record"]["name"], tuple(o["record"]["relations"]),
           o["record"]["fields"].get("answer"),
           o["record"]["fields"].get("stated_value"),
           o["record"]["status"]) for o in train}
    dc = {(o["tag"], o["record"]["name"], tuple(o["record"]["relations"]),
           o["record"]["fields"].get("answer"),
           o["record"]["fields"].get("stated_value"),
           o["record"]["status"]) for o in dev}
    print("combos: train=%d dev=%d inter=%d" % (len(tc), len(dc),
                                                len(tc & dc)))
    ok &= (len(tc & dc) == 0)
    return ok


def selftest():
    base_ok = {"kind": "answer", "status": "OK", "name": "Aldo",
               "relations": ["mother"],
               "fields": {"answer": "Ander", "trail": ["M000001"],
                          "source": "taught"}}
    cases = [
        (dict(base_ok, tag="ANSWER"), "Yep, <S1>'s <R1> is <V1>.", []),
        (dict(base_ok, tag="ANSWER"), "Yep, <S1>'s <R1> is.", ["R1_missing"]),
        (dict(base_ok, tag="ANSWER"), "Yep, Aldo's <R1> is <V1>.",
         ["R1_missing", "R3_caps"]),
        (dict(base_ok, tag="ANSWER"), "Yep, <S1>'s <R1> is <V1>. Got it.",
         ["R4_status"]),
        ({"kind": "answer", "status": "UNKNOWN", "name": "Aldo",
          "relations": ["city"],
          "fields": {"subject": "Aldo", "relation": "city", "hop": 1,
                     "trail": [], "source": "taught"}, "tag": "ABSTAIN"},
         "Hmm, I don't know where <S1>'s <R1> is yet.", []),
        ({"kind": "answer", "status": "UNKNOWN", "name": "Aldo",
          "relations": ["city"],
          "fields": {"subject": "Aldo", "relation": "city", "hop": 1,
                     "trail": [], "source": "taught"}, "tag": "ABSTAIN"},
         "Hmm, <S1>'s <R1> is <V1>.", ["R2_extra", "R4_status"]),
        ({"kind": "answer", "status": "FORGOT", "name": "Aldo",
          "relations": ["boss"],
          "fields": {"subject": "Aldo", "relation": "boss", "hop": 1,
                     "source": "taught"}, "tag": "FORGOT_ACK"},
         "Okay, I've forgotten who <S1>'s <R1> is.", []),
        ({"kind": "answer", "status": "FORGOT", "name": "Aldo",
          "relations": ["boss"],
          "fields": {"subject": "Aldo", "relation": "boss", "hop": 1,
                     "source": "taught"}, "tag": "FORGOT_ACK"},
         "Okay, who <S1>'s <R1> is, I mean.", ["R4_status"]),
        ({"kind": "answer", "status": "CLARIFY", "name": "our",
          "relations": ["dog"],
          "fields": {"owner_phrase": "our", "relation": "dog",
                     "source": "taught"}, "tag": "WHOSE"},
         "Whose <R1> do you mean? Yours, or someone else's?", []),
        ({"kind": "answer", "status": "CLARIFY", "name": "our",
          "relations": ["dog"],
          "fields": {"owner_phrase": "our", "relation": "dog",
                     "source": "taught"}, "tag": "WHOSE"},
         "Whose <R1> does <S1> mean?", ["R2_extra"]),
    ]
    bad = 0
    for rec, reply, want in cases:
        tag = rec.pop("tag")
        got = check_row(dict(rec, tag=tag), reply)
        if got != want:
            print("SELFTEST MISMATCH: %r got=%r want=%r" % (reply, got,
                                                            want))
            bad += 1
    # every template must pass on a fitting sample row
    p_row = {"kind": "answer", "status": "OK", "name": "Aldo",
             "relations": ["mother"],
             "fields": {"answer": "Ander", "trail": ["M000001"],
                        "source": "taught"}}
    l_row = {"kind": "answer", "status": "OK", "name": "Aldo",
             "relations": ["city"],
             "fields": {"answer": "Rook", "trail": ["M000001"],
                        "source": "taught"}}
    t_row = {"kind": "answer", "status": "OK", "name": "Aldo",
             "relations": ["hobby"],
             "fields": {"answer": "chess", "trail": ["M000001"],
                        "source": "taught"}}
    block = tuple(TRAIN_OWNERS + TRAIN_VALUES + TRAIN_PLACES +
                  [w for vs in THING_VALUES.values() for w in vs])
    checks = []
    for t in T_OK:
        checks.append((dict(p_row, tag="ANSWER"), t))
    for t in T_SAVED:
        checks.append((dict(p_row, status="SAVED", tag="ACK_SAVE",
                            fields={"answer": "Ander",
                                    "trail": ["M000001"],
                                    "source": "taught"}), t))
    unk_p = {"kind": "answer", "status": "UNKNOWN", "name": "Aldo",
             "relations": ["mother"],
             "fields": {"subject": "Aldo", "relation": "mother", "hop": 1,
                        "trail": [], "source": "taught"}}
    unk_l = dict(unk_p, relations=["city"],
                 fields={"subject": "Aldo", "relation": "city", "hop": 1,
                         "trail": [], "source": "taught"})
    unk_t = dict(unk_p, relations=["hobby"],
                 fields={"subject": "Aldo", "relation": "hobby", "hop": 1,
                         "trail": [], "source": "taught"})
    for t in T_UNKNOWN_P:
        checks.append((dict(unk_p, tag="ABSTAIN"), t))
    for t in T_UNKNOWN_L:
        checks.append((dict(unk_l, tag="ABSTAIN"), t))
    for t in T_UNKNOWN_T:
        checks.append((dict(unk_t, tag="ABSTAIN"), t))
    abs_p = dict(unk_p, status="ABSTAIN",
                 fields={"reason": "no record of that",
                         "source": "taught"})
    abs_l = dict(unk_l, status="ABSTAIN",
                 fields={"reason": "no record of that",
                         "source": "taught"})
    abs_t = dict(unk_t, status="ABSTAIN",
                 fields={"reason": "no record of that",
                         "source": "taught"})
    for t in T_ABSTAIN_P:
        checks.append((dict(abs_p, tag="ABSTAIN"), t))
    for t in T_ABSTAIN_L:
        checks.append((dict(abs_l, tag="ABSTAIN"), t))
    for t in T_ABSTAIN_T:
        checks.append((dict(abs_t, tag="ABSTAIN"), t))
    frg_p = {"kind": "answer", "status": "FORGOT", "name": "Aldo",
             "relations": ["boss"],
             "fields": {"subject": "Aldo", "relation": "boss", "hop": 1,
                        "source": "taught"}}
    frg_l = dict(frg_p, relations=["city"],
                 fields={"subject": "Aldo", "relation": "city", "hop": 1,
                         "source": "taught"})
    frg_t = dict(frg_p, relations=["hobby"],
                 fields={"subject": "Aldo", "relation": "hobby", "hop": 1,
                         "source": "taught"})
    for t in T_FORGOT_P:
        checks.append((dict(frg_p, tag="FORGOT_ACK"), t))
    for t in T_FORGOT_L:
        checks.append((dict(frg_l, tag="FORGOT_ACK"), t))
    for t in T_FORGOT_T:
        checks.append((dict(frg_t, tag="FORGOT_ACK"), t))
    clr = {"kind": "answer", "status": "CLARIFY", "name": "Aldo",
           "relations": ["boss"],
           "fields": {"name": "Aldo", "choices": "Ander (M000002)",
                      "ids": ["M000002"], "source": "taught"}}
    for t in T_CLARIFY:
        checks.append((dict(clr, tag="CLARIFY"), t))
    whs = {"kind": "answer", "status": "CLARIFY", "name": "our",
           "relations": ["dog"],
           "fields": {"owner_phrase": "our", "relation": "dog",
                      "source": "taught"}}
    for t in T_WHOSE:
        checks.append((dict(whs, tag="WHOSE"), t))
    for rec, t in checks:
        got = check_row(rec, t, block)
        if got:
            print("TEMPLATE FAIL: %r -> %r" % (t, got))
            bad += 1
    print("selftest templates=%d mismatches=%d" % (len(checks), bad))
    return bad == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="artifacts/claude-own-m0-20260923")
    ap.add_argument("--verify", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        sys.exit(0 if selftest() else 1)
    if args.verify:
        sys.exit(0 if verify(args.out) else 1)
    import claude_own_m0_check as C
    tb = set(TALKER120_BLOCK) if hasattr(C, "TALKER120_BLOCK") else set()
    mine = (TRAIN_OWNERS + DEV_OWNERS + TRAIN_VALUES + DEV_VALUES +
            TRAIN_PLACES + DEV_PLACES)
    assert len(set(mine)) == len(mine), "own pools overlap each other"
    assert not (set(mine) & tb), "own pool hits talker120 names: %s" % (
        sorted(set(mine) & tb))
    assert not (set(TRAIN_OWNERS) & set(DEV_OWNERS)), "owner pools overlap"
    os.makedirs(args.out, exist_ok=True)
    train, dtrain, _ = build_split(TRAIN_COUNTS, TRAIN_OWNERS,
                                   TRAIN_VALUES, TRAIN_PLACES, SEED_TRAIN)
    dev, ddev, _ = build_split(DEV_COUNTS, DEV_OWNERS, DEV_VALUES,
                               DEV_PLACES, SEED_DEV)
    want_train = sum(TRAIN_COUNTS.values())
    want_dev = sum(DEV_COUNTS.values())
    assert len(train) == want_train, (len(train), want_train)
    assert len(dev) == want_dev, (len(dev), want_dev)
    write_jsonl(os.path.join(args.out, "train.jsonl"), train)
    write_jsonl(os.path.join(args.out, "dev.jsonl"), dev)
    block = sorted(set(mine + [w for vs in THING_VALUES.values()
                               for w in vs]))
    json.dump({"block": block},
              open(os.path.join(args.out, "pools.json"), "w"))
    bs, bt, _ = stats_of(train)
    ds, dt, _ = stats_of(dev)
    stats = {"train": len(train), "dev": len(dev),
             "train_by_status": dict(bs), "train_by_tag": dict(bt),
             "dev_by_status": dict(ds), "dev_by_tag": dict(dt),
             "drops_train": dtrain, "drops_dev": ddev}
    json.dump(stats, open(os.path.join(args.out, "stats.json"), "w"),
              indent=1, sort_keys=True)
    print(json.dumps(stats, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
# __END__
