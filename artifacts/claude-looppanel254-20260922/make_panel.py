"""Loop wording panel 254 (blind writer). Holds the items by hand, writes panel.jsonl
deterministically and runs the self-checks from the spec. All names are fictional.

Run from the repo root:  python3 artifacts/claude-looppanel254-20260922/make_panel.py
"""
import json, re, sys
from pathlib import Path

OUT = Path(__file__).resolve().parent / "panel.jsonl"

# One fixed alias list per relation.
REL = {
    "city": ["lives_in", "home_city", "residence", "location", "home", "lives", "current_city", "town"],
    "dog": ["dog_name", "pet_dog", "has_dog", "pet"],
    "cat": ["cat_name", "pet_cat", "has_cat", "pet"],
    "parrot": ["parrot_name", "pet_parrot", "pet"],
    "tortoise": ["tortoise_name", "pet_tortoise", "pet"],
    "sister": ["sibling", "twin_sister", "older_sister"],
    "brother": ["sibling"],
    "mother": ["mom", "mum", "mam", "mother_name"],
    "father": ["dad", "father_name"],
    "spouse": ["wife", "husband", "married_to", "partner"],
    "friend": ["best_friend", "pal", "buddy"],
    "neighbour": ["neighbor"],
    "cousin": [],
    "uncle": [],
    "dentist": [],
    "job": ["occupation", "profession", "works_as", "work", "role", "career"],
    "workplace": ["employer", "works_at", "work_place", "company", "workplace_name", "works_for",
                  "teaches_at", "place_of_work", "work_location"],
    "birthplace": ["born_in", "place_of_birth", "birth_city", "birth_place", "birth_town"],
    "hometown": ["grew_up_in", "home_town", "childhood_home", "raised_in", "from"],
    "language": ["speaks", "native_language", "first_language", "languages", "mother_tongue"],
    "favorite_food": ["favourite_food", "fav_food", "favorite_dish", "favourite_dish", "favorite_meal"],
    "favorite_color": ["favourite_color", "favourite_colour", "favorite_colour", "fav_color",
                       "fav_colour", "colour", "color"],
    "boss": ["manager", "supervisor", "works_for"],
    "teacher": ["tutor"],
    "school": ["attends", "studies_at", "goes_to"],
    "son": ["child", "kid", "children"],
    "daughter": ["child", "kid", "children"],
    "hobby": ["pastime", "hobbies", "interest"],
}

FAMILIES = [("teach_varied", 30), ("ask_varied", 30), ("both_varied", 20), ("casual", 20),
            ("backwards", 15), ("chain", 15), ("no_save", 20), ("control", 10)]

ITEMS = []


def I(fam, setup, turn, followup, gold, answer, must_not, feature, tags=(), kind=None):
    ITEMS.append(dict(fam=fam, setup=list(setup), turn=turn, followup=followup, gold=list(gold),
                      answer=answer, must_not=list(must_not), feature=feature, tags=list(tags), kind=kind))


# ---------------- teach_varied (30, T) ----------------
T = "teach_varied"
I(T, [], "Brannoc works as a locksmith.", "What is Brannoc's job?", [("Brannoc", "job", "locksmith")], "locksmith", [], "verb 'works as'")
I(T, [], "Ilse Marrow teaches at Pinecrest School.", "What is Ilse Marrow's workplace?", [("Ilse Marrow", "workplace", "Pinecrest School")], "Pinecrest School", [], "verb 'teaches at'")
I(T, [], "My cousin Fenwick moved to Larkspur last spring.", "What is Fenwick's city?", [("me", "cousin", "Fenwick"), ("Fenwick", "city", "Larkspur")], "Larkspur", [], "'my cousin X' + 'moved to' + time phrase", ["two"])
I(T, [], "Odalys grew up in Tarnhollow.", "What is Odalys's hometown?", [("Odalys", "hometown", "Tarnhollow")], "Tarnhollow", [], "verb 'grew up in'")
I(T, [], "I have a dog called Bramble.", "What is my dog?", [("me", "dog", "Bramble")], "Bramble", [], "'I have a dog called'")
I(T, [], "My cat's name is Marzipan.", "What is my cat?", [("me", "cat", "Marzipan")], "Marzipan", [], "'my cat's name is'")
I(T, [], "Corvin is my neighbour and he's a firefighter.", "What is Corvin's job?", [("me", "neighbour", "Corvin"), ("Corvin", "job", "firefighter")], "firefighter", [], "inverted relative + pronoun job", ["pron", "two"])
I(T, [], "Petra Lindqvist Oyelaran speaks Finnish.", "What is Petra Lindqvist Oyelaran's language?", [("Petra Lindqvist Oyelaran", "language", "Finnish")], "Finnish", [], "3-word name + verb 'speaks'")
I(T, [], "Nessa Pryor is a pilot and she lives in Orlow.", "What is Nessa Pryor's city?", [("Nessa Pryor", "job", "pilot"), ("Nessa Pryor", "city", "Orlow")], "Orlow", [], "'is a JOB' + pronoun 'lives in'", ["pron", "two"])
I(T, [], "Dorrit was born in Sallowgate.", "What is Dorrit's birthplace?", [("Dorrit", "birthplace", "Sallowgate")], "Sallowgate", [], "verb 'was born in'")
I(T, [], "Halvard is married to Ysolde.", "Who is Halvard's wife?", [("Halvard", "spouse", "Ysolde")], "Ysolde", [], "'is married to'")
I(T, [], "Merriam is Tobiah's older sister.", "Who is Tobiah's sister?", [("Tobiah", "sister", "Merriam")], "Merriam", [], "inverted 'X is Y's older sister'")
I(T, [], "Roasted parsnips are Lowen Achterberg's favourite food.", "What is Lowen Achterberg's favorite food?", [("Lowen Achterberg", "favorite_food", "Roasted parsnips")], "roasted parsnips", [], "inverted favourite, value first")
I(T, [], "I met Anouk yesterday; she's married to Gideon Vale.", "Who is Anouk's husband?", [("Anouk", "spouse", "Gideon Vale")], "Gideon Vale", [], "event clause + pronoun 'she's married to'", ["pron"])
I(T, [], "My sister Rosalind works at Holloway Clinic.", "What is Rosalind's workplace?", [("me", "sister", "Rosalind"), ("Rosalind", "workplace", "Holloway Clinic")], "Holloway Clinic", [], "'my sister X' + 'works at'", ["two"])
I(T, [], "Emrys and his brother Caddoc both live in Wenlow.", "What is Caddoc's city?", [("Emrys", "brother", "Caddoc"), ("Emrys", "city", "Wenlow"), ("Caddoc", "city", "Wenlow")], "Wenlow", [], "coordinated subjects + 'his brother'", ["pron", "two"])
I(T, [], "Pim Okonkwo-Hale is Saoirse's boss.", "Who is Saoirse's boss?", [("Saoirse", "boss", "Pim Okonkwo-Hale")], "Pim Okonkwo-Hale", [], "inverted 'X is Y's boss', hyphenated name")
I(T, [], "my mum is called gwendolyn", "Who is my mother?", [("me", "mother", "gwendolyn")], "gwendolyn", [], "'my mum is called', no capitals", ["lower"])
I(T, [], "Arvid is a fisherman and he has a daughter named Linnea.", "Who is Arvid's daughter?", [("Arvid", "job", "fisherman"), ("Arvid", "daughter", "Linnea")], "Linnea", [], "'is a JOB' + 'he has a daughter named'", ["pron", "two"])
I(T, [], "Thessaly's got a son, Bram.", "Who is Thessaly's son?", [("Thessaly", "son", "Bram")], "Bram", [], "'has got a son, X'")
I(T, [], "Kestrel Adeyemi is a vet; he works at Mossbank Animal Hospital.", "What is Kestrel Adeyemi's workplace?", [("Kestrel Adeyemi", "job", "vet"), ("Kestrel Adeyemi", "workplace", "Mossbank Animal Hospital")], "Mossbank Animal Hospital", [], "semicolon + pronoun 'works at'", ["pron", "two"])
I(T, [], "I work as a translator.", "What is my job?", [("me", "job", "translator")], "translator", [], "first person 'I work as'")
I(T, [], "I was born in Quenby.", "What is my birthplace?", [("me", "birthplace", "Quenby")], "Quenby", [], "first person 'I was born in'")
I(T, [], "I grew up speakng Welsh.", "What is my language?", [("me", "language", "Welsh")], "Welsh", [], "'grew up speaking' with typo", ["typo"])
I(T, [], "Marisol Quint is my dentist. She lives in Farrowdale.", "What is Marisol Quint's city?", [("me", "dentist", "Marisol Quint"), ("Marisol Quint", "city", "Farrowdale")], "Farrowdale", [], "two sentences, second with 'She'", ["pron", "two"])
I(T, [], "Liesl is married to Ambrose and she works as a piano teacher.", "What is Liesl's job?", [("Liesl", "spouse", "Ambrose"), ("Liesl", "job", "piano teacher")], "piano teacher", [], "'married to' + pronoun 'works as'", ["pron", "two"])
I(T, [], "Dagny likes green best of all colours.", "What is Dagny's favorite color?", [("Dagny", "favorite_color", "green")], "green", [], "'likes V best of all colours'")
I(T, [], "Ferris took up birdwatching as a hobby.", "What is Ferris's hobby?", [("Ferris", "hobby", "birdwatching")], "birdwatching", [], "'took up V as a hobby'")
I(T, [], "Anselm Brightwater is Yarrow's father; he's a carpenter.", "Who is Yarrow's father?", [("Yarrow", "father", "Anselm Brightwater"), ("Anselm Brightwater", "job", "carpenter")], "Anselm Brightwater", [], "inverted father + pronoun job", ["pron", "two"])
I(T, [], "Cosima lives in Brackenridge and she has a cat called Tuppence.", "What is Cosima's cat?", [("Cosima", "city", "Brackenridge"), ("Cosima", "cat", "Tuppence")], "Tuppence", [], "'lives in' + pronoun 'has a cat called'", ["pron", "two"])

# ---------------- ask_varied (30, A) ----------------
A = "ask_varied"
I(A, ["Brisa's job is potter."], "What does Brisa do for a living?", None, [("Brisa", "job", "potter")], "potter", [], "'do for a living'")
I(A, ["Maelor's workplace is Ridgeway Library.", "Maelor's job is archivist."], "Where does Maelor work?", None, [("Maelor", "workplace", "Ridgeway Library"), ("Maelor", "job", "archivist")], "Ridgeway Library", ["archivist"], "verb 'where does X work' with a job neighbour")
I(A, ["My dog is Marmalade."], "What's the name of my dog?", None, [("me", "dog", "Marmalade")], "Marmalade", [], "'the name of my dog'")
I(A, ["Juno Takahara's city is Bellcombe."], "Which town does Juno Takahara live in?", None, [("Juno Takahara", "city", "Bellcombe")], "Bellcombe", [], "'which town does X live in'")
I(A, ["Oriel's sister is Primrose."], "Do you know who Oriel's sister is?", None, [("Oriel", "sister", "Primrose")], "Primrose", [], "'do you know who ... is'")
I(A, ["My mother is Hesper."], "Can you remind me what my mom's name is?", None, [("me", "mother", "Hesper")], "Hesper", [], "'remind me', mom for mother")
I(A, ["Caspian Rudd's birthplace is Ellsmere.", "Caspian Rudd's city is Tollmarsh."], "Where was Caspian Rudd born?", None, [("Caspian Rudd", "birthplace", "Ellsmere"), ("Caspian Rudd", "city", "Tollmarsh")], "Ellsmere", ["Tollmarsh"], "'where was X born' with a city neighbour")
I(A, ["Wilhelmina's language is Catalan."], "What language does Wilhelmina speak?", None, [("Wilhelmina", "language", "Catalan")], "Catalan", [], "verb 'speak'")
I(A, ["Tamsin Holt's hometown is Grayburn."], "Where did Tamsin Holt grow up?", None, [("Tamsin Holt", "hometown", "Grayburn")], "Grayburn", [], "'grow up'")
I(A, ["My cat is Ptolemy."], "what's my cat's nmae", None, [("me", "cat", "Ptolemy")], "Ptolemy", [], "lowercase, typo, no '?'", ["lower", "typo", "noq"])
I(A, ["Idris's boss is Carrow Finch."], "Who does Idris report to?", None, [("Idris", "boss", "Carrow Finch")], "Carrow Finch", [], "'report to'")
I(A, ["Leocadia's favorite food is dumplings."], "What does Leocadia like to eat most?", None, [("Leocadia", "favorite_food", "dumplings")], "dumplings", [], "'like to eat most'")
I(A, ["Bartholomew's wife is Clementine."], "Who is Bartholomew married to?", None, [("Bartholomew", "spouse", "Clementine")], "Clementine", [], "'married to'")
I(A, ["My friend is Solveig Maren."], "Who's my friend?", None, [("me", "friend", "Solveig Maren")], "Solveig Maren", [], "contraction who's + my")
I(A, ["Gideon's son is Tobin."], "Has Gideon got any kids?", None, [("Gideon", "son", "Tobin")], "Tobin", [], "'got any kids'")
I(A, ["Rosalie Achebe's school is Linden Hall."], "Which school does Rosalie Achebe go to?", None, [("Rosalie Achebe", "school", "Linden Hall")], "Linden Hall", [], "'go to'")
I(A, ["My job is paramedic."], "what do i do for work", None, [("me", "job", "paramedic")], "paramedic", [], "first person 'do for work', lowercase, no '?'", ["lower", "noq"])
I(A, ["My city is Harrowgate."], "where do i live", None, [("me", "city", "Harrowgate")], "Harrowgate", [], "first person 'where do I live', lowercase, no '?'", ["lower", "noq"])
I(A, ["Evander's father is Leopold Crane."], "Who's Evander's dad?", None, [("Evander", "father", "Leopold Crane")], "Leopold Crane", [], "dad for father")
I(A, ["Marguerite's hobby is pottery."], "What does Marguerite do for fun?", None, [("Marguerite", "hobby", "pottery")], "pottery", [], "'do for fun'")
I(A, ["Philippa's favorite color is violet."], "Which colour does Philippa like best?", None, [("Philippa", "favorite_color", "violet")], "violet", [], "'which colour ... like best'")
I(A, ["Thorne's brother is Ashby."], "What's Thorne's brother called?", None, [("Thorne", "brother", "Ashby")], "Ashby", [], "'what's ... called'")
I(A, ["My language is Basque."], "what langauge do i speak", None, [("me", "language", "Basque")], "Basque", [], "first person verb, typo, no '?'", ["lower", "typo", "noq"])
I(A, ["Ignatius Pell's dog is Rufus."], "Tell me the name of Ignatius Pell's dog", None, [("Ignatius Pell", "dog", "Rufus")], "Rufus", [], "imperative 'tell me', no '?'", ["noq"])
I(A, ["Seraphine's daughter is Odette."], "What's the name of Seraphine's daughter", None, [("Seraphine", "daughter", "Odette")], "Odette", [], "'the name of', no '?'", ["noq"])
I(A, ["My sister is Imogen."], "Remind me, who is my sister?", None, [("me", "sister", "Imogen")], "Imogen", [], "'remind me,' prefix")
I(A, ["Aurelio's workplace is Cobble Street Bakery."], "Where's Aurelio employed", None, [("Aurelio", "workplace", "Cobble Street Bakery")], "Cobble Street Bakery", [], "'employed', no '?'", ["noq"])
I(A, ["My brother is Lachlan."], "do you remeber my brother's name", None, [("me", "brother", "Lachlan")], "Lachlan", [], "'do you remember', typo, lowercase, no '?'", ["lower", "typo", "noq"])
I(A, ["Winslow's birthplace is Fairhaven.", "Winslow's city is Stonebridge."], "In which town was Winslow born", None, [("Winslow", "birthplace", "Fairhaven"), ("Winslow", "city", "Stonebridge")], "Fairhaven", ["Stonebridge"], "'in which town was X born', no '?', city neighbour", ["noq"])
I(A, ["Delphine's mother is Agathe.", "Delphine's father is Remy."], "Who is Delphine's mum?", None, [("Delphine", "mother", "Agathe"), ("Delphine", "father", "Remy")], "Agathe", ["Remy"], "mum for mother, father neighbour")

# ---------------- both_varied (20, T+A) ----------------
B = "both_varied"
I(B, ["Ravenna works as a glassblower."], "What does Ravenna do?", None, [("Ravenna", "job", "glassblower")], "glassblower", [], "'works as' then 'what does X do'")
I(B, ["I have a parrot called Captain Biscuit."], "What's my parrot's name?", None, [("me", "parrot", "Captain Biscuit")], "Captain Biscuit", [], "'I have a parrot called' then 'my parrot's name'")
I(B, ["Oswin moved to Kellingford in March."], "Which city does Oswin live in now?", None, [("Oswin", "city", "Kellingford")], "Kellingford", [], "'moved to' + time then 'live in now'")
I(B, ["My uncle Ferdinand teaches at Moorgate College."], "Where does Ferdinand teach?", None, [("me", "uncle", "Ferdinand"), ("Ferdinand", "workplace", "Moorgate College")], "Moorgate College", [], "'my uncle X teaches at' then 'where does X teach'")
I(B, ["Anika Sorensen grew up in Wexmoor."], "Where's Anika Sorensen from originally?", None, [("Anika Sorensen", "hometown", "Wexmoor")], "Wexmoor", [], "'grew up in' then 'from originally'")
I(B, ["Bellamy is married to Rhiannon."], "Who's Bellamy's wife?", None, [("Bellamy", "spouse", "Rhiannon")], "Rhiannon", [], "'married to' then 'wife'")
I(B, ["Tavish was born in Norrow Point."], "Where was Tavish born?", None, [("Tavish", "birthplace", "Norrow Point")], "Norrow Point", [], "'born in' then 'where was X born'")
I(B, ["Cressida speaks fluent Icelandic."], "What language does Cressida speak?", None, [("Cressida", "language", "Icelandic")], "Icelandic", [], "'speaks fluent V' then verb question")
I(B, ["I work at Saltmarsh Brewery."], "where do i wrok", None, [("me", "workplace", "Saltmarsh Brewery")], "Saltmarsh Brewery", [], "'I work at' then lowercase typo question, no '?'", ["lower", "typo", "noq"])
I(B, ["Linus Farraday is a surgeon."], "What's Linus Farraday's job?", None, [("Linus Farraday", "job", "surgeon")], "surgeon", [], "'is a JOB' then \"what's X's job\"")
I(B, ["My daughter is called Elowen."], "What's my daughter's name?", None, [("me", "daughter", "Elowen")], "Elowen", [], "'is called' then 'my daughter's name'")
I(B, ["Horatio has a tortoise named Sheldon."], "What's Horatio's tortoise called?", None, [("Horatio", "tortoise", "Sheldon")], "Sheldon", [], "'has a tortoise named' then 'called'")
I(B, ["Priya can't get enough of mushroom risotto; it's her favourite food."], "What's Priya's favourite food?", None, [("Priya", "favorite_food", "mushroom risotto")], "mushroom risotto", [], "value first, 'it's her favourite food'")
I(B, ["Casimir works for Delia Strand."], "Who is Casimir's manager?", None, [("Casimir", "boss", "Delia Strand")], "Delia Strand", [], "'works for PERSON' then 'manager'")
I(B, ["Mirabel, Jonah's twin sister, lives in Calder."], "Where does Jonah's sister live?", None, [("Jonah", "sister", "Mirabel"), ("Mirabel", "city", "Calder")], "Calder", [], "appositive teach then two-hop verb question")
I(B, ["I grew up in Pellowford."], "Where did I grow up?", None, [("me", "hometown", "Pellowford")], "Pellowford", [], "first person 'grew up in' both ways")
I(B, ["Zinnia Cole has been my best friend since school."], "Who's my best friend?", None, [("me", "friend", "Zinnia Cole")], "Zinnia Cole", [], "'has been my best friend since' then \"who's my best friend\"")
I(B, ["Barnaby's favourite colour has always been orange."], "What colour does Barnaby like most?", None, [("Barnaby", "favorite_color", "orange")], "orange", [], "'has always been' then 'like most'")
I(B, ["Esme and her husband Lorcan live in Tiverstone."], "Who is Esme's husband?", None, [("Esme", "spouse", "Lorcan"), ("Esme", "city", "Tiverstone"), ("Lorcan", "city", "Tiverstone")], "Lorcan", ["Tiverstone"], "coordinated subjects with 'her husband'")
I(B, ["Quentin is a chef at Harbourlight Grill."], "Which restaurant does Quentin work at?", None, [("Quentin", "job", "chef"), ("Quentin", "workplace", "Harbourlight Grill")], "Harbourlight Grill", [], "'a JOB at PLACE' then 'which restaurant'")

# ---------------- casual (20: 10 T, 10 A) ----------------
C = "casual"
I(C, [], "ok so my freind tobias lives in marlow", "What is Tobias's city?", [("me", "friend", "tobias"), ("tobias", "city", "marlow")], "marlow", [], "filler + typo + two facts", ["lower", "typo", "two"], "T")
I(C, [], "btw my favrite food is pancakes lol", "What is my favorite food?", [("me", "favorite_food", "pancakes")], "pancakes", [], "fillers + typo", ["lower", "typo"], "T")
I(C, [], "ivo works as a plumber btw", "What is Ivo's job?", [("ivo", "job", "plumber")], "plumber", [], "lowercase verb teach + filler", ["lower"], "T")
I(C, [], "my sisters name is ottilie", "Who is my sister?", [("me", "sister", "ottilie")], "ottilie", [], "missing apostrophe", ["lower"], "T")
I(C, [], "heres a fact: renata's dog is called waffles", "What is Renata's dog?", [("renata", "dog", "waffles")], "waffles", [], "missing apostrophe, 'is called'", ["lower"], "T")
I(C, [], "so basically ansel grew up in brixham and he speaks dutch", "What is Ansel's language?", [("ansel", "hometown", "brixham"), ("ansel", "language", "dutch")], "dutch", [], "filler + pronoun + two facts", ["lower", "pron", "two"], "T")
I(C, [], "my bosss name is dorian keel", "Who is my boss?", [("me", "boss", "dorian keel")], "dorian keel", [], "typo + missing apostrophe", ["lower", "typo"], "T")
I(C, [], "fyi clover teaches at wyeford school, she luvs it", "What is Clover's workplace?", [("clover", "workplace", "wyeford school")], "wyeford school", [], "filler + chat tail with typo", ["lower", "typo"], "T")
I(C, [], "umm my brother lives in ashcombe now, his names fergus", "What is Fergus's city?", [("me", "brother", "fergus"), ("fergus", "city", "ashcombe")], "ashcombe", [], "filler, name given after, pronoun, missing apostrophe", ["lower", "pron", "two"], "T")
I(C, [], "lol i just got a cat, hes calld noodle", "What is my cat?", [("me", "cat", "noodle")], "noodle", [], "filler, pronoun, typo", ["lower", "typo", "pron"], "T")
I(C, ["Wendeline's city is Crowhurst."], "wat town does wendeline live in", None, [("Wendeline", "city", "Crowhurst")], "Crowhurst", [], "typo + no '?'", ["lower", "typo", "noq"], "A")
I(C, ["My dog is Bosun."], "whats my dogs name again", None, [("me", "dog", "Bosun")], "Bosun", [], "missing apostrophes + 'again', no '?'", ["lower", "noq"], "A")
I(C, ["Rafferty's job is electrician."], "ok so wat does rafferty do for work", None, [("Rafferty", "job", "electrician")], "electrician", [], "filler + typo + no '?'", ["lower", "typo", "noq"], "A")
I(C, ["Honoria's brother is Cuthbert."], "who is honorias brother", None, [("Honoria", "brother", "Cuthbert")], "Cuthbert", [], "missing apostrophe, no '?'", ["lower", "noq"], "A")
I(C, ["My friend is Lysander Gray."], "btw whos my freind again lol", None, [("me", "friend", "Lysander Gray")], "Lysander Gray", [], "fillers + typo, no '?'", ["lower", "typo", "noq"], "A")
I(C, ["Sabine's language is Romansh."], "wich language does sabine speak?", None, [("Sabine", "language", "Romansh")], "Romansh", [], "typo", ["lower", "typo"], "A")
I(C, ["Maxence's workplace is Northgate Depot."], "where does maxence wrok", None, [("Maxence", "workplace", "Northgate Depot")], "Northgate Depot", [], "typo, no '?'", ["lower", "typo", "noq"], "A")
I(C, ["My mother is Perpetua."], "hey whats my moms name", None, [("me", "mother", "Perpetua")], "Perpetua", [], "greeting + missing apostrophes, no '?'", ["lower", "noq"], "A")
I(C, ["Leander's birthplace is Oxmoor."], "were was leander born", None, [("Leander", "birthplace", "Oxmoor")], "Oxmoor", [], "typo, no '?'", ["lower", "typo", "noq"], "A")
I(C, ["Juniper Vale's favorite color is saffron."], "juniper vales favrite colour?", None, [("Juniper Vale", "favorite_color", "saffron")], "saffron", [], "bare noun phrase question, typo, missing apostrophe", ["lower", "typo"], "A")

# ---------------- backwards (15, A) ----------------
K = "backwards"
I(K, ["Hollis's workplace is Brindle Foundry.", "Merritt's workplace is Coldharbour Yard."], "Who works at Brindle Foundry?", None, [("Hollis", "workplace", "Brindle Foundry"), ("Merritt", "workplace", "Coldharbour Yard")], "Hollis", ["Merritt"], "who works at PLACE", ["back"])
I(K, ["Oskar Venn's sister is Talitha.", "Talitha's sister is Maribel."], "Whose sister is Talitha?", None, [("Oskar Venn", "sister", "Talitha"), ("Talitha", "sister", "Maribel")], "Oskar Venn", ["Maribel"], "whose R is X; forward reading gives the distractor", ["back"])
I(K, ["Corliss's city is Pembry.", "Anwen's city is Dalby."], "Who lives in Pembry?", None, [("Corliss", "city", "Pembry"), ("Anwen", "city", "Dalby")], "Corliss", ["Anwen"], "who lives in PLACE", ["back"])
I(K, ["Fitzroy's boss is Delphina.", "Delphina's boss is Marchetti."], "Who has Delphina as a boss?", None, [("Fitzroy", "boss", "Delphina"), ("Delphina", "boss", "Marchetti")], "Fitzroy", ["Marchetti"], "'who has X as a R'", ["back"])
I(K, ["Gunnar's dog is Pickle.", "Rosamund's dog is Tansy."], "Who owns a dog called Pickle?", None, [("Gunnar", "dog", "Pickle"), ("Rosamund", "dog", "Tansy")], "Gunnar", ["Rosamund"], "'who owns a dog called'", ["back"])
I(K, ["Ezra's teacher is Vespera Lint.", "Vespera Lint's teacher is Hobart."], "Who is Vespera Lint a teacher to?", None, [("Ezra", "teacher", "Vespera Lint"), ("Vespera Lint", "teacher", "Hobart")], "Ezra", ["Hobart"], "'who is X a R to'", ["back"])
I(K, ["Aldric's boss is Perrin."], "Who is Aldric the boss of?", None, [("Aldric", "boss", "Perrin")], None, ["Perrin"], "'who is X the R of'; honest answer is don't know", ["back"])
I(K, ["Saffi's mother is Grizel."], "Whose mother is Saffi?", None, [("Saffi", "mother", "Grizel")], None, ["Grizel"], "whose R is X; honest answer is don't know", ["back"])
I(K, ["Laurel's job is architect.", "Bede's job is architect.", "Cato's job is baker."], "Who works as an architect", None, [("Laurel", "job", "architect"), ("Bede", "job", "architect"), ("Cato", "job", "baker")], "Laurel; Bede", ["Cato"], "who works as JOB, two answers, no '?'", ["back", "noq"])
I(K, ["Emmeline's birthplace is Carrow Bay.", "Emmeline's city is Lymfield."], "Who was born in Carrow Bay?", None, [("Emmeline", "birthplace", "Carrow Bay"), ("Emmeline", "city", "Lymfield")], "Emmeline", ["Lymfield"], "who was born in PLACE", ["back"])
I(K, ["Ottilie's father is Magnus Rhee.", "Magnus Rhee's father is Aurelian."], "Magnus Rhee is whose father", None, [("Ottilie", "father", "Magnus Rhee"), ("Magnus Rhee", "father", "Aurelian")], "Ottilie", ["Aurelian"], "'X is whose R', no '?'", ["back", "noq"])
I(K, ["Percival's daughter is Clemency."], "Whose daughter is Percival?", None, [("Percival", "daughter", "Clemency")], None, ["Clemency"], "whose R is X; honest answer is don't know", ["back"])
I(K, ["Iona's language is Gaelic.", "Hamish's language is Norwegian."], "who speaks gaelic", None, [("Iona", "language", "Gaelic"), ("Hamish", "language", "Norwegian")], "Iona", ["Hamish"], "who speaks LANGUAGE, lowercase, no '?'", ["back", "lower", "noq"])
I(K, ["Thaddeus's son is Kit.", "Kit's son is Jory."], "Kit is the son of who?", None, [("Thaddeus", "son", "Kit"), ("Kit", "son", "Jory")], "Thaddeus", ["Jory"], "'X is the R of who'", ["back"])
I(K, ["Marisa's teacher is Ulric."], "Who is Marisa the teacher of?", None, [("Marisa", "teacher", "Ulric")], None, ["Ulric"], "'who is X the R of'; honest answer is don't know", ["back"])

# ---------------- chain (15, A) ----------------
H = "chain"
I(H, ["Gilda's brother is Rowan.", "Rowan's city is Fernhill."], "Where does Gilda's brother live?", None, [("Gilda", "brother", "Rowan"), ("Rowan", "city", "Fernhill")], "Fernhill", [], "verb two-hop")
I(H, ["My friend is Caius Dorn.", "Caius Dorn's job is falconer."], "what does my friend do for a living", None, [("me", "friend", "Caius Dorn"), ("Caius Dorn", "job", "falconer")], "falconer", [], "my-chain, lowercase, no '?'", ["lower", "noq"])
I(H, ["Mireille's boss is Oberon.", "Oberon's dog is Ruckus."], "What's the name of Mireille's boss's dog?", None, [("Mireille", "boss", "Oberon"), ("Oberon", "dog", "Ruckus")], "Ruckus", [], "stacked possessive")
I(H, ["My sister is Anneliese.", "Anneliese's workplace is Glenholm Hospital."], "Where does my sister work?", None, [("me", "sister", "Anneliese"), ("Anneliese", "workplace", "Glenholm Hospital")], "Glenholm Hospital", [], "my-chain verb")
I(H, ["Hugo's wife is Signe.", "Signe's birthplace is Kilwinter."], "Where was Hugo's wife born?", None, [("Hugo", "spouse", "Signe"), ("Signe", "birthplace", "Kilwinter")], "Kilwinter", [], "'where was X's R born'")
I(H, ["Tiberius's father is Crispin.", "Crispin's language is Latvian."], "Which language does Tiberius's dad speak", None, [("Tiberius", "father", "Crispin"), ("Crispin", "language", "Latvian")], "Latvian", [], "dad for father, no '?'", ["noq"])
I(H, ["My brother is Declan.", "Declan's cat is Sprocket."], "whats my brothers cat called", None, [("me", "brother", "Declan"), ("Declan", "cat", "Sprocket")], "Sprocket", [], "my-chain, missing apostrophes, no '?'", ["lower", "noq"])
I(H, ["Marlowe's teacher is Ingrid Solberg.", "Ingrid Solberg's hometown is Ravensmoor."], "Where did Marlowe's teacher grow up?", None, [("Marlowe", "teacher", "Ingrid Solberg"), ("Ingrid Solberg", "hometown", "Ravensmoor")], "Ravensmoor", [], "'grow up' two-hop")
I(H, ["Petronella's daughter is Isaura.", "Isaura's job is geologist."], "What does Petronella's daughter work as?", None, [("Petronella", "daughter", "Isaura"), ("Isaura", "job", "geologist")], "geologist", [], "'work as' two-hop")
I(H, ["My mother is Philomena.", "Philomena's city is Wrenfield."], "Which city is my mum living in these days?", None, [("me", "mother", "Philomena"), ("Philomena", "city", "Wrenfield")], "Wrenfield", [], "my-chain, mum, 'these days'")
I(H, ["Casper's friend is Juniper Oak.", "Juniper Oak's favorite food is tamales."], "What food does Casper's friend like best?", None, [("Casper", "friend", "Juniper Oak"), ("Juniper Oak", "favorite_food", "tamales")], "tamales", [], "'like best' two-hop")
I(H, ["Anatole's son is Remus.", "Remus's school is Kingsbarrow School."], "Which school does Anatole's boy attend?", None, [("Anatole", "son", "Remus"), ("Remus", "school", "Kingsbarrow School")], "Kingsbarrow School", [], "boy for son, 'attend'")
I(H, ["Bettina's husband is Florian.", "Florian's boss is Magda Kerr."], "Who does Bettina's husband work for", None, [("Bettina", "spouse", "Florian"), ("Florian", "boss", "Magda Kerr")], "Magda Kerr", [], "'work for' two-hop, no '?'", ["noq"])
I(H, ["My friend is Ottoline.", "Ottoline's brother is Lysandro."], "Does my friend have a brother?", None, [("me", "friend", "Ottoline"), ("Ottoline", "brother", "Lysandro")], "Lysandro", [], "my-chain yes/no that should name the brother")
I(H, ["Evadne's workplace is Salt Row Press.", "Salt Row Press's city is Hexham."], "Which city does Evadne work in?", None, [("Evadne", "workplace", "Salt Row Press"), ("Salt Row Press", "city", "Hexham")], "Hexham", [], "person->place->city")

# ---------------- no_save (20) ----------------
N = "no_save"
I(N, ["Rhodri's city is Ellanby."], "So Rhodri lives in Carfax now?", None, [("Rhodri", "city", "Ellanby")], None, ["Carfax"], "statement-shaped question")
I(N, [], "Talia works at Hemlock Press, right?", None, [], None, ["Hemlock Press"], "tag question")
I(N, [], "If Dunstan moved to Coldwater, would he be happier?", None, [], None, ["Coldwater"], "hypothetical")
I(N, [], "Someone told me Ophira's brother is Leif.", None, [], None, ["Leif"], "hearsay")
I(N, ["Bronwen's job is nurse."], "Bronwen doesn't have a dog.", None, [("Bronwen", "job", "nurse")], None, [], "negation, no value")
I(N, [], "Castor might move to Lindqvist Harbour next year.", None, [], None, ["Lindqvist Harbour"], "plan")
I(N, [], "I bumped into Perpetua and Fenella at the market today.", None, [], None, [], "chit-chat with names")
I(N, ["My city is Oldcastle."], "I'm thinking about moving to Brightwell.", None, [("me", "city", "Oldcastle")], None, ["Brightwell"], "first person plan")
I(N, [], "What if Lucan's sister were called Aveline?", None, [], None, ["Aveline"], "hypothetical question")
I(N, [], "Apparently Jessamy grew up in Porthkennack, but I'm not sure.", None, [], None, ["Porthkennack"], "hearsay with doubt")
I(N, [], "Gregor isn't a dentist anymore.", None, [], None, ["dentist"], "negation")
I(N, [], "Ondine speaks Hungarian?", None, [], None, ["Hungarian"], "statement-shaped question")
I(N, [], "My neighbour said that Viggo's wife is Rosalind Marsh.", None, [], None, ["Rosalind Marsh"], "hearsay")
I(N, ["Tamsin Reed's workplace is Oakhurst Bank."], "Tamsin Reed hopes to work at Pellingham Studios one day.", None, [("Tamsin Reed", "workplace", "Oakhurst Bank")], None, ["Pellingham Studios"], "plan / wish")
I(N, [], "I don't have a cat.", None, [], None, [], "first person negation")
I(N, [], "Wouldn't it be funny if Barnabas's dog was called Sir Wiggles?", None, [], None, ["Sir Wiggles"], "hypothetical")
I(N, [], "Leopold and I had lunch yesterday, it was lovely.", None, [], None, [], "chit-chat with a name")
I(N, ["Delyth's city is Aberfal."], "Delyth never lived in Morwenstow.", None, [("Delyth", "city", "Aberfal")], None, ["Morwenstow"], "negation")
I(N, [], "maybe my sister will name her baby clementine", None, [], None, ["clementine"], "first person plan, lowercase", ["lower"])
I(N, [], "Isn't Hawthorn's birthplace Selkirk Cove?", None, [], None, ["Selkirk Cove"], "negative question")

# ---------------- control (10) ----------------
Z = "control"
I(Z, [], "Oriane's city is Gillsworth.", "What is Oriane's city?", [("Oriane", "city", "Gillsworth")], "Gillsworth", [], "plain teach", [], "T")
I(Z, ["Benedick's job is tailor."], "What is Benedick's job?", None, [("Benedick", "job", "tailor")], "tailor", [], "plain ask", [], "A")
I(Z, [], "My dog is Barnacle.", "What is my dog?", [("me", "dog", "Barnacle")], "Barnacle", [], "plain first-person teach", [], "T")
I(Z, ["Rosina's brother is Aldous."], "Who is Rosina's brother?", None, [("Rosina", "brother", "Aldous")], "Aldous", [], "plain ask", [], "A")
I(Z, [], "Corentin's workplace is Mill Lane Forge.", "What is Corentin's workplace?", [("Corentin", "workplace", "Mill Lane Forge")], "Mill Lane Forge", [], "plain teach", [], "T")
I(Z, ["My job is carpenter."], "What is my job?", None, [("me", "job", "carpenter")], "carpenter", [], "plain first-person ask", [], "A")
I(Z, [], "Valentina Ash's language is Greek.", "What is Valentina Ash's language?", [("Valentina Ash", "language", "Greek")], "Greek", [], "plain teach", [], "T")
I(Z, ["Ludo's birthplace is Wexcombe."], "What is Ludo's birthplace?", None, [("Ludo", "birthplace", "Wexcombe")], "Wexcombe", [], "plain ask", [], "A")
I(Z, [], "Hester's sister is Morwenna.", "Who is Hester's sister?", [("Hester", "sister", "Morwenna")], "Morwenna", [], "plain teach", [], "T")
I(Z, ["Anselm Gray's dog is Muffin."], "What is Anselm Gray's dog?", None, [("Anselm Gray", "dog", "Muffin")], "Muffin", [], "plain ask", [], "A")


FIRST = re.compile(r"\b(i|i'm|i've|me|my|mine|myself)\b", re.I)


def build():
    rows = []
    for n, it in enumerate(ITEMS, 1):
        tags = list(it["tags"])
        if FIRST.search(it["turn"]) and "user" not in tags:
            tags.append("user")
        note = it["feature"] + " [tags: " + ",".join(tags) + "]"
        if it["kind"]:
            note = it["kind"] + ": " + note
        rows.append({
            "id": f"l254-{n:03d}",
            "family": it["fam"],
            "setup": it["setup"],
            "turn": it["turn"],
            "followup": it["followup"],
            "gold_store": [{"subject": s, "relation": r, "relation_aliases": list(REL[r]), "value": v}
                           for (s, r, v) in it["gold"]],
            "gold_answer": it["answer"],
            "must_not": it["must_not"],
            "note": note,
        })
    return rows


def tags_of(row):
    return re.search(r"\[tags: ([^\]]*)\]", row["note"]).group(1).split(",") if "[tags: " in row["note"] else []


def check(rows):
    errs = []
    # family counts and order
    exp = []
    for fam, n in FAMILIES:
        exp += [fam] * n
    if [r["family"] for r in rows] != exp:
        errs.append("family counts/order wrong: " + str({f: sum(r["family"] == f for r in rows) for f, _ in FAMILIES}))
    turns = [r["turn"] for r in rows]
    if len(set(turns)) != len(turns):
        errs.append("duplicate turn")
    TEACH = {"teach_varied"}
    for r in rows:
        text = " ".join(r["setup"] + [r["turn"]] + ([r["followup"]] if r["followup"] else [])).lower()
        kind = r["note"].split(":")[0] if r["family"] in ("casual", "control") else None
        teach_scored = r["family"] in TEACH or kind == "T"
        if teach_scored and not r["followup"]:
            errs.append(r["id"] + " teach-scored without followup")
        if not teach_scored and r["followup"] is not None:
            errs.append(r["id"] + " followup on non-teach item")
        if r["family"] in ("casual", "control") and kind not in ("T", "A"):
            errs.append(r["id"] + " casual/control note must start with T: or A:")
        for g in r["gold_store"]:
            for k in ("subject", "value"):
                if g[k] != "me" and g[k].lower() not in text:
                    errs.append(f"{r['id']} gold {k} {g[k]!r} not in dialog")
            if g["relation"] not in REL:
                errs.append(r["id"] + " unknown relation")
        if r["gold_answer"]:
            pool = " ".join(r["setup"]).lower()
            vals = {x.lower() for g in r["gold_store"] for x in (g["subject"], g["value"])}
            for p in r["gold_answer"].split(";"):
                p = p.strip().lower()
                if p not in vals and p not in pool:
                    errs.append(f"{r['id']} gold_answer part {p!r} not in gold_store/setup")
        if r["family"] == "no_save" and r["gold_answer"] is not None:
            errs.append(r["id"] + " no_save must have null gold_answer")
        t = tags_of(r)
        if "lower" in t and r["turn"] != r["turn"].lower():
            errs.append(r["id"] + " tagged lower but has capitals")
        if "noq" in t and "?" in r["turn"]:
            errs.append(r["id"] + " tagged noq but has '?'")
        if r["family"] == "casual" and r["turn"] != r["turn"].lower():
            errs.append(r["id"] + " casual turn not lowercase")
    q = {
        "lowercase": sum(r["turn"] == r["turn"].lower() for r in rows),
        "typo": sum("typo" in tags_of(r) for r in rows),
        "noq": sum("noq" in tags_of(r) for r in rows),
        "pron": sum("pron" in tags_of(r) for r in rows),
        "user": sum(bool(FIRST.search(r["turn"])) for r in rows),
        "two_fact": sum("two" in tags_of(r) for r in rows),
    }
    need = {"lowercase": 25, "typo": 15, "noq": 20, "pron": 10, "user": 20, "two_fact": 10}
    for k, v in need.items():
        if q[k] < v:
            errs.append(f"quota {k} {q[k]} < {v}")
    rels = sorted({g["relation"] for r in rows for g in r["gold_store"]})
    if len(rels) < 12:
        errs.append("fewer than 12 relations")
    return errs, q, rels


if __name__ == "__main__":
    rows = build()
    errs, q, rels = check(rows)
    with open(OUT, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("rows", len(rows), "quotas", q)
    print("relations", len(rels), rels)
    if errs:
        print("CHECK FAILED")
        for e in errs:
            print(" ", e)
        sys.exit(1)
    print("CHECKS OK")
