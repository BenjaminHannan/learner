"""Supplement: 233's own frame (negative polite: can't/won't/couldn't/don't you ... tell me/know/remind me/say), fresh wordings."""
import json
U="USER"; P=[]
def d(id,feat,turns,expect,note=""): P.append({"id":id,"feature":feat,"turns":turns,"expect_stored":expect,"note":note})
d("S01","polite233",["T|Tomas's boss is Mirela.","Q|Can't you tell me who Tomas's boss is?"],[["Tomas","boss","Mirela"]],"taught -> Mirela")
d("S02","polite233",["T|Yarrow lives in Keld.","Q|Won't you tell me where Yarrow lives?"],[["Yarrow","city","Keld"]],"taught -> Keld")
d("S03","polite233",["T|Kestrel's job is fisher.","Q|Couldn't you remind me what Kestrel's job is?"],[["Kestrel","job","fisher"]],"taught -> fisher")
d("S04","polite233",["T|Pim's favourite colour is teal.","Q|Don't you know who Pim's boss is?"],[["Pim","favourite_colour","teal"]],"untaught relation -> don't know")
d("S05","polite233",["Q|Wouldn't you just tell me Garrick's city?"],[],"unknown person -> don't know")
d("S06","polite233",["T|Nell lives in Orrin.","Q|Do you not know where Nell lives?"],[["Nell","city","Orrin"]],"taught -> Orrin")
d("S07","polite233",["T|My name is Pippa.","Q|Can't you please tell me my name?"],[[U,"name","Pippa"]],"name -> Pippa")
d("S08","polite233",["T|Fitch works for Grobal.","Q|Cannot you say who Fitch works for?"],[["Fitch","employer","Grobal"]],"taught -> Grobal")
d("S09","polite233",["T|Juno was born in Ashby.","Q|So, won't you tell me where Juno was born?"],[["Juno","place_of_birth","Ashby"]],"taught -> Ashby")
d("S10","polite233",["T|Hale's sister is Orla.","Q|Couldn't you tell me who Hale's brother is?"],[["Hale","sister","Orla"]],"untaught relation -> don't know")
d("S11","negation-control",["T|Tove's boss is Anselm.","Q|Isn't Tove's boss Anselm?"],[["Tove","boss","Anselm"]],"must match 138l")
d("S12","negation-control",["T|Tove's boss is Anselm.","Q|Tove's boss isn't Anselm."],[["Tove","boss","Anselm"]],"negated statement; must match 138l")
json.dump(P,open("probes-supp.json","w"),indent=1); print(len(P))
