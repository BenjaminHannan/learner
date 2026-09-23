#!/usr/bin/env python3
"""Rung 1 of design 43: the FRAME TABLE, re-targeted from
`scripts/fable_talker24_dialogues_frames.py` (friend/gift/prize/charm toy world) to the
LISTENING schema of `scripts/fable_listening_english.py`.

Frames only: a data table plus construction tags.  No sampling, no model, no notebook.
Nothing here is edited by any other file; the split lives in `fable_ears45_data.py`.

PLACEHOLDERS
  {S}        the subject name                                   -> role S
  {OWNER}    possessive owner chain, e.g. "Mira", "Mira's mom"  -> roles S, H0, H1...
  {OWNER_OF} of-style owner chain, e.g. "the mom of Mira"       -> roles S, H0, H1...
  {R}        the FINAL relation wording                         -> role H<last>
  {V}        a literal value                                    -> role V
  {O}        a person-name value                                -> role V
  {OLD}      the value a correction names out loud              -> no role
  {A} {C}    nickname and the canonical name                    -> roles A, C
  {G}        a gibberish token                                  -> no role
  {S2} {R2} {V2} {O2}   the second/third fact of a multi trap   -> no role
  {N}        a leftover name that no slot explains              -> no role
  {P}        a bare pronoun subject                             -> no role

A frame's `kind` says which relation wordings may fill {R}:
  'noun'  noun-like wording ("mother", "favourite colour", "teacher")
  'verb'  verb-like wording ("lives in", "works at", "was born in")
  'any'   either
A frame's `value` says what fills {V}/{O}: 'literal', 'person', 'none'.

`far=True` marks a construction that is held out WHOLE (panel T-far, E.3): its tag never
appears in TRAIN.
"""
from __future__ import annotations

# (construction_tag, template)  --  order is part of the sealed identity, never re-sort.

TEACH_NOUN = [
    ("poss_be", "{S}'s {R} is {V}."),
    ("poss_be", "{S}'s {R} is {V} now."),
    ("poss_be", "{S}'s {R} is {V}, by the way."),
    ("poss_be", "{S}'s {R} happens to be {V}."),
    ("poss_colon", "{S}'s {R}: {V}."),
    ("poss_dash", "{S}'s {R} - {V}."),
    ("of_be", "the {R} of {S} is {V}."),
    ("of_be", "the {R} for {S} is {V}."),
    ("has_as", "{S} has {V} as a {R}."),
    ("has_as", "{S} has {V} for a {R}."),
    ("topic", "about {S}: the {R} is {V}."),
    ("topic", "about {S}, the {R} is {V}."),
    ("topic", "as for {S}, the {R} is {V}."),
    ("topic", "speaking of {S}, the {R} is {V}."),
    ("frame_tell", "i want you to know that {S}'s {R} is {V}."),
    ("frame_tell", "you should know that {S}'s {R} is {V}."),
    ("frame_tell", "just so you know, {S}'s {R} is {V}."),
    ("frame_tell", "let me tell you: {S}'s {R} is {V}."),
    ("frame_note", "remember that {S}'s {R} is {V}."),
    ("frame_note", "note that {S}'s {R} is {V}."),
    ("frame_note", "please write down that {S}'s {R} is {V}."),
    ("frame_note", "write this down: {S}'s {R} is {V}."),
    ("frame_note", "add this: {S}'s {R} is {V}."),
    ("frame_note", "keep this in mind: {S}'s {R} is {V}."),
    ("frame_new", "here is a fact: {S}'s {R} is {V}."),
    ("frame_new", "new fact: {S}'s {R} is {V}."),
    ("frame_new", "one more: {S}'s {R} is {V}."),
    ("frame_new", "small update: {S}'s {R} is {V}."),
    ("first_person", "my {R} is {V}."),
    ("first_person", "i want you to know my {R} is {V}."),
    ("first_person", "my {R}: {V}."),
    ("second_person", "your {R} is {V}."),
    ("second_person", "note that your {R} is {V}."),
    ("texting", "{S}'s {R} {V}"),
    ("texting", "{S}: {R} {V}"),
    ("inverted_be", "{V} is {S}'s {R}."),
    ("inverted_be", "{V} is the {R} of {S}."),
    ("cleft", "it is {V} that is {S}'s {R}.", True),
    ("passive_named", "{V} was named as {S}'s {R}.", True),
    ("there_is", "there is a {R} for {S}: it is {V}.", True),
]

TEACH_VERB = [
    ("svo", "{S} {R} {V}."),
    ("svo", "{S} {R} {V} now."),
    ("svo", "{S} {R} {V}, just so you know."),
    ("svo_topic", "about {S}: {S} {R} {V}."),
    ("svo_frame", "i want you to know that {S} {R} {V}."),
    ("svo_frame", "you should know that {S} {R} {V}."),
    ("svo_frame", "just so you know, {S} {R} {V}."),
    ("svo_note", "remember that {S} {R} {V}."),
    ("svo_note", "note that {S} {R} {V}."),
    ("svo_note", "please write down that {S} {R} {V}."),
    ("svo_note", "write this down: {S} {R} {V}."),
    ("svo_new", "new fact: {S} {R} {V}."),
    ("svo_new", "here is a fact: {S} {R} {V}."),
    ("svo_new", "small update: {S} {R} {V}."),
    ("first_person", "i {R} {V}.", False, "vbase"),
    ("first_person", "just so you know, i {R} {V}.", False, "vbase"),
    ("texting", "{S} {R} {V}"),
    ("texting", "{S} {R} {V} btw"),
    ("svo_and", "{S} {R} {V} these days."),
    ("svo_and", "{S} {R} {V} at the moment."),
    ("cleft_verb", "it is {V} that {S} {R}.", True),
    ("relclause_v", "the one who {R} {V} is {S}.", True),
]

TEACH_LINK = [
    ("poss_be", "{S}'s {R} is {O}."),
    ("poss_be", "{S}'s {R} is {O} now."),
    ("poss_be", "{S}'s {R} happens to be {O}."),
    ("poss_colon", "{S}'s {R}: {O}."),
    ("poss_dash", "{S}'s {R} - {O}."),
    ("of_be", "the {R} of {S} is {O}."),
    ("of_be", "the {R} for {S} is {O}."),
    ("has_as", "{S} has {O} as a {R}."),
    ("topic", "about {S}: the {R} is {O}."),
    ("topic", "about {S}, the {R} is {O}."),
    ("topic", "as for {S}, the {R} is {O}."),
    ("frame_tell", "i want you to know that {S}'s {R} is {O}."),
    ("frame_tell", "you should know that {S}'s {R} is {O}."),
    ("frame_tell", "just so you know, {S}'s {R} is {O}."),
    ("frame_note", "remember that {S}'s {R} is {O}."),
    ("frame_note", "note that {S}'s {R} is {O}."),
    ("frame_note", "please write down that {S}'s {R} is {O}."),
    ("frame_note", "add this: {S}'s {R} is {O}."),
    ("frame_new", "new fact: {S}'s {R} is {O}."),
    ("frame_new", "here is a fact: {S}'s {R} is {O}."),
    ("frame_new", "small update: {S}'s {R} is {O}."),
    ("first_person", "my {R} is {O}."),
    ("second_person", "your {R} is {O}."),
    ("texting", "{S}'s {R} {O}"),
    ("inverted_be", "{O} is {S}'s {R}."),
    ("inverted_be", "{O} is the {R} of {S}."),
    ("cleft", "it is {O} who is {S}'s {R}.", True),
    ("there_is", "there is a {R} for {S}: it is {O}.", True),
]

CORRECT_NOUN = [
    ("actually", "actually, {S}'s {R} is {V}."),
    ("actually", "actually {S}'s {R} is {V}."),
    ("actually", "actually, the {R} of {S} is {V}."),
    ("sorry", "sorry, {S}'s {R} is {V}."),
    ("sorry", "sorry, i was wrong: {S}'s {R} is {V}."),
    ("correction", "correction: {S}'s {R} is {V}."),
    ("correction", "a correction: {S}'s {R} is {V}."),
    ("correction", "small correction: {S}'s {R} is {V}."),
    ("i_meant", "i meant that {S}'s {R} is {V}."),
    ("i_meant", "i meant to say that {S}'s {R} is {V}."),
    ("i_meant", "what i meant was that {S}'s {R} is {V}."),
    ("not_old", "{S}'s {R} is not {OLD}, it is {V}."),
    ("not_old", "{S}'s {R} is not {OLD}; it is {V}."),
    ("not_old", "{S}'s {R} is not {OLD} but {V}."),
    ("not_old", "actually, {S}'s {R} is not {OLD}, it is {V}."),
    ("not_old", "sorry, {S}'s {R} is not {OLD}, it is {V}."),
    ("not_old", "{S}'s {R} is no longer {OLD}, it is {V}."),
    ("not_old", "correction: {S}'s {R} is not {OLD}, it is {V}."),
    ("comma_not", "{S}'s {R} is {V}, not {OLD}."),
    ("comma_not", "the {R} of {S} is {V}, not {OLD}."),
    ("first_person", "actually, my {R} is {V}."),
    ("first_person", "sorry, my {R} is {V}."),
    ("second_person", "actually, your {R} is {V}."),
    ("wait", "wait, {S}'s {R} is {V}."),
    ("wait", "wait, i was wrong: {S}'s {R} is {V}."),
    ("actually_topic", "actually, about {S}: the {R} is {V}."),
    ("actually_of", "actually, {V} is {S}'s {R}."),
    ("i_meant_cleft", "i meant it is {V} that is {S}'s {R}.", True),
]

CORRECT_VERB = [
    ("actually", "actually, {S} {R} {V}."),
    ("actually", "actually {S} {R} {V}."),
    ("sorry", "sorry, {S} {R} {V}."),
    ("sorry", "sorry, i was wrong: {S} {R} {V}."),
    ("correction", "correction: {S} {R} {V}."),
    ("correction", "small correction: {S} {R} {V}."),
    ("i_meant", "i meant that {S} {R} {V}."),
    ("i_meant", "i meant to say that {S} {R} {V}."),
    ("not_old", "actually, {S} no longer {R} {OLD}, {S} {R} {V}."),
    ("comma_not", "{S} {R} {V}, not {OLD}."),
    ("wait", "wait, {S} {R} {V}."),
    ("first_person", "actually, i {R} {V}.", False, "vbase"),
    ("first_person", "sorry, i {R} {V}.", False, "vbase"),
    ("actually_now", "actually {S} {R} {V} now."),
    ("i_meant_cleft", "i meant it is {V} that {S} {R}.", True),
]

CORRECT_LINK = [
    ("actually", "actually, {S}'s {R} is {O}."),
    ("actually", "actually {S}'s {R} is {O}."),
    ("actually", "actually, the {R} of {S} is {O}."),
    ("sorry", "sorry, {S}'s {R} is {O}."),
    ("sorry", "sorry, i was wrong: {S}'s {R} is {O}."),
    ("correction", "correction: {S}'s {R} is {O}."),
    ("correction", "small correction: {S}'s {R} is {O}."),
    ("i_meant", "i meant that {S}'s {R} is {O}."),
    ("i_meant", "what i meant was that {S}'s {R} is {O}."),
    ("not_old", "{S}'s {R} is not {OLD}, it is {O}."),
    ("not_old", "{S}'s {R} is not {OLD} but {O}."),
    ("not_old", "actually, {S}'s {R} is not {OLD}, it is {O}."),
    ("not_old", "{S}'s {R} is no longer {OLD}, it is {O}."),
    ("comma_not", "{S}'s {R} is {O}, not {OLD}."),
    ("wait", "wait, {S}'s {R} is {O}."),
    ("first_person", "actually, my {R} is {O}."),
    ("second_person", "actually, your {R} is {O}."),
    ("actually_of", "actually, {O} is {S}'s {R}.", True),
]

ASK_NOUN = [
    ("wh_poss", "what is {OWNER}'s {R}?"),
    ("wh_poss", "what's {OWNER}'s {R}?"),
    ("wh_poss", "what is {OWNER}'s {R} again?"),
    ("wh_poss", "what is {OWNER}'s {R}, then?"),
    ("wh_of", "what is the {R} of {OWNER_OF}?"),
    ("wh_of", "what is the {R} for {OWNER_OF}?"),
    ("aux_know", "do you know {OWNER}'s {R}?"),
    ("aux_know", "do you know what {OWNER}'s {R} is?"),
    ("aux_know", "do you know the {R} of {OWNER_OF}?"),
    ("aux_know", "do you remember {OWNER}'s {R}?"),
    ("aux_can", "can you tell me {OWNER}'s {R}?"),
    ("aux_can", "can you tell me what {OWNER}'s {R} is?"),
    ("aux_can", "could you tell me {OWNER}'s {R}?"),
    ("imperative", "tell me {OWNER}'s {R}."),
    ("imperative", "tell me what {OWNER}'s {R} is."),
    ("imperative", "remind me of {OWNER}'s {R}."),
    ("imperative", "look up {OWNER}'s {R} for me."),
    ("wonder", "i wonder what {OWNER}'s {R} is."),
    ("wonder", "i forget what {OWNER}'s {R} is."),
    ("wonder", "i want to know {OWNER}'s {R}."),
    ("anyidea", "any idea what {OWNER}'s {R} is?"),
    ("anyidea", "any idea about {OWNER}'s {R}?"),
    ("topicq", "about {OWNER}: what is the {R}?"),
    ("topicq", "about {OWNER}, what is the {R}?"),
    ("topicq", "as for {OWNER}, what is the {R}?"),
    ("fragmentq", "{OWNER}'s {R}?"),
    ("fragmentq", "and {OWNER}'s {R}?"),
    ("whatabout", "what about {OWNER}'s {R}?"),
    ("whatabout", "how about {OWNER}'s {R}?"),
    ("first_person", "what is my {R}?"),
    ("second_person", "what is your {R}?"),
    ("texting", "{OWNER}'s {R}"),
    ("wh_relclause", "what is the {R} that {OWNER} has?", True),
    ("whose", "whose {R} is it, for {OWNER_OF}?", True),
]

ASK_VERB3 = [
    ("wh_where", "where {OWNER} {R}?"),
    ("aux_know_v", "do you know where {OWNER} {R}?"),
    ("aux_know_v", "do you remember where {OWNER} {R}?"),
    ("aux_can_v", "can you tell me where {OWNER} {R}?"),
    ("aux_can_v", "could you tell me where {OWNER} {R}?"),
    ("imperative_v", "tell me where {OWNER} {R}."),
    ("imperative_v", "remind me where {OWNER} {R}."),
    ("wonder_v", "i wonder where {OWNER} {R}."),
    ("wonder_v", "i forget where {OWNER} {R}."),
    ("anyidea_v", "any idea where {OWNER} {R}?"),
    ("topicq_v", "about {OWNER}: where {R} it?", True),
]

ASK_VBASE = [
    ("wh_does", "where does {OWNER} {R}?"),
    ("wh_does", "where does {OWNER} {R} again?"),
    ("wh_does", "where does {OWNER} {R}, then?"),
    ("aux_know_b", "do you know where {OWNER} does {R}?"),
    ("first_person_b", "where do i {R}?"),
    ("second_person_b", "where do you {R}?"),
    ("did_b", "where did {OWNER} {R}?"),
    ("does_far", "does {OWNER} {R} anywhere i know?", True),
]

ASK_LINK = [
    ("wh_poss", "who is {OWNER}'s {R}?"),
    ("wh_poss", "who's {OWNER}'s {R}?"),
    ("wh_poss", "who is {OWNER}'s {R} again?"),
    ("wh_poss", "who is {OWNER}'s {R}, then?"),
    ("wh_of", "who is the {R} of {OWNER_OF}?"),
    ("wh_of", "who is the {R} for {OWNER_OF}?"),
    ("aux_know", "do you know {OWNER}'s {R}?"),
    ("aux_know", "do you know who {OWNER}'s {R} is?"),
    ("aux_know", "do you know the {R} of {OWNER_OF}?"),
    ("aux_know", "do you remember {OWNER}'s {R}?"),
    ("aux_can", "can you tell me {OWNER}'s {R}?"),
    ("aux_can", "can you tell me who {OWNER}'s {R} is?"),
    ("aux_can", "could you tell me {OWNER}'s {R}?"),
    ("imperative", "tell me {OWNER}'s {R}."),
    ("imperative", "tell me who {OWNER}'s {R} is."),
    ("imperative", "remind me of {OWNER}'s {R}."),
    ("imperative", "look up {OWNER}'s {R} for me."),
    ("wonder", "i wonder who {OWNER}'s {R} is."),
    ("wonder", "i forget who {OWNER}'s {R} is."),
    ("wonder", "i want to know {OWNER}'s {R}."),
    ("anyidea", "any idea who {OWNER}'s {R} is?"),
    ("anyidea", "any idea about {OWNER}'s {R}?"),
    ("topicq", "about {OWNER}: who is the {R}?"),
    ("topicq", "about {OWNER}, who is the {R}?"),
    ("topicq", "as for {OWNER}, who is the {R}?"),
    ("fragmentq", "{OWNER}'s {R}?"),
    ("fragmentq", "and {OWNER}'s {R}?"),
    ("whatabout", "what about {OWNER}'s {R}?"),
    ("first_person", "who is my {R}?"),
    ("second_person", "who is your {R}?"),
    ("texting", "{OWNER}'s {R}"),
    ("wh_relclause", "who is the {R} that {OWNER} has?", True),
    ("whose", "whose {R} is it, for {OWNER_OF}?", True),
]

PERSON = [
    ("new_person", "{S} is someone i know."),
    ("new_person", "{S} is a person."),
    ("new_person", "new person: {S}."),
    ("new_person", "add a person: {S}."),
    ("new_person", "add {S} as a person."),
    ("new_person", "remember the person {S}."),
    ("new_person", "please remember {S} as a person."),
    ("new_person", "{S} is a new person for you."),
    ("new_person", "there is a person named {S}."),
    ("new_person", "i know a person named {S}."),
    ("new_person", "write down the person {S}."),
    ("new_person", "note the person {S}."),
    ("new_person", "a new person: {S}."),
    ("new_person", "keep {S} as a person."),
    ("texting", "new person {S}"),
    ("new_person_far", "it is {S} who is the new person.", True),
]

ALIAS = [
    ("call_x_y", "you can call {C} {A}."),
    ("call_x_y", "we call {C} {A}."),
    ("call_x_y", "everyone calls {C} {A}."),
    ("call_x_y", "please call {C} {A}."),
    ("call_x_y", "i call {C} {A}."),
    ("goes_by", "{C} goes by {A}."),
    ("goes_by", "{C} usually goes by {A}."),
    ("short_for", "{A} is short for {C}."),
    ("short_for", "{A} is {C} for short."),
    ("nickname_is", "{C}'s nickname is {A}."),
    ("nickname_is", "the nickname of {C} is {A}."),
    ("same_person", "{A} and {C} are the same person."),
    ("same_person", "{A} is the same person as {C}."),
    ("also_known", "{C} is also known as {A}."),
    ("also_known", "{C} is also called {A}."),
    ("frame_note", "note that {C} goes by {A}."),
    ("frame_note", "remember that we call {C} {A}."),
    ("frame_note", "write this down: {C} goes by {A}."),
    ("texting", "we call {C} {A}"),
    ("alias_far", "it is {A} that {C} goes by.", True),
]

FORGET = [
    ("forget_poss", "forget {S}'s {R}."),
    ("forget_poss", "please forget {S}'s {R}."),
    ("forget_poss", "just forget {S}'s {R}."),
    ("forget_of", "forget the {R} of {S}."),
    ("drop", "drop {S}'s {R}."),
    ("drop", "please drop {S}'s {R}."),
    ("remove", "remove {S}'s {R}."),
    ("remove", "please remove {S}'s {R}."),
    ("remove", "remove the {R} of {S}."),
    ("delete", "delete {S}'s {R}."),
    ("delete", "please delete {S}'s {R}."),
    ("clear", "clear {S}'s {R}."),
    ("clear", "clear out {S}'s {R}."),
    ("stop_keeping", "stop keeping {S}'s {R}."),
    ("first_person", "forget my {R}."),
    ("texting", "forget {S}'s {R}"),
    ("forget_far", "it is {S}'s {R} that you should forget.", True),
]

SMALLTALK = [
    ("greeting", "hi!"),
    ("greeting", "hello!"),
    ("greeting", "hey there."),
    ("greeting", "good morning."),
    ("greeting", "good evening."),
    ("greeting", "i am back."),
    ("howareyou", "how are you?"),
    ("howareyou", "how are you today?"),
    ("howareyou", "how is it going?"),
    ("howareyou", "are you ok?"),
    ("howareyou", "how was your day?"),
    ("mystate", "i am fine."),
    ("mystate", "i am tired today."),
    ("mystate", "i am happy today."),
    ("mystate", "i am hungry."),
    ("mystate", "i had a long day."),
    ("didtoday", "i went to the park today."),
    ("didtoday", "i read a book last night."),
    ("didtoday", "i played outside after lunch."),
    ("didtoday", "we had bread for dinner."),
    ("didtoday", "i cleaned my room today."),
    ("ilike", "i like dogs."),
    ("ilike", "i like the rain."),
    ("ilike", "i love the summer."),
    ("reaction", "that sounds fun."),
    ("reaction", "that is nice."),
    ("reaction", "that is funny."),
    ("reaction", "ok, thanks."),
    ("reaction", "thank you."),
    ("closing", "i have to go now."),
    ("closing", "talk to you later."),
    ("closing", "good night."),
    ("closing", "see you tomorrow."),
    ("weather", "it is raining here."),
    ("weather", "it is very sunny today."),
    ("smalltalk_far", "what a day it has been.", True),
]

# ------------------------------------------------------------------ traps: must write nothing
TRAP_NEGATION = [
    ("neg_verb", "{S} does not {R} {V}.", False, "vbase"),
    ("neg_verb", "{S} no longer {R} {V}.", False, "verb"),
    ("neg_noun", "{S}'s {R} is not {V}.", False, "noun"),
    ("neg_noun", "{S}'s {R} is not {V} any more.", False, "noun"),
    ("neg_noun", "the {R} of {S} is not {V}.", False, "noun"),
    ("neg_noun", "{S} does not have {V} as a {R}.", False, "noun"),
    ("neg_noun", "{S}'s {R} was never {V}.", False, "noun"),
    ("neg_link", "{S}'s {R} is not {O}.", False, "noun"),
    ("neg_link", "{S}'s {R} was never {O}.", False, "noun"),
    ("neg_far", "never is {S}'s {R} {V}.", True, "noun"),
]

TRAP_HYPO = [
    ("if_", "if {S} {R} {V}, that would be nice.", False, "verb"),
    ("if_", "if {S}'s {R} were {V}, i would be happy.", False, "noun"),
    ("if_", "if {S}'s {R} is {V}, tell me.", False, "noun"),
    ("suppose", "suppose {S}'s {R} is {V}.", False, "noun"),
    ("suppose", "suppose {S} {R} {V}.", False, "verb"),
    ("imagine", "imagine {S}'s {R} is {V}.", False, "noun"),
    ("imagine", "imagine {S} {R} {V}.", False, "verb"),
    ("if_link", "if {S}'s {R} were {O}, that would help.", False, "noun"),
    ("suppose_link", "suppose {S}'s {R} is {O}.", False, "noun"),
    ("hypo_far", "were {S}'s {R} {V}, i would know.", True, "noun"),
]

TRAP_HEARSAY = [
    ("said", "{S} said {S} {R} {V}.", False, "verb"),
    ("said", "{S} says {S}'s {R} is {V}.", False, "noun"),
    ("told_me", "{S} told me that {S}'s {R} is {V}.", False, "noun"),
    ("i_heard", "i heard {S}'s {R} is {V}.", False, "noun"),
    ("i_heard", "i heard {S} {R} {V}.", False, "verb"),
    ("according", "according to {S}, the {R} is {V}.", False, "noun"),
    ("claims", "{S} claims {S}'s {R} is {V}.", False, "noun"),
    ("said_link", "{S} said {S}'s {R} is {O}.", False, "noun"),
    ("told_me_link", "{S} told me that {S}'s {R} is {O}.", False, "noun"),
    ("hearsay_far", "rumour has it {S}'s {R} is {V}.", True, "noun"),
]

TRAP_STMTQ = [
    ("tag_q", "{S}'s {R} is {V}, right?", False, "noun"),
    ("tag_q", "{S}'s {R} is {V}, is it not?", False, "noun"),
    ("tag_q", "{S} {R} {V}, right?", False, "verb"),
    ("you_know", "you know {S}'s {R}, right?", False, "noun"),
    ("you_know", "you know where {S} {R}, right?", False, "verb3"),
    ("is_it", "is {S}'s {R} {V}?", False, "noun"),
    ("is_it", "is {S}'s {R} {O}?", False, "noun"),
    ("does_it", "does {S} {R} {V}?", False, "vbase"),
    ("stmtq_far", "{S}'s {R}: {V}, or am i wrong?", True, "noun"),
]

TRAP_LEFTOVER = [
    ("with_extra", "{S} {R} {V} with {N}.", False, "verb"),
    ("with_extra", "{S}'s {R} is {V} and {N}.", False, "noun"),
    ("with_extra", "{S} {R} {V} near {N}.", False, "verb"),
    ("and_extra", "{S}'s {R} is {V}, {N} too.", False, "noun"),
    ("and_extra", "{S} has {V} as a {R}, so does {N}.", False, "noun"),
    ("for_extra", "{S}'s {R} is {V} for {N}.", False, "noun"),
    ("leftover_far", "{N} aside, {S}'s {R} is {V}.", True, "noun"),
]

TRAP_MULTI = [
    ("and_two", "{S}'s {R} is {V} and {S2}'s {R2} is {V2}."),
    ("and_two", "{S}'s {R} is {V}, {S2}'s {R2} is {V2}."),
    ("and_two", "{S} {R} {V} and {S2} {R2} {V2}.", False, "verb"),
    ("also_two", "{S}'s {R} is {V}; also {S2}'s {R2} is {V2}."),
    ("write_two", "write down {S}'s {R} as {V} and {S2}'s {R2} as {V2}."),
    ("both_two", "both {S}'s {R} and {S2}'s {R2} are {V}."),
    ("ask_two", "what are {S}'s {R} and {S2}'s {R2}?"),
    ("three", "{S}'s {R} is {V}, {S2}'s {R2} is {V2}, and {O2}'s {R} is {V}."),
    ("multi_far", "two things: {S}'s {R} is {V}, plus {S2}'s {R2} is {V2}.", True),
]

UNSURE_GIBBERISH = [
    ("gibberish", "{G}"),
    ("gibberish", "{G} {G}."),
    ("gibberish", "what is {G}?"),
    ("gibberish", "{G} {G} {G}?"),
    ("gibberish", "tell me about {G}."),
    ("gibberish", "{G}, please."),
    ("gibberish", "i think {G}."),
    ("gibberish", "do you know {G}?"),
    ("gibberish", "{G}!"),
    ("gibberish", "{G} the {G} of {G}."),
    ("gibberish_far", "{G}? {G}!", True),
]

UNSURE_PRONOUN = [
    ("pronoun", "what is {P} {R}?"),
    ("pronoun", "who is {P} {R}?"),
    ("pronoun", "{P} {R} is {V}."),
    ("pronoun", "{P} {R} is {O}."),
    ("pronoun", "tell me {P} {R}."),
    ("pronoun", "do you know {P} {R}?"),
    ("pronoun", "what about {P} {R}?"),
    ("pronoun", "{P} {R}?"),
    ("pronoun", "i forget {P} {R}."),
    ("pronoun", "remind me of {P} {R}."),
    ("noowner", "the {R} is {V}."),
    ("noowner", "what is the {R}?"),
    ("noowner", "tell me the {R}."),
    ("noowner", "who is the {R}?"),
    ("pronoun_far", "of {P} {R}, what do you know?", True),
]

# family -> (rows, act, kind, value)
FAMILY_SPEC = {
    "teach.noun": (TEACH_NOUN, "teach", "noun", "literal"),
    "teach.verb": (TEACH_VERB, "teach", "verb", "literal"),
    "teach.link": (TEACH_LINK, "teach", "noun", "person"),
    "correct.noun": (CORRECT_NOUN, "correct", "noun", "literal"),
    "correct.verb": (CORRECT_VERB, "correct", "verb", "literal"),
    "correct.link": (CORRECT_LINK, "correct", "noun", "person"),
    "ask.noun": (ASK_NOUN, "ask", "noun", "none"),
    "ask.verb3": (ASK_VERB3, "ask", "verb3", "none"),
    "ask.vbase": (ASK_VBASE, "ask", "vbase", "none"),
    "ask.link": (ASK_LINK, "ask", "noun", "none"),
    "person": (PERSON, "person", "none", "none"),
    "alias": (ALIAS, "alias", "none", "none"),
    "forget": (FORGET, "forget", "noun", "none"),
    "smalltalk": (SMALLTALK, "smalltalk", "none", "none"),
    "trap.negation": (TRAP_NEGATION, "quote", "any", "literal"),
    "trap.hypo": (TRAP_HYPO, "quote", "any", "literal"),
    "trap.hearsay": (TRAP_HEARSAY, "quote", "any", "literal"),
    "trap.stmtq": (TRAP_STMTQ, "ask", "any", "literal"),
    "trap.leftover": (TRAP_LEFTOVER, "unsure", "any", "literal"),
    "trap.multi": (TRAP_MULTI, "multi", "noun", "literal"),
    "unsure.gibberish": (UNSURE_GIBBERISH, "unsure", "none", "none"),
    "unsure.pronoun": (UNSURE_PRONOUN, "unsure", "noun", "literal"),
}

OPENERS = [
    "ok, ", "so, ", "by the way, ", "hey, ", "right, ", "well, ", "oh, ",
    "listen, ", "um, ", "alright, ", "hmm, ", "btw ", "fyi ", "quick one: ",
    "one thing: ",
]

# Fifteen openers; E.3 holds out three.  The held-out three are chosen by the same hash
# rank rule as the frames, in fable_ears45_data.py.


class Frame:
    __slots__ = ("id", "family", "construction", "template", "far", "act", "kind", "value")

    def __init__(self, family, index, construction, template, far, act, kind, value):
        self.id = f"{family}.{index:03d}"
        self.family, self.construction, self.template = family, construction, template
        self.far, self.act, self.kind, self.value = far, act, kind, value

    def __repr__(self):
        return f"Frame({self.id!r}, {self.template!r})"


def build_frames():
    out = {}
    for family, (rows, act, kind_default, value) in FAMILY_SPEC.items():
        frames = []
        seen = set()
        for i, row in enumerate(rows):
            tag, template = row[0], row[1]
            far = bool(row[2]) if len(row) > 2 else False
            kind = row[3] if len(row) > 3 else kind_default
            if template in seen:
                raise ValueError(f"duplicate template in {family}: {template!r}")
            seen.add(template)
            frames.append(Frame(family, i, tag, template, far, act, kind, value))
        out[family] = frames
    return out


FRAMES = build_frames()
ALL_FRAMES = {f.id: f for fs in FRAMES.values() for f in fs}
