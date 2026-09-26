"""0.2c judge packets (month-end, 2026-09-26, after the run; adapted from judge_prep336b.py). Prints counts only.
usage: judge_prep02c.py BANK SCORE OUTDIR"""
import json, random, sys
from pathlib import Path
BANK, SCORE, OUT = map(Path, sys.argv[1:4])
ld = lambda p: [json.loads(x) for x in open(p, encoding="utf-8") if x.strip()]
turns = {(t["life_id"], t["turn_index"]): t for t in ld(BANK / "turns.jsonl")}
truth = ld(BANK / "truth.jsonl")
OUT.mkdir(parents=True, exist_ok=True)
def w(name, rows):
    (OUT / name).parent.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
def wk(name, key):
    (OUT / name).parent.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(key), encoding="utf-8")
# M1-style wrong saves and M2 wrong answers: X and G mixed under neutral ids (keys applied by script later)
for kind, prefix, seed in (("saves", "S", 3365), ("asks", "Q", 3364)):
    rows = []
    for arm in ("X", "G"):
        for p in ld(SCORE / f"judge_{kind}_{arm}.jsonl"):
            p = dict(p); p["_arm"] = arm; rows.append(p)
    random.Random(seed).shuffle(rows)
    key = {}
    for i, p in enumerate(rows):
        p["id"] = f"{prefix}{i:04d}"; key[p["id"]] = p.pop("_arm")
        t = turns.get((p["life_id"], p["turn_index"]))
        if kind == "asks":
            p["user_text"] = t["user_text"]
            p["truth_valid_now"] = [{k: f[k] for k in ("owner", "relation", "value")} for f in truth
                                    if f["life_id"] == p["life_id"] and f["taught_turn"] <= p["turn_index"]
                                    and (f.get("valid_until_turn") is None or f["valid_until_turn"] > p["turn_index"])]
        else:
            p["user_text"] = t["user_text"] if (t and p.get("row_kind") == "user") else None
    w(f"m1/{kind}.jsonl" if kind == "saves" else f"m2/{kind}.jsonl", rows)
    wk(f"key_{kind}.json", key)
CLEAN = ["That sounds like a lovely way to spend the afternoon.", "I hope the interview goes well tomorrow.",
 "Rainbows form when sunlight bends inside raindrops.", "A short walk after dinner can help you sleep.",
 "You could bring a salad and some fresh bread.", "It is completely normal to feel nervous before a big day.",
 "The bakery on the corner opens at seven.", "Try writing down three things that went well today.",
 "Cast iron holds heat because it is thick and dense.", "She might enjoy a book about local birds.",
 "Let me know how the recital goes.", "A warm drink and a blanket can make a rainy evening cosy.",
 "Your plan for the weekend sounds relaxed and fun.", "Water boils at a lower temperature on a mountain.",
 "Packing the night before saves a lot of stress.", "Congratulations on finishing the marathon!",
 "It helps to take breaks when you study for a long time.", "A handwritten card is always a thoughtful touch.",
 "The museum is usually quieter on weekday mornings.", "You did the right thing by asking for help.",
 "Tomatoes grow best with plenty of sun and steady watering.", "A picnic by the river could be a nice surprise.",
 "I'm sorry the week has been so exhausting.", "Stretching before a run can prevent some injuries.",
 "The recipe needs two eggs and a cup of flour.", "Maybe you could start with a short practice session.",
 "Birthdays are more fun with a small surprise.", "The train should be faster than driving at rush hour.",
 "Honey never really spoils if it is stored well.", "It sounds like your team worked very hard this month.",
 "A board game night is an easy way to relax together.", "Most houseplants prefer bright, indirect light.",
 "You might feel better after a good night's sleep.", "The concert starts at eight, so leave a little early.",
 "Learning a few phrases before a trip is really useful.", "Hot soup is perfect on a cold evening.",
 "Writing a list can make a busy day feel smaller.", "Dogs usually love a long walk in the park.",
 "That was a kind thing to do for your neighbour.", "Saving a little each week adds up over a year."]
def plant(s, k):
    ws = s.split()
    kind = k % 4
    if kind == 0:                                   # doubled word
        i = 1 + (k * 7) % (len(ws) - 2); ws.insert(i, ws[i])
    elif kind == 1:                                 # agreement: is <-> are / has <-> have / a->an
        for a, b in (("is", "are"), ("are", "is"), ("has", "have"), ("can", "cans"), ("might", "mights")):
            if a in ws: ws[ws.index(a)] = b; break
        else: ws.insert(1, "does")
    elif kind == 2:                                 # wrong article
        for i, x in enumerate(ws):
            if x.lower() in ("a", "the"): ws[i] = "an" if x.lower() == "a" else "a the"; break
        else: ws.insert(len(ws) - 1, "a")
    else:                                           # missing verb: drop the first verb-ish word
        for v in ("is", "are", "can", "could", "might", "should", "helps", "holds", "need", "needs", "opens",
                  "starts", "prefer", "form", "grow", "love", "did", "was", "adds", "makes", "make", "sounds"):
            if v in ws: ws.remove(v); break
        else: ws = ws[:1] + ws[2:]
    return " ".join(ws)
errs = [plant(s, k) for k, s in enumerate(CLEAN)]
assert all(e != s for e, s in zip(errs, CLEAN))
cleanB = ["Thanks for telling me about your day.", "A cup of tea might help you unwind.",
 "The library has a great section on gardening.", "It is a good idea to check the weather first.",
 "You can freeze the soup for later.", "Sometimes a quiet evening is exactly what you need.",
 "The bus stop is just around the corner.", "Try adding a little lemon to the dressing.",
 "Your sister will probably love a framed photo.", "It takes time to get used to a new job.",
 "A light jacket should be enough tonight.", "Bananas ripen faster in a paper bag.",
 "The movie was longer than I expected.", "Keep the receipt in case it doesn't fit.",
 "Most cats sleep for much of the day.", "A good breakfast gives you energy for the morning.",
 "You could invite a few friends over for pizza.", "It might rain later, so bring an umbrella.",
 "The recipe works well with brown rice too.", "Small steps are still progress.",
 "The garden looks better after a little rain.", "Reading before bed helps many people relax.",
 "Your idea for the party is really creative.", "A quick call can mean a lot to someone.",
 "Fresh herbs make a simple dish taste special.", "The trip will be easier if you book early.",
 "It is fine to say no when you are tired.", "The kids might enjoy a scavenger hunt.",
 "Soft music can make studying less boring.", "A spare charger is handy on long trips.",
 "Walking to work is a nice way to clear your head.", "That sounds like a well-earned rest.",
 "The shop closes early on Sundays.", "A bright scarf would suit her well.",
 "Remember to drink water during the hike.", "The museum has free entry on Fridays.",
 "Plants need less water in the winter.", "You handled a hard situation calmly.",
 "The pasta takes about ten minutes to cook.", "A photo album makes a thoughtful gift."]

RX = sorted({x["reply"] for x in ld(SCORE / "grammar_chat_X.jsonl")})
for g, seed in (("A", 3366), ("B", 3367)):
    items = [(r, False) for r in RX] + [(e, True) for e in errs] + [(c, False) for c in cleanB]
    random.Random(seed).shuffle(items)
    w(f"m7/gram{g}.jsonl", [{"id": f"{g}{i:04d}", "text": t} for i, (t, _) in enumerate(items)])
    wk(f"key_gram{g}.json", {f"{g}{i:04d}": {"planted_error": e, "planted_clean": t in cleanB, "x_reply": t in RX}
                             for i, (t, e) in enumerate(items)})
# chat pairs: one packet per 15 conversations (already shuffled per conversation by the runner, keys in score/)
for other in ("G", "T"):
    rows = ld(SCORE / f"chat_pair_{other}.jsonl")
    for c in range(0, len(rows), 15):
        w(f"pairs/pair_{other}_{c // 15 + 1}.jsonl", rows[c:c + 15])
print(json.dumps({"saves": sum(1 for _ in open(OUT / "m1/saves.jsonl")), "asks": sum(1 for _ in open(OUT / "m2/asks.jsonl")),
                  "grammar_replies": len(RX), "planted_errors": len(errs), "planted_clean": len(cleanB)}))
