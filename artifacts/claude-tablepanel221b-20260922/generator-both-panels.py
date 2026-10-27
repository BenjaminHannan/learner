import json, os, collections
ROOT = "/Users/ben-hannan/Desktop/projects/beautiful-model/.claude/worktrees/card-experiment-handoff-7c5b27"

A, N = "answer", "abstain"
# (setup, question, expect, gold, clear, notes)
P1 = {
"named": [
 (["Tamsin Arlo's landlord is Petra Voss."], "Who is Tamsin Arlo's landlord?", A, "Petra Voss", True, ""),
 (["Dorian Kell's dentist is Maren Hask.", "Dorian Kell's hometown is Fennick."], "Who is Dorian Kell's dentist?", A, "Maren Hask", True, "distractor fact"),
 (["Juno Barrow's wedding anniversary is June 3."], "When is Juno Barrow's wedding anniversary?", A, "June 3", True, "multi-word relation"),
 (["Rafe Lindqvist's favorite color is teal."], "What is Rafe Lindqvist's favorite color?", A, "teal", True, ""),
 (["Orla Penhale's employer is Quillmark Foods."], "Who is Orla Penhale's employer?", A, "Quillmark Foods", True, ""),
 (["Casimir Oduya's blood type is O negative.", "Casimir Oduya's dentist is Ilse Varga."], "What is Casimir Oduya's blood type?", A, "O negative", True, "distractor fact"),
 (["Wren Ashdown's piano teacher is Holm Farrier."], "Who is Wren Ashdown's piano teacher?", A, "Holm Farrier", True, "multi-word relation"),
 (["Tollin Library's head librarian is Anneke Solt."], "Who is Tollin Library's head librarian?", A, "Anneke Solt", True, "subject is a place"),
 (["Mika Dunmore's best friend is Sol Carrow.", "Mika Dunmore's cousin is Fern Talley."], "Who is Mika Dunmore's best friend?", A, "Sol Carrow", True, "distractor fact"),
 (["Harlan Quist's phone number is 555-0142."], "What is Harlan Quist's phone number?", A, "555-0142", True, ""),
 (["Esme Tollaver's hometown is Grelling."], "What is Esme Tollaver's hometown?", A, "Grelling", True, ""),
 (["Ansel Brightwater's accountant is Nadia Pell.", "Ansel Brightwater's lawyer is Corin Vale."], "Who is Ansel Brightwater's lawyer?", A, "Corin Vale", True, "asks the second of two facts"),
 (["Talmoria's capital is Ostrel."], "What is Talmoria's capital?", A, "Ostrel", True, "subject is a country"),
 (["Pim Achterberg's favorite food is lentil soup."], "What is Pim Achterberg's favorite food?", A, "lentil soup", True, ""),
 (["Noor Halvik's manager is Teodor Bram.", "Liesel Brandt's manager is Oskar Fenn."], "Who is Noor Halvik's manager?", A, "Teodor Bram", True, "same relation for another person as distractor"),
],
"word_form": [
 (["Ivor Sandell's coach is Mirelle Dax."], "Who coaches Ivor Sandell?", A, "Mirelle Dax", True, "coach -> coaches"),
 (["Harrowgate Bakery's founding date is 1952."], "When was Harrowgate Bakery founded?", A, "1952", True, "founding date -> founded"),
 (["Selby Marr's graduation date is May 2019."], "When did Selby Marr graduate?", A, "May 2019", True, "graduation date -> graduate"),
 (["Fenwick Cafe's owner is Bram Okafor."], "Who owns Fenwick Cafe?", A, "Bram Okafor", True, "owner -> owns"),
 (["Juniper Hale's employer is Kestrel Freight."], "Where does Juniper Hale work?", A, "Kestrel Freight", True, "employer -> work"),
 (["Milo Varden's tutor is Agnes Pryor."], "Who tutors Milo Varden?", A, "Agnes Pryor", True, "tutor -> tutors"),
 (["Castell Theatre's director is Yusuf Brandel."], "Who directs Castell Theatre?", A, "Yusuf Brandel", True, "director -> directs"),
 (["Linnea Sorrow's birthplace is Marrowdale."], "Where was Linnea Sorrow born?", A, "Marrowdale", True, "birthplace -> born"),
 (["Otto Quenell's mentor is Priya Lanrow.", "Otto Quenell's manager is Des Hollin."], "Who mentors Otto Quenell?", A, "Priya Lanrow", True, "mentor -> mentors; distractor"),
 (["Rosalind Kerrow's residence is Ambleford."], "Where does Rosalind Kerrow live?", A, "Ambleford", True, "residence -> live"),
 (["Dalton Fisk's birth date is April 9, 1990."], "When was Dalton Fisk born?", A, "April 9, 1990", True, "birth date -> born"),
 (["Hollis Brenn's husband is Tobias Arne."], "Who is Hollis Brenn married to?", A, "Tobias Arne", True, "husband -> married to"),
 (["Saffron Lile's landlord is Egon Tarrow."], "Who does Saffron Lile rent from?", A, "Egon Tarrow", True, "landlord -> rent from"),
 (["Brisko Games's founder is Anya Petrel."], "Who founded Brisko Games?", A, "Anya Petrel", True, "founder -> founded"),
 (["Idris Monk's employer is Pell & Garrow."], "Who does Idris Monk work for?", A, "Pell & Garrow", True, "employer -> work for"),
],
"contractions_fillers": [
 (["Tamsin Holloway's dentist is Arvid Lund."], "Who's Tamsin Holloway's dentist?", A, "Arvid Lund", True, ""),
 (["Ivo Castellan's birthday is October 12."], "When's Ivo's birthday again?", A, "October 12", True, "first name only; only one Ivo in setup"),
 (["Sela Morrow's pet is Biscuit."], "What's Sela Morrow's pet called?", A, "Biscuit", True, ""),
 (["Dex Ormond's boss is Kira Vantes."], "so who's Dex Ormond's boss?", A, "Kira Vantes", True, "lowercase filler start"),
 (["Mabel Crane's favorite band is The Low Lanterns."], "What's Mabel Crane's favorite band, remind me?", A, "The Low Lanterns", True, "trailing filler"),
 (["Jonah Pike's vet is Hedda Moss."], "Um, who's Jonah Pike's vet?", A, "Hedda Moss", True, ""),
 (["Rowan Aske's hometown is Kilbrae.", "Rowan Aske's school is Kilbrae High."], "What's Rowan Aske's hometown again?", A, "Kilbrae", True, "distractor shares a word with the answer"),
 (["Petra Lindell's neighbor is Gus Arnott."], "Hey, who's Petra Lindell's neighbor?", A, "Gus Arnott", True, ""),
 (["Anouk Drey's email is anouk.drey@fernmail.test."], "What's Anouk Drey's email?", A, "anouk.drey@fernmail.test", True, ""),
 (["Callum Brisk's anniversary is August 20."], "When's Callum Brisk's anniversary?", A, "August 20", True, ""),
 (["Zora Hemming's roommate is Lise Carver."], "Who's Zora Hemming's roommate, do you know?", A, "Lise Carver", True, ""),
 (["Bertrand Oake's favorite movie is Salt Harbor."], "what's Bertrand Oake's favorite movie", A, "Salt Harbor", True, "no question mark, lowercase"),
 (["Nell Ferrant's doctor is Ruben Szell."], "Quick q, who's Nell Ferrant's doctor?", A, "Ruben Szell", True, ""),
 (["Kofi Andrade's gym is Ironleaf Fitness.", "Kofi Andrade's barber is Sami Ruel."], "What's Kofi Andrade's gym called?", A, "Ironleaf Fitness", True, "distractor"),
 (["Ivy Talbot's sister is Maude Talbot."], "Who's Ivy Talbot's sister, btw?", A, "Maude Talbot", True, "abbreviation filler"),
],
"of_form": [
 (["Tamara Voight's landlord is Emil Rusk."], "Who is the landlord of Tamara Voight?", A, "Emil Rusk", True, ""),
 (["Talvenia's capital is Mirebrook."], "What is the capital of Talvenia?", A, "Mirebrook", True, ""),
 (["Harrow & Finch's CEO is Delia Morcant."], "Who is the CEO of Harrow & Finch?", A, "Delia Morcant", True, ""),
 (["Oldmere School's principal is Fergus Tann."], "Who is the principal of Oldmere School?", A, "Fergus Tann", True, ""),
 (["Lark Street Clinic's address is 14 Lark Street."], "What is the address of Lark Street Clinic?", A, "14 Lark Street", True, ""),
 (["Bellhaven's mayor is Ottilie Grane.", "Bellhaven's population is 12,000."], "Who is the mayor of Bellhaven?", A, "Ottilie Grane", True, "distractor"),
 (["Seren Abbot's manager is Hugo Lark."], "Who's the manager of Seren Abbot?", A, "Hugo Lark", True, "contraction + of-form"),
 (["Cinder Owls's drummer is Pax Delaney."], "Who is the drummer of the Cinder Owls?", A, "Pax Delaney", True, "question adds 'the'"),
 (["Quarry Lane Bakery's owner is Imogen Rhys."], "Who is the owner of Quarry Lane Bakery?", A, "Imogen Rhys", True, ""),
 (["Marlow Tennant's birthday is March 2."], "What is the birthday of Marlow Tennant?", A, "March 2", True, "stilted but clear"),
 (["Veyra Station's opening date is 1911."], "What's the opening date of Veyra Station?", A, "1911", True, "multi-word relation"),
 (["Linden Park's architect is Soren Blythe."], "Who was the architect of Linden Park?", A, "Soren Blythe", True, "past tense 'was'"),
 (["Ember Isle's population is 3,400."], "What is the population of Ember Isle?", A, "3,400", True, ""),
 (["Coralie Dunne's doctor is Anton Beck.", "Coralie Dunne's dentist is Wim Hollis."], "Who is the dentist of Coralie Dunne?", A, "Wim Hollis", True, "must pick dentist not doctor"),
 (["Northgate Rovers's coach is Gideon Marsh."], "Who is the coach of Northgate Rovers?", A, "Gideon Marsh", True, ""),
],
"synonyms": [
 (["Hattie Crewe's doctor is Lionel Marsh."], "Who is Hattie Crewe's physician?", A, "Lionel Marsh", True, "doctor = physician"),
 (["Alder Voss's boss is Renata Coil."], "Who is Alder Voss's supervisor?", A, "Renata Coil", True, "boss = supervisor"),
 (["Mina Castor's residence is Wexley."], "What city does Mina Castor live in?", A, "Wexley", False, "residence ~ city; Wexley might be a town, so not fully determined"),
 (["Tomas Egret's mother tongue is Vellish."], "What is Tomas Egret's native language?", A, "Vellish", True, "mother tongue = native language"),
 (["Greta Holm's spouse is Arne Liss."], "Who is Greta Holm's husband?", A, "Arne Liss", False, "spouse -> husband assumes gender"),
 (["Ines Farrow's job is carpenter."], "What is Ines Farrow's occupation?", A, "carpenter", True, "job = occupation"),
 (["Leo Marchetti's date of birth is July 14, 1988."], "When is Leo Marchetti's birthday?", A, "July 14, 1988", True, "date of birth -> birthday; 'July 14' alone is also correct"),
 (["Oskar Lindgren's lawyer is Beatrix Hale."], "Who is Oskar Lindgren's attorney?", A, "Beatrix Hale", True, "lawyer = attorney"),
 (["Pia Sund's yoga teacher is Carmen Holt."], "Who is Pia Sund's yoga instructor?", A, "Carmen Holt", True, "teacher = instructor"),
 (["Barnaby Pratt's vet is Olga Tarn."], "Who is Barnaby Pratt's veterinarian?", A, "Olga Tarn", True, "vet = veterinarian"),
 (["Rhea Lamont's mobile number is 555-0199."], "What's Rhea Lamont's cell number?", A, "555-0199", True, "mobile = cell"),
 (["Kai Morland's company is Brightfen Labs."], "Who is Kai Morland's employer?", A, "Brightfen Labs", False, "'company' could mean one he owns"),
 (["Ottavio Grin's birthplace is Selmouth."], "What is Ottavio Grin's place of birth?", A, "Selmouth", True, "birthplace = place of birth"),
 (["Delphine Arkwright's GP is Samir Otten."], "Who is Delphine Arkwright's family doctor?", A, "Samir Otten", True, "GP = family doctor"),
 (["Finn Galloway's best mate is Rory Pask."], "Who is Finn Galloway's best friend?", A, "Rory Pask", True, "best mate = best friend"),
],
"traps": [
 (["Tovah Rennick's dentist is Ada Wrenfield."], "Who is Tovah Rennick's doctor?", N, None, True, "dentist stored, doctor asked"),
 (["Ilsa Morven's head coach is Dario Fenn.", "Ilsa Morven's assistant coach is Kit Oyelaran."], "Who is Ilsa Morven's coach?", N, None, False, "two partial matches; should abstain or ask which. A human might list both; single answer is wrong"),
 (["Bastian Crowe's landlord is Hedy Voll."], "Who is Marisol Tane's landlord?", N, None, True, "unknown person"),
 (["Anika Strand's boss is Leon Farris.", "Pieter Strand's dentist is Ola Vine."], "Who is Pieter Strand's boss?", N, None, True, "boss stored for a different Strand"),
 (["Garrick Holt's birthday is May 5."], "When is Garrick Holt's anniversary?", N, None, True, "birthday stored, anniversary asked"),
 (["Rosa Kimura's sister is Emi Kimura."], "Who is Rosa Kimura's brother?", N, None, True, "sister vs brother"),
 (["Orson Tewk's mother is Ruth Tewk."], "Who is Orson Tewk's father?", N, None, True, "mother vs father"),
 (["Lyra Beck's senior manager is Ted Arno.", "Lyra Beck's project manager is Sue Kaplan."], "Who is Lyra Beck's manager?", N, None, False, "two partial matches; single answer is wrong"),
 (["Colm Aherne's home phone is 555-0110.", "Colm Aherne's work phone is 555-0177."], "What's Colm Aherne's phone number?", N, None, False, "two partial matches; listing both is also acceptable to a human, picking one is wrong"),
 (["Delia Farrow's dentist is Iris Kent."], "Who is Delia Farrell's dentist?", N, None, True, "near-miss surname = unknown person"),
 (["Marek Juhl's employer is Dunmore Paints."], "Who is Marek Juhl's landlord?", N, None, True, "relation not stored"),
 (["My dentist is Paula Grey.", "Noah Selden's doctor is Vic Amari."], "Who is Noah Selden's dentist?", N, None, True, "dentist stored for the user, not Noah"),
 (["Hanne Solberg's birth city is Carrowmere."], "Where does Hanne Solberg live now?", N, None, True, "birth city is not current residence"),
 (["Wendell Ashe's ex-wife is Carla Ashe."], "Who is Wendell Ashe's wife?", N, None, True, "ex-wife is not wife"),
 (["Evie Lorne's cat is Pudding."], "What is Evie Lorne's dog called?", N, None, True, "cat vs dog"),
],
"user_facts": [
 (["My dentist is Hana Leroux."], "Who is my dentist?", A, "Hana Leroux", True, ""),
 (["My landlord is Silas Brenner.", "Tova Rannoch's landlord is Marta Quill."], "Who's my landlord?", A, "Silas Brenner", True, "same relation for another person as distractor"),
 (["My wedding anniversary is September 30."], "When is my wedding anniversary?", A, "September 30", True, ""),
 (["My sister is Clio Varga."], "Who is my sister?", A, "Clio Varga", True, ""),
 (["My favorite restaurant is Bramble & Salt."], "What's my favorite restaurant?", A, "Bramble & Salt", True, ""),
 (["My license plate is KRV 482."], "What's my license plate?", A, "KRV 482", True, ""),
 (["My gym is Summit Works.", "My dentist is Oren Fell."], "What's my gym called?", A, "Summit Works", True, "distractor"),
 (["My boss is Harriet Kowal."], "Who is my boss?", A, "Harriet Kowal", True, ""),
 (["My mother tongue is Dunnish."], "What is my native language?", A, "Dunnish", True, "synonym on a user fact"),
 (["My hometown is Pellory."], "What's my hometown again?", A, "Pellory", True, ""),
 (["My locker number is 217."], "What is my locker number?", A, "217", True, ""),
 (["My doctor is Yara Blum.", "Lukas Cato's doctor is Ines Rook."], "Who is my doctor?", A, "Yara Blum", True, "distractor"),
 (["My dentist is Nils Ekdahl."], "Who is my doctor?", N, None, True, "trap: dentist stored, doctor asked"),
 (["My wifi password is lanternfish42."], "What's my wifi password?", A, "lanternfish42", True, "fictional value"),
 (["My book club day is Thursday."], "What day is my book club?", A, "Thursday", True, "reworded"),
],
"yes_no": [
 (["Tamsin Orr's landlord is Ada Wrennet."], "Is Ada Wrennet Tamsin Orr's landlord?", A, "yes", True, ""),
 (["Hugo Brill's dentist is Lena Marsh."], "Is Kurt Adler Hugo Brill's dentist?", A, "no", True, "different dentist stored; one dentist assumed"),
 (["Frida Nygaard's hometown is Ostby."], "Is Frida Nygaard's hometown Ostby?", A, "yes", True, ""),
 (["Pax Merriman's employer is Gullwing Air."], "Does Pax Merriman work for Gullwing Air?", A, "yes", True, "word form"),
 (["Dora Kessel's birthday is June 8."], "Is Dora Kessel's birthday in July?", A, "no", True, "needs month comparison"),
 (["Eamon Ruddock's boss is Trina Waugh."], "Is Trina Waugh Eamon Ruddock's boss?", A, "yes", True, ""),
 (["Sunniva Lodge's coach is Ari Mendel."], "Does Ari Mendel coach Sunniva Lodge?", A, "yes", True, "word form"),
 (["My dentist is Olof Brandt."], "Is Olof Brandt my dentist?", A, "yes", True, "user fact"),
 (["My hometown is Crale."], "Is my hometown Dunmere?", A, "no", True, "user fact"),
 (["Jasper Trent's wife is Mirela Trent."], "Is Jasper Trent married to Mirela Trent?", A, "yes", True, "wife -> married to"),
 (["Kestrel Books's owner is Hal Pardew."], "Does Nora Pardew own Kestrel Books?", A, "no", False, "co-owner not ruled out; best answer no / not as far as I know"),
 (["Veda Olsen's cat is Marbles."], "Is Veda Olsen's cat called Marbles?", A, "yes", True, ""),
 (["Ruth Calder's doctor is Amos Kyle."], "Is Amos Kyle Ruth Calder's physician?", A, "yes", True, "synonym"),
 (["Ingrid Pale's manager is Olu Baker.", "Tess Hovland's manager is Rui Santos."], "Is Rui Santos Ingrid Pale's manager?", A, "no", True, "Rui is another person's manager"),
 (["Cyril Ambrose's favorite color is green."], "Is Cyril Ambrose's favorite colour blue?", A, "no", True, "British spelling in question"),
],
}

S, X = "save", "nosave"
EMP = ["employer", "workplace", "works at", "works for", "company", "work", "job"]
RES = ["residence", "home", "lives in", "city", "town", "location", "address", "hometown"]
BIRTH = ["birthplace", "place of birth", "born in", "birth city", "birth town", "hometown"]
SCHOOL = ["school", "university", "college", "alma mater", "studied at", "education"]
OCC = ["occupation", "job", "profession", "work", "role", "career", "trade", "works as"]
SPOUSE = ["spouse", "wife", "husband", "married to", "partner"]
TEAM = ["team", "club", "plays for"]
# (statement, expect, subject, relation_any, value, notes)
P2 = {
"verbs": [
 ("Marta Quellen works at Brindle Logistics.", S, "Marta Quellen", EMP, "Brindle Logistics", ""),
 ("Osric Dahl works for Pennant Insurance.", S, "Osric Dahl", EMP, "Pennant Insurance", ""),
 ("Lucia Farnham lives in Coldwater Bay.", S, "Lucia Farnham", RES, "Coldwater Bay", ""),
 ("Tobiah Rask was born in Elmsford.", S, "Tobiah Rask", BIRTH, "Elmsford", ""),
 ("Wynn Carradine studied at Ashcombe University.", S, "Wynn Carradine", SCHOOL, "Ashcombe University", ""),
 ("Priya Selwyn teaches at Hollin Grove Academy.", S, "Priya Selwyn", EMP + ["teaches at", "school"], "Hollin Grove Academy", ""),
 ("Dario Maske plays for the Greywater Hawks.", S, "Dario Maske", TEAM, "Greywater Hawks", "value with leading 'the' also fine"),
 ("Anja Korbel speaks Vellish.", S, "Anja Korbel", ["language", "languages", "speaks", "spoken language"], "Vellish", ""),
 ("Silas Wendt owns Juniper Lane Books.", S, "Silas Wendt", ["owns", "owner of", "business", "property", "shop", "store"], "Juniper Lane Books", "inverse (Juniper Lane Books, owner, Silas Wendt) is equally correct"),
 ("Hedda Brun coaches the Millbrook Otters.", S, "Hedda Brun", ["coaches", "coach of", "team", "team coached"], "Millbrook Otters", "inverse (Millbrook Otters, coach, Hedda Brun) is equally correct"),
 ("Fenella Okoro founded Tidewell Robotics.", S, "Fenella Okoro", ["founded", "company founded", "company", "founder of"], "Tidewell Robotics", "inverse (Tidewell Robotics, founder, Fenella Okoro) is equally correct"),
 ("Rufus Adair is married to Clementine Adair.", S, "Rufus Adair", SPOUSE, "Clementine Adair", "symmetric; reverse also correct"),
 ("Jem Tolliver lives on Orchard Row.", S, "Jem Tolliver", RES + ["street", "lives on"], "Orchard Row", "'on' instead of 'in'"),
],
"occupation": [
 ("Mara Holtby is a vet.", S, "Mara Holtby", OCC, "vet", "veterinarian also fine"),
 ("Ivo Kestner works as a nurse.", S, "Ivo Kestner", OCC, "nurse", ""),
 ("Talia Brenner is an architect.", S, "Talia Brenner", OCC, "architect", ""),
 ("Gus Pemberton is a retired firefighter.", S, "Gus Pemberton", OCC + ["former occupation", "former job"], "retired firefighter", "value 'firefighter' with retired noted also fine"),
 ("Oona Farquhar is a pastry chef.", S, "Oona Farquhar", OCC, "pastry chef", ""),
 ("Bram Castellan is a lawyer.", S, "Bram Castellan", OCC, "lawyer", ""),
 ("Selma Ruud is a dentist.", S, "Selma Ruud", OCC, "dentist", "'dentist' here is her job, not someone's dentist relation"),
 ("Hector Vale works as a bus driver.", S, "Hector Vale", OCC, "bus driver", ""),
 ("Nika Solberg is a high school math teacher.", S, "Nika Solberg", OCC, "high school math teacher", "'math teacher' or 'teacher' acceptable"),
 ("Arlo Pinnock is an electrician by trade.", S, "Arlo Pinnock", OCC, "electrician", ""),
 ("Fern Adeyemi is a software engineer at Loftwise.", S, "Fern Adeyemi", OCC, "software engineer", "second fact: (Fern Adeyemi, employer, Loftwise)"),
 ("Corin Mayhew does accounting for a living.", S, "Corin Mayhew", OCC, "accountant", "paraphrase; value 'accounting' also fine"),
],
"the_R_of_Y": [
 ("Nils Aberdale is the director of Glasshaven Museum.", S, "Glasshaven Museum", ["director", "head", "museum director"], "Nils Aberdale", ""),
 ("Petra Ilves is the mayor of Dunhollow.", S, "Dunhollow", ["mayor"], "Petra Ilves", ""),
 ("Omar Reyes-Kell is the owner of the Copper Kettle Diner.", S, "Copper Kettle Diner", ["owner", "proprietor"], "Omar Reyes-Kell", "hyphenated name"),
 ("Harriet Voss is the principal of Elmbridge Primary.", S, "Elmbridge Primary", ["principal", "head teacher", "headteacher", "head"], "Harriet Voss", ""),
 ("Ines Garrick is the CEO of Stillwater Energy.", S, "Stillwater Energy", ["CEO", "chief executive", "chief executive officer", "head", "boss"], "Ines Garrick", ""),
 ("Ruben Achter is the captain of the Kilnworth Falcons.", S, "Kilnworth Falcons", ["captain", "team captain"], "Ruben Achter", ""),
 ("Mireille Dufort is the landlord of Tova Renwick.", S, "Tova Renwick", ["landlord"], "Mireille Dufort", "person as Y"),
 ("Ashby is the capital of Norrland Vale.", S, "Norrland Vale", ["capital", "capital city"], "Ashby", ""),
 ("Keir Lomond is the coach of Bexley Harriers.", S, "Bexley Harriers", ["coach", "head coach", "manager"], "Keir Lomond", ""),
 ("Sunita Varma is the author of The Glass Orchard.", S, "The Glass Orchard", ["author", "writer", "written by"], "Sunita Varma", "Y is a book title starting with 'The'"),
 ("Willa Crane is the editor of the Harbourside Gazette.", S, "Harbourside Gazette", ["editor", "editor-in-chief", "chief editor"], "Willa Crane", ""),
 ("Pavel Orlov is the founder of Moth & Lantern.", S, "Moth & Lantern", ["founder", "founded by", "creator"], "Pavel Orlov", "ampersand in name"),
],
"a_R_of_Y": [
 ("Ada Wrenley is a friend of Tova Rask.", S, "Tova Rask", ["friend", "friends"], "Ada Wrenley", "one of possibly several friends"),
 ("Jonas Ekberg is a cousin of Lotte Ekberg.", S, "Lotte Ekberg", ["cousin", "cousins"], "Jonas Ekberg", ""),
 ("Mei Halloran is a colleague of Dev Patrick.", S, "Dev Patrick", ["colleague", "coworker", "co-worker", "colleagues"], "Mei Halloran", ""),
 ("Rolf Anker is a client of Sabine Morrell.", S, "Sabine Morrell", ["client", "customer", "clients"], "Rolf Anker", ""),
 ("Tess Marlowe is a student of Professor Ian Gault.", S, "Ian Gault", ["student", "pupil", "students"], "Tess Marlowe", "subject 'Professor Ian Gault' also fine"),
 ("Liam Castro is an uncle of Pia Castro.", S, "Pia Castro", ["uncle"], "Liam Castro", "'an'"),
 ("Karin Holt is a neighbor of Mateo Brisk.", S, "Mateo Brisk", ["neighbor", "neighbour", "neighbors"], "Karin Holt", ""),
 ("Otto Venn is a member of the Larkspur Chess Club.", S, "Larkspur Chess Club", ["member", "members"], "Otto Venn", "inverse (Otto Venn, club, Larkspur Chess Club) also correct"),
 ("Fiona Grady is a patient of Dr. Hal Osei.", S, "Hal Osei", ["patient", "patients"], "Fiona Grady", "inverse (Fiona Grady, doctor, Hal Osei) also correct"),
 ("Bex Tamura is an employee of Norrow Freight.", S, "Norrow Freight", ["employee", "staff", "worker", "employees"], "Bex Tamura", "inverse (Bex Tamura, employer, Norrow Freight) also correct"),
 ("Aurelio Pinto is a fan of the Redbank Comets.", S, "Redbank Comets", ["fan", "fans", "supporter"], "Aurelio Pinto", "inverse (Aurelio Pinto, favorite team, Redbank Comets) also correct"),
 ("Sadie Crum is a former teammate of Jo Ellery.", S, "Jo Ellery", ["former teammate", "teammate", "ex-teammate"], "Sadie Crum", "'former' should be kept if possible"),
],
"user": [
 ("I work at Veltrane.", S, "me", EMP, "Veltrane", "subject = the user (me/I/user)"),
 ("My sister is Ada Wrennick.", S, "me", ["sister", "sibling"], "Ada Wrennick", ""),
 ("I live in Tamsford.", S, "me", RES, "Tamsford", ""),
 ("I was born in Kellbridge.", S, "me", BIRTH, "Kellbridge", ""),
 ("My dentist is Dr. Rosa Imrie.", S, "me", ["dentist"], "Rosa Imrie", "'Dr. Rosa Imrie' also fine"),
 ("I'm a paramedic.", S, "me", OCC, "paramedic", ""),
 ("I speak Dunnish and Vellish.", S, "me", ["language", "languages", "speaks"], "Dunnish", "second fact: (me, language, Vellish)"),
 ("My dog's name is Pickle.", S, "me", ["dog", "dog's name", "pet", "pet's name", "dog name"], "Pickle", ""),
 ("I'm married to Theo Lark.", S, "me", SPOUSE, "Theo Lark", ""),
 ("I studied at Carrow College.", S, "me", SCHOOL, "Carrow College", ""),
 ("My birthday is November 2.", S, "me", ["birthday", "birth date", "date of birth"], "November 2", ""),
 ("I play for the Southmere Kestrels.", S, "me", TEAM, "Southmere Kestrels", ""),
 ("I drive a Kessler Alto.", S, "me", ["car", "vehicle", "drives"], "Kessler Alto", ""),
],
"tense_time": [
 ("Kim Ashgrove used to live in Norrby.", S, "Kim Ashgrove", ["former residence", "previous residence", "past residence", "used to live in", "lived in", "former home"], "Norrby", "past fact worth keeping, but must be marked as past; plain 'residence' would be wrong"),
 ("Lee Parrish now lives in Bergholt.", S, "Lee Parrish", RES, "Bergholt", "'now' marks current; save as residence (replacing any older one)"),
 ("Anya Frost will start at Merrow Bank next month.", X, None, [], None, "future plan, not yet true; storing employer now would be wrong. A 'future employer' note would be defensible, but default is nosave"),
 ("Joel Maddox was born in Farrowby in 1979.", S, "Joel Maddox", BIRTH, "Farrowby", "second fact: (Joel Maddox, birth year, 1979)"),
 ("Rhona Kitt currently works at Pinefold Studio.", S, "Rhona Kitt", EMP, "Pinefold Studio", "'currently' is fine"),
 ("Dmitri Sallow worked at Hesketh Mills until 2019.", S, "Dmitri Sallow", ["former employer", "previous employer", "past employer", "worked at", "former workplace"], "Hesketh Mills", "past only; plain 'employer' would be wrong"),
 ("Since March, Coraline Ebb has been living in Wexmoor.", S, "Coraline Ebb", RES, "Wexmoor", "time phrase at the front"),
 ("Theo Varga's old dentist was Mira Kell.", S, "Theo Varga", ["old dentist", "former dentist", "previous dentist", "ex-dentist"], "Mira Kell", "plain 'dentist' would be wrong"),
 ("Brynn Coley is moving to Saltmarsh next week.", X, None, [], None, "future move; not yet her residence"),
 ("Owain Price is still with Harrowgate Rail.", S, "Owain Price", EMP, "Harrowgate Rail", "'still with' = still employed there (most natural reading)"),
 ("Petra Owusu has lived in Calder Heights since 2010.", S, "Petra Owusu", RES, "Calder Heights", "present perfect = current"),
 ("Kim Hadley no longer works at Lumen Dairy.", X, None, [], None, "tells what is no longer true; storing employer would be wrong. 'former employer' would be defensible but default nosave"),
],
"traps": [
 ("Varnholm is a city of Talvenia.", X, None, [], None, "category statement, not a personal relation (brief's Lima/Peru style)"),
 ("Wexmoor is lovely in the spring.", X, None, [], None, "opinion"),
 ("I'm so tired of Hollin Ward's emails.", X, None, [], None, "feeling"),
 ("If Kim Ostrander lived in Farrowby, she'd be a lot happier.", X, None, [], None, "hypothetical"),
 ("Kim Ostrander doesn't live in Farrowby.", X, None, [], None, "negation"),
 ("who is Tova Renwick's landlord", X, None, [], None, "question without question mark"),
 ("where does Pell Harker work", X, None, [], None, "question without question mark"),
 ("My boss is basically a dragon lol", X, None, [], None, "joke; must not store boss=dragon"),
 ("Grelling is a town.", X, None, [], None, "category statement"),
 ("Maybe Dex Porter works at Cindervale, I'm not sure.", X, None, [], None, "speaker is unsure"),
 ("The Mayor of Dunhollow is such a good podcast.", X, None, [], None, "role title is part of a podcast name + opinion; must not store (Dunhollow, mayor, ...)"),
 ("I just finished The Doctor of Wexmoor, what a book!", X, None, [], None, "role title inside a book name; must not store (Wexmoor, doctor, ...)"),
 ("I wish my sister lived in Tamsford.", X, None, [], None, "wish, not fact"),
 ("tell me who owns Fenwick Cafe", X, None, [], None, "request, no fact"),
],
"harder": [
 ("She works at Coldharbour Press.", S, "Dagny Ruud", EMP, "Coldharbour Press", "previous sentence: 'Dagny Ruud moved here last spring.' 'She' = Dagny Ruud"),
 ("His dentist is Rhea Salk.", S, "Otis Brand", ["dentist"], "Rhea Salk", "previous sentence: 'Have you met Otis Brand?'"),
 ("My sister Ada Wrennick lives in Dunmere.", S, "Ada Wrennick", RES, "Dunmere", "appositive; also (me, sister, Ada Wrennick). Main-clause fact listed; the sister fact alone would also be an acceptable save"),
 ("Our neighbour, Gil Farris, teaches at Hollowmere College.", S, "Gil Farris", EMP + ["teaches at", "school"], "Hollowmere College", "appositive; also (me, neighbor, Gil Farris)"),
 ("Ines Morrow lives in Ketterby and works at Salt & Sparrow.", S, "Ines Morrow", RES, "Ketterby", "two facts; second: (Ines Morrow, employer, Salt & Sparrow)"),
 ("Tomas Weir's wife is Ada Weir and his son is Pip Weir.", S, "Tomas Weir", ["wife", "spouse", "married to", "partner"], "Ada Weir", "two facts; second: (Tomas Weir, son, Pip Weir)"),
 ("My boss, Rhiannon Tate, was born in Glenholm.", S, "Rhiannon Tate", BIRTH, "Glenholm", "appositive; also (me, boss, Rhiannon Tate)"),
 ("He plays for the Fenmoor Badgers.", S, "Lorcan Ivey", TEAM, "Fenmoor Badgers", "previous sentence: 'Lorcan Ivey is my new flatmate.'"),
 ("It was founded by Anya Petrell.", S, "Brisko Games", ["founder", "founded by", "creator"], "Anya Petrell", "previous sentence: 'Brisko Games is a small studio in Tamsford.'"),
 ("Both Rosa and Ilse Kimura work at Pennant Insurance.", S, "Rosa Kimura", EMP, "Pennant Insurance", "two facts; shared surname; second: (Ilse Kimura, employer, Pennant Insurance)"),
 ("Dr. Hana Leroux, who's my dentist, lives in Crale.", S, "Hana Leroux", RES, "Crale", "relative clause; also (me, dentist, Hana Leroux)"),
 ("Otto Venn, the guy from my book club, owns a bakery called Rye & Rise.", S, "Otto Venn", ["owns", "owner of", "business", "bakery", "shop"], "Rye & Rise", "appositive; inverse (Rye & Rise, owner, Otto Venn) also correct"),
],
}

def write(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

rows1, i = [], 0
for fam, items in P1.items():
    for setup, q, exp, gold, clear, notes in items:
        i += 1
        assert (exp == "abstain") == (gold is None)
        assert 1 <= len(setup) <= 4
        for s in setup:
            assert s.endswith(".") and (" is " in s) and ("'s " in s or s.startswith("My ")), s
        rows1.append({"id": f"q221b-{i:03d}", "family": fam, "setup": setup, "question": q,
                      "expect": exp, "gold": gold, "clear": clear, "notes": notes})
rows2, i = [], 0
for fam, items in P2.items():
    for st, exp, subj, rels, val, notes in items:
        i += 1
        assert (exp == "save") == (subj is not None and val is not None and len(rels) > 0)
        rows2.append({"id": f"t229-{i:03d}", "family": fam, "statement": st, "expect": exp,
                      "subject": subj, "relation_any": rels, "value": val, "notes": notes})
write(f"{ROOT}/artifacts/claude-tablepanel221b-20260922/panel.jsonl", rows1)
write(f"{ROOT}/artifacts/claude-teachpanel229-20260922/panel.jsonl", rows2)
print(len(rows1), collections.Counter(r["family"] for r in rows1),
      collections.Counter(r["expect"] for r in rows1), sum(not r["clear"] for r in rows1))
print(len(rows2), collections.Counter(r["family"] for r in rows2), collections.Counter(r["expect"] for r in rows2))
