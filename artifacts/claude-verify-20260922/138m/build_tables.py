"""Build case-tables.md and summary.json from both arms' rows. Labels for changed replies are the verifier's hand labels (LAB)."""
import json, re
B="better"; W="worse"; S="same"
LAB={ # (id, turn index among non-restart turns) -> (label, reason)
 ("A02",0):(S,"identity miss in both ('who made u'); m text is only cleaner"),
 ("A03",0):(B,"identity sheet instead of glued decline"),("A04",0):(B,"identity sheet"),("A05",0):(B,"identity sheet"),
 ("A06",0):(S,"typo 'yuor' misses identity in both"),
 ("A07",0):(B,"Ben built me."),("A08",0):(B,"Ben built me."),("A09",0):(B,"My name is Premonition."),("A10",0):(B,"My name is Premonition."),
 ("A11",0):(B,"Ben built me."),("A12",0):(B,"identity sheet"),("A14",0):(B,"Ben built me."),
 ("A15",0):(S,"'are u human' misses identity in both"),("A16",1):(B,"My name is Premonition. (not the user's name)"),
 ("N02",1):(W,"correct answer is 'I don't know'; m now says only 'didn't understand'"),
 ("N03",0):(W,"correct answer is 'I don't know'; m says only 'didn't understand'"),
 ("N05",0):(W,"correct answer is 'I don't know'; m says only 'didn't understand'"),
 ("N07",0):(W,"correct answer is 'I don't know'; m says only 'didn't understand'"),
 ("N08",0):(S,"'Are you busy?' out of scope; both abstain, m cleaner"),
 ("N09",0):(W,"'What's your city?' should be 'I don't know'; m says only 'didn't understand'"),
 ("B04",1):(S,"name stored but both miss (212/216 gate); m no longer falsely says 'no record'"),
 ("B05",1):(S,"name stored but both miss (212/216 gate)"),
 ("B12",1):(B,"Yes. Your name is Wren."),("B14",1):(B,"Your name is Isolde."),
 ("B15",0):(S,"'Please call me Fenna.' not saved in either"),
 ("B18",0):(W,"nothing stored; should be 'I don't know your name yet'; m calls a request unsaveable"),
 ("B19",1):(B,"Your name is Tamsin."),("B20",1):(S,"name stored but both miss"),
 ("C14",0):(W,"unknown person; correct 'I don't know'; m says only 'didn't understand'"),
 ("D01",0):(S,"polite teach not saved in either"),("D02",1):(S,"fact stored, both miss"),("D03",1):(S,"fact stored, both miss"),
 ("D04",0):(S,"polite teach not saved in either"),("D05",1):(S,"fact stored, both miss; m calls a question unsaveable"),
 ("D06",0):(W,"unknown person; correct 'I don't know'; m says only 'didn't understand'"),
 ("D07",1):(B,"Your name is Pippa."),("D08",1):(S,"fact stored, both miss"),("D09",1):(S,"polite correction not applied in either"),
 ("D10",1):(S,"both miss; bad entity 'Please, Kestrel' stored in both"),
 ("E02",0):(B,"234 reply"),("E03",0):(B,"234 reply replaces LISTENING mode leak"),("E06",0):(S,"'hello there' bad in both; m calls it unsaveable"),
 ("E08",0):(B,"234 reply replaces LISTENING mode leak"),("E09",2):(B,"234 reply replaces LISTENING mode leak"),
 ("R05",1):(B,"234 reply"),("R06",0):(B,"Ben built me."),("R06",2):(B,"My name is Premonition."),
 ("R07",0):(S,"polite teach not saved in either"),("R07",1):(S,"fact never saved; both abstain"),
 ("S01",1):(B,"233: answers Mirela"),("S02",1):(B,"233: answers Keld"),("S03",1):(B,"233: answers fisher"),
 ("S04",1):(B,"233: honest 'I don't know'"),("S05",0):(B,"233: honest 'I don't know anyone called'"),("S06",1):(B,"233: answers Orrin"),
 ("S09",1):(B,"233: answers Ashby"),("S10",1):(B,"233: honest 'I don't know'"),
}
def faults(t):
    f=[]
    if t and not t[0].isupper() and not t[0] in '"\'': f.append("no capital")
    if t and t.rstrip()[-1] not in '.?!)"\'': f.append("no end punctuation")
    if "USER" in t or re.search(r"\w_\w",t): f.append("raw key")
    if "LISTENING" in t: f.append("mode name")
    if re.search(r"\b1 people\b",t): f.append("agreement")
    if "didn't understand that, I don't know" in t: f.append("comma splice")
    if "called the name of" in t: f.append("misparse 'the name of'")
    if "Please, " in t and "Saved" in t: f.append("junk entity")
    return f
rows=[]; summ={"changed":{},"du_dk":{}}
for pf,rl,rm in [('probes.json','rows-138l.json','rows-138m.json'),('probes-supp.json','supp-rows-138l.json','supp-rows-138m.json')]:
    P=json.load(open(pf)); L=json.load(open(rl)); M=json.load(open(rm))
    for p,a,b in zip(P,L,M):
        k=0
        for x,y in zip(a['rows'],b['rows']):
            if x.get('restart'): continue
            if x['reply']!=y['reply']:
                lab,why=LAB.get((p['id'],k),("UNLABELLED",""))
                summ["changed"].setdefault(p['feature'],{}).setdefault(lab,0); summ["changed"][p['feature']][lab]+=1
            else: lab,why=("-","unchanged")
            fl=faults(x['reply']); fm=faults(y['reply'])
            rows.append((p['id'],p['feature'],x['turn'],x['reply'],y['reply'],lab,why,"; ".join(fl) or "-","; ".join(fm) or "-"))
            for arm,t in (('l',x['reply']),('m',y['reply'])):
                du="didn't understand" in t; dk=("don't know" in t or "do not know" in t or "never told me" in t)
                c="both(glued)" if du and dk else "didnt_understand" if du else "dont_know" if dk else "other"
                summ["du_dk"].setdefault(arm,{}).setdefault(c,0); summ["du_dk"][arm][c]+=1
            k+=1
esc=lambda s:s.replace("|","\\|").replace("\n"," ")
with open("case-tables.md","w") as f:
    f.write("# 138m verifier probes: case table\n\nOne row per probe turn (restarts omitted). l = 138l, m = 138m. Label is for changed replies only.\n\n| id | feature | turn | 138l reply | 138m reply | change | reason | faults l | faults m |\n|---|---|---|---|---|---|---|---|---|\n")
    for r in rows: f.write("| "+" | ".join(esc(str(c)) for c in r)+" |\n")
json.dump(summ,open("summary.json","w"),indent=1); print(json.dumps(summ,indent=1))
print("unlabelled:",[r[:3] for r in rows if r[5]=="UNLABELLED"])
