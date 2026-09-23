# Held-out verifier cases for fixes 245-251. Fictional names only.
# kind: claim (fix says it handles; gold must appear), keep (must not change vs base),
#       trap (no stored value may appear; no write). gold=[] means a correct reply gives no stored value.
# Wrong value = any stored value (object side of a stored triple) appearing in the reply that is not in gold
#   and not in `allow` (names the question itself mentions are allowed).
import json, sys
C = []
def add(fix, i, kind, setup, q, gold, allow=(), note="", novel=False):
    C.append(dict(id=f"v{fix}-{i:02d}", fix=fix, kind=kind, setup=list(setup), question=q,
                  gold=list(gold), allow=list(allow), note=note, novel_wording=novel))

# ---------- 245 my <relation> ----------
A = ["My aunt is Mirelle.", "Mirelle's pet is Tobrin."]
add(245,1,"claim",A,"What is my aunt's pet?",["Tobrin"],["Mirelle"],"'What is' (not What's)",True)
add(245,2,"claim",["My grandfather is Oswin Garrow.","Oswin Garrow's doctor is Fenna Rusk."],"Who is my grandfather's doctor?",["Fenna Rusk"],["Oswin Garrow"],"2-word X, doctor",True)
add(245,3,"claim",["My nephew is Dallin.","Dallin's school is Brackenhurst."],"what is my nephew's school?",["Brackenhurst"],["Dallin"],"lowercase, school",True)
add(245,4,"claim",["My cousin is Vessa.","Vessa's employer is Quillon Works."],"Who is my cousin's employer?",["Quillon Works"],["Vessa"],"possessive employer",True)
add(245,5,"claim",["My mother is Ardith.","Ardith's city is Morrowdale."],"Hello, where does my mother live?",["Morrowdale"],["Ardith"],"greeting strip")
add(245,6,"claim",["My friend is Pethra.","Pethra's spouse is Gorran."],"Who is my friend married to?",["Gorran"],["Pethra"],"married to")
add(245,7,"claim",["My brother is Caddoc.","Caddoc's city is Wendlebury."],"Where does my brother live, please?",["Wendlebury"],["Caddoc"],"trailing please")
add(245,8,"claim",["My boss is Irla Venn.","Irla Venn's teacher is Morvid."],"Who is my boss's teacher?",["Morvid"],["Irla Venn"],"teacher",True)
add(245,9,"keep",["My sister is Wenna."],"Who is my sister?",["Wenna"],[],"Me166 form")
add(245,10,"keep",["My city is Harrowmere."],"What is my city?",["Harrowmere"],[],"Me166 own fact")
add(245,11,"keep",["My name is Aldric Penn."],"What is my name?",["Aldric Penn"],[],"name")
add(245,12,"keep",["My brother is Caddoc.","Caddoc's city is Wendlebury."],"Where does Caddoc live?",["Wendlebury"],[],"direct name")
add(245,13,"trap",A,"What is my aunt's school?",[],["Mirelle"],"untaught relation")
add(245,14,"trap",["My brother is Caddoc.","Caddoc's employer is Ferrow Mills."],"Who does my brother employ?",[],["Caddoc"],"direction flip")
add(245,15,"trap",["My sister is Wenna."],"Does my sister live in Tarnby?",[],["Wenna","Tarnby"],"must not write")
add(245,16,"trap",["My sister is Wenna.","Wenna's city is Tarnby."],"Where does my uncle live?",[],[],"no such relative")

add(245,17,"claim",["My uncle is Belmor.","Belmor's language is Tessic."],"What language does my uncle speak?",["Tessic"],["Belmor"],"language verb",True)
add(245,18,"claim",["My grandfather is Oswin Garrow.","Oswin Garrow's doctor is Fenna Rusk."],"Who is the doctor of my grandfather?",["Fenna Rusk"],["Oswin Garrow"],"the R of",True)
add(245,19,"claim",["My cousin is Vessa.","Vessa was born in Harrowdean."],"where was my cousin born?",["Harrowdean"],["Vessa"],"lower born")
add(245,20,"claim",["My nephew is Dallin Roke.","Dallin Roke's employer is Pellam Yards."],"Where does my nephew work?",["Pellam Yards"],["Dallin Roke"],"2-word X, where work")

# ---------- 246 mention walk (star entity, one hop) ----------
S = ["Keswin Tull is married to Arabel Moss.","Keswin Tull's city is Fallowick.","Keswin Tull's employer is Grenby Loom."]
add(246,1,"claim",S,"Who is Keswin Tull married to?",["Arabel Moss"],["Keswin Tull"],"star spouse")
add(246,2,"claim",S,"who's keswin tull married to?",["Arabel Moss"],["Keswin Tull"],"lower who's")
add(246,3,"claim",S,"Who employs Keswin Tull?",["Grenby Loom"],["Keswin Tull"],"employs")
add(246,4,"claim",["Odo is married to Merrit.","Odo's pet is Snib."],"Who is the partner of Odo?",["Merrit"],["Odo"],"partner of",True)
add(246,5,"claim",["Brisa is a citizen of Galdoria.","Brisa's city is Penhollow."],"Brisa is a citizen of which country?",["Galdoria"],["Brisa"],"fronted subject",True)
add(246,6,"claim",["Tamlin is married to Yselde.","Tamlin's city is Craydon."],"What is the name of the person Tamlin is married to?",["Yselde"],["Tamlin"],"long wording",True)
add(246,7,"claim",["Hollis Brey is married to Nerys Cole.","Hollis Brey's pet is Pip."],"Whom has Hollis Brey married?",["Nerys Cole"],["Hollis Brey"],"has married",True)
add(246,8,"claim",["Varro was born in Estmere.","Varro's city is Ludwell."],"Where was Varro born?",["Estmere"],["Varro"],"born (place_of_birth)",True)
add(246,9,"keep",["Keswin Tull's city is Fallowick."],"What is Keswin Tull's city?",["Fallowick"],[],"possessive, single fact")
add(246,10,"keep",["Odo is married to Merrit."],"Who is Odo married to?",["Merrit"],[],"single fact, base works")
add(246,11,"keep",S,"What is Keswin Tull's employer?",["Grenby Loom"],[],"possessive")
add(246,12,"keep",S,"Where does Keswin Tull live?",["Fallowick"],[],"verb reader")
add(246,13,"trap",S,"Who is Keswin Tull's doctor?",[],["Keswin Tull"],"untaught")
add(246,14,"trap",S,"Who does Grenby Loom work with?",[],["Grenby Loom"],"work with / wrong dir")
add(246,15,"trap",S,"Is Keswin Tull married to Opaline?",[],["Keswin Tull","Opaline"],"yes/no, no write")
add(246,16,"trap",S,"Who is Arabel Moss's employer?",[],["Arabel Moss"],"value-side entity, untaught")

# ---------- 247 missing apostrophe ----------
P = ["Quenby's city is Harlowe.","Quenby's pet is Dandle.","Quenby's doctor is Isolde Ferr.","Quenby's school is Tamsworth."]
add(247,1,"claim",P,"Who is Quenbys doctor?",["Isolde Ferr"],["Quenby"],"doctor")
add(247,2,"claim",P,"what is quenbys pet?",["Dandle"],["Quenby"],"lowercase")
add(247,3,"claim",["Mab Orrow Fell's city is Pikeholm."],"What is Mab Orrow Fells city?",["Pikeholm"],["Mab Orrow Fell"],"3-word name")
add(247,4,"claim",["Dorrin Vask's employer is Coldharbour Press."],"Who is Dorrin Vasks employer?",["Coldharbour Press"],["Dorrin Vask"],"2-word")
add(247,5,"claim",P,"Who's Quenbys doctor?",["Isolde Ferr"],["Quenby"],"Who's contraction + no apos",True)
add(247,6,"claim",P,"What was Quenbys school?",["Tamsworth"],["Quenby"],"past tense 'was'",True)
add(247,7,"claim",["Tessaly's boss is Ormund.","Ormund's city is Blackwater Reach."],"What is Tessalys boss's city?",["Blackwater Reach"],["Tessaly","Ormund"],"chain",True)
add(247,8,"claim",["Lorcan's place of birth is Easterly."],"What is Lorcans place of birth?",["Easterly"],["Lorcan"],"multiword relation",True)
add(247,9,"keep",P,"Who is Quenby's doctor?",["Isolde Ferr"],[],"has apostrophe")
add(247,10,"keep",["Wills's city is Harlowe."],"What is Wills's city?",["Harlowe"],[],"name ending in s, apostrophe")
add(247,11,"keep",["James Wills's pet is Rook."],"Who is James Wills?",[],["James Wills"],"name ends in s, no relation")
add(247,12,"keep",P,"Where does Quenby live?",["Harlowe"],[],"verb form, no apos needed")
add(247,13,"trap",P,"Who is Quenbys teacher?",[],["Quenby"],"untaught")
add(247,14,"trap",["Soren's pet is Marl."],"Who is Sorens owner?",[],["Soren"],"flip-ish untaught 'owner'")
add(247,15,"trap",P,"Is Quenbys city Harlowe?",[],["Quenby","Harlowe"],"yes/no, no write")
add(247,16,"keep",["Hobbs's pet is Tansy."],"What is Hobbs pet?",[],["Hobbs","Tansy"],"name ends in s; stem Hobb not an entity; must not change")

# ---------- 248 whats/whos/wheres ----------
W = ["Linnet's city is Corvale.","Linnet's coach is Barrow Emm.","Linnet's employer is Heathcote Mill."]
add(248,1,"claim",W,"whats Linnet's city?",["Corvale"],["Linnet"],"lower")
add(248,2,"claim",W,"Whos Linnet's coach?",["Barrow Emm"],["Linnet"],"Whos")
add(248,3,"claim",W,"Hey, whats Linnet's employer?",["Heathcote Mill"],["Linnet"],"filler",True)
add(248,4,"claim",W,"wheres Linnet's city?",["Corvale"],["Linnet"],"wheres")
add(248,5,"claim",["Ober Stail's pet is Grummet."],"WHATS OBER STAIL'S PET?",["Grummet"],["Ober Stail"],"upper 2-word")
add(248,6,"claim",W+["Barrow Emm's city is Lanthorn."],"whats Linnet's coach's city?",["Lanthorn"],["Linnet","Barrow Emm"],"chain",True)
add(248,7,"claim",["Ferris Hale's doctor is Una Pike."],"Okay whos Ferris Hale's doctor?",["Una Pike"],["Ferris Hale"],"filler no comma",True)
add(248,8,"claim",W,"whats the city of Linnet?",["Corvale"],["Linnet"],"'the R of X'",True)
add(248,9,"keep",W,"What's Linnet's city?",["Corvale"],[],"apostrophe")
add(248,10,"keep",W,"What is Linnet's coach?",["Barrow Emm"],[],"full")
add(248,11,"keep",["Whatley's city is Corvale."],"Whatley's city?",["Corvale"],[],"name starting What")
add(248,12,"keep",W,"whats up?",[],[],"small talk")
add(248,13,"trap",W,"whats Linnet's pet?",[],["Linnet"],"untaught")
add(248,14,"trap",W,"whos Heathcote Mill's employer?",[],["Heathcote Mill"],"flip direction")
add(248,15,"trap",W,"whats Linnet's city, is it Rookby?",[],["Linnet","Rookby"],"no write")

# ---------- 249 first person ----------
add(249,1,"claim",["My city is Ambergate."],"What city do I live in?",["Ambergate"],[],"",True)
add(249,2,"claim",["My boss is Tilda Marr."],"Who do I report to?",["Tilda Marr"],[],"",True)
add(249,3,"claim",["My job is carpenter."],"What do I do for a living?",["carpenter"],[],"",True)
add(249,4,"claim",["My age is 34."],"How old am I?",["34"],[],"")
add(249,5,"claim",["My school is Wickmoor Academy."],"Which school do I attend?",["Wickmoor Academy"],[],"",True)
add(249,6,"claim",["My spouse is Rowan Tiel."],"hey, who am i married to?",["Rowan Tiel"],[],"lower + greeting")
add(249,7,"claim",["My employer is Stellwick Foods."],"Where do I work, please?",["Stellwick Foods"],[],"trailing please")
add(249,8,"claim",["My pet is Cobble."],"What pet do I have?",["Cobble"],[],"",True)
add(249,9,"keep",["My city is Ambergate."],"What is my city?",["Ambergate"],[],"Me166 form")
add(249,10,"keep",["My name is Hesper Vane."],"Who am I?",["Hesper Vane"],[],"name")
add(249,11,"keep",["Ansel's city is Ambergate."],"Where does Ansel live?",["Ambergate"],[],"third person")
add(249,12,"keep",["My city is Ambergate.","My employer is Stellwick Foods."],"Where do you live?",[],[],"second person; no user value")
add(249,13,"trap",["My city is Ambergate."],"Where do I work?",[],[],"untaught employer, city stored")
add(249,14,"trap",["My employer is Stellwick Foods."],"Who works for me?",[],[],"direction flip")
add(249,15,"trap",["My city is Ambergate."],"Do I live in Brindle?",[],["Brindle"],"yes/no, no write")

# ---------- 250 verb subject ----------
V = ["Elland Tove's city is Rushmere.","Elland Tove's employer is Gant Ropeworks.","Elland Tove's language is Norric."]
add(250,1,"claim",V,"where does elland tove live?",["Rushmere"],["Elland Tove"],"lower 2-word")
add(250,2,"claim",V,"WHO DOES ELLAND TOVE WORK FOR?",["Gant Ropeworks"],["Elland Tove"],"upper")
add(250,3,"claim",V,"What language does elland tove speak?",["Norric"],["Elland Tove"],"language")
add(250,4,"claim",["Mab Ostry Fell's city is Coldbrook.","Mab Ostry Fell's pet is Wisp."],"Where does Mab Ostry Fell live?",["Coldbrook"],["Mab Ostry Fell"],"3-word",True)
add(250,5,"claim",["quillan's place of birth is Sedge Hollow.","quillan's city is Rushmere."],"Where was quillan born?",["Sedge Hollow"],["quillan"],"lower, born",True)
add(250,6,"claim",V,"where does Elland tove work?",["Gant Ropeworks"],["Elland Tove"],"mixed case, where work",True)
add(250,7,"claim",["Jory Pask's city is Tamberlin."],"Where does jory pask live, please?",["Tamberlin"],["Jory Pask"],"trailing please",True)
add(250,8,"claim",V,"who does elland tove work for?",["Gant Ropeworks"],["Elland Tove"],"lower work for")
add(250,9,"keep",V,"Where does Elland live?",[],["Elland"],"partial name (unknown one-word)")
add(250,10,"keep",["Brask's city is Rushmere."],"Where does Brask live?",["Rushmere"],[],"base already works")
add(250,11,"keep",V,"Where does my sister live?",[],[],"possessive det veto")
add(250,12,"keep",V,"Where do they live?",[],[],"closed-class subject")
add(250,13,"trap",V,"where was elland tove born?",[],["Elland Tove"],"untaught birthplace")
add(250,14,"trap",V,"who does gant ropeworks work for?",[],["Gant Ropeworks"],"direction flip (value side)")
add(250,15,"trap",V,"does elland tove live in rushmere?",[],["Elland Tove","Rushmere"],"yes/no no write")

# ---------- 251 direction ----------
D = ["Tamsin's employer is Graywater Foundry.","Tamsin's teacher is Orla Vey.","Tamsin's doctor is Bede Marsh."]
add(251,1,"claim",D,"Whom did Graywater Foundry hire?",["Tamsin"],["Graywater Foundry"],"hire (inverse)",True)
add(251,2,"claim",D,"Who is taught by Orla Vey?",["Tamsin"],["Orla Vey"],"passive teach",True)
add(251,3,"claim",D,"Who does Tamsin employ?",[],["Tamsin"],"leak must decline")
add(251,4,"claim",D,"Who does Bede Marsh treat?",["Tamsin"],["Bede Marsh"],"treat inverse")
add(251,5,"claim",D,"Who are Bede Marsh's patients?",["Tamsin"],["Bede Marsh"],"noun form",True)
add(251,6,"claim",D,"Who is Orla Vey the teacher of?",["Tamsin"],["Orla Vey"],"'the R of'",True)
add(251,7,"claim",D,"Who does Tamsin teach?",[],["Tamsin"],"forward-teacher must not leak")
add(251,8,"claim",["Sable's owner is Crispin Hay."],"What does Crispin Hay own?",["Sable"],["Crispin Hay"],"own",True)
add(251,9,"keep",D,"Who is Tamsin's employer?",["Graywater Foundry"],[],"forward possessive")
add(251,10,"keep",D,"Who does Tamsin work for?",["Graywater Foundry"],[],"forward verb")
add(251,11,"keep",D,"Who teaches Tamsin?",["Orla Vey"],[],"active forward (subject=value)")
add(251,12,"keep",D,"Who employs Tamsin?",["Graywater Foundry"],[],"active forward")
add(251,13,"trap",D,"Who does Tamsin supervise?",[],["Tamsin"],"untaught verb")
add(251,14,"trap",D,"What did Tamsin create?",[],["Tamsin"],"verb outside table")
add(251,15,"trap",D,"Does Graywater Foundry employ Kell?",[],["Graywater Foundry","Kell"],"no write")
add(251,16,"trap",D,"Who works at Tamsin?",[],["Tamsin"],"extra wording, wrong direction")
json.dump(C, open(sys.argv[1], "w"), indent=1)
print(len(C))
