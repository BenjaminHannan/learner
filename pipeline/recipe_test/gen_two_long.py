"""Round 7: questions longer than the real core's 49-token query cap. Run with RT_ROUND=2.
Training: a share of two-step items get 1-6 neutral filler sentences inserted (digit-free, no quantity or add/remove words), so the answer is unchanged.
Eval ("long" set): 192 two-step questions built from the 24 independently written layout families (round-5 and round-6 blind sets) with filler sentences from a pool written
by a separate worker (eval_filler_r7.json) until the question is at least 55 tokens (never more than 150). The short eval sets are unchanged.
"""
import itertools, json, os, random, re
import gen, gen2, gen_two

HERE = os.path.dirname(os.path.abspath(__file__))
LONG_LO, LONG_HI = 55, 150
FILL_TRAIN = [
    "The afternoon light was soft and the street outside stayed quiet.", "A radio somewhere nearby played an old slow song.", "Nobody in the room seemed to be in any particular hurry that day.",
    "The weather report promised clouds followed by a mild evening breeze.", "A faint smell of fresh bread drifted in from the corner bakery.", "The walls of the little office had recently been painted a pale green.",
    "Outside the window a bus rumbled past and disappeared around the bend.", "It had been a calm week in the neighbourhood, with very little going on.", "The old clock above the door ticked louder than anyone remembered.",
    "A cat slept on the windowsill and ignored every sound in the building.", "The meeting had been moved to a smaller room with a view of the courtyard.", "Somebody had left a blue umbrella leaning against the doorframe.",
    "The coffee machine in the hallway made its usual gurgling noise.", "Everyone agreed that the garden looked especially lovely in the morning sun.", "A distant train whistle echoed over the rooftops of the town.",
    "The floor creaked gently whenever someone walked across the wooden hall.", "On the notice board hung a faded poster about the spring festival.", "The mood was cheerful, and a few people hummed while they worked.",
    "A thin layer of frost covered the grass behind the old storage building.", "The telephone on the desk rang twice and then fell silent.", "Dust floated slowly through the beam of light that crossed the room.",
    "It was one of those quiet days when the whole building seemed to be resting.", "A gentle rain tapped against the glass and made the lamps look warmer.", "The hallway smelled faintly of lemon polish and warm paper.",
    "Far off a dog barked twice, then the neighbourhood went still again.", "The sky over the harbour turned a deep orange as the day wound down.", "Somebody had taped a hand-drawn map of the building beside the elevator.",
    "The wind picked up a little and rattled the shutters on the north side.", "A group of schoolchildren walked past singing a song nobody could name.", "The new carpet in the corridor was a bit too bright for most tastes.",
    "A kettle whistled in the back room while the radio read the local news.", "The streetlights flickered on one by one along the quiet avenue.", "People spoke softly, as though the room itself deserved some respect.",
    "The windows were fogged from the warm air and the cold glass outside.", "A sleepy calm had settled over the town after the long holiday weekend.", "The stairwell echoed with footsteps and the occasional cheerful greeting.",
    "Sunlight crept slowly across the tiles and warmed the corner of the desk.", "The hallway lamps hummed quietly in the stillness of the early evening.", "An old poster of a mountain landscape curled at its corners near the door.",
    "It was a peaceful morning, and the air smelled of cut grass and rain.", "Pigeons gathered on the ledge outside and watched the crowd below.", "The little shop at the corner kept its bell ringing for every passer-by.",
    "A comfortable silence filled the room after the last announcement ended.", "The river beyond the park looked calm and silver under the pale sky.", "Everything about the place felt familiar, tidy, and slightly sleepy.",
    "The sound of distant hammering drifted over from a building site across the road.", "A soft knock at the door was followed by a polite apology and a smile.", "The cafeteria was warm, noisy, and full of conversations about the weekend.",
    "Dark clouds gathered over the hills, though the town stayed bright for now.", "Someone had opened a window and let a pleasant breeze drift through the room."]

_SENT = re.compile(r"(?<=[.?])\s+")


def lengthen(text, rng, pool, ntok, lo=LONG_LO, hi=LONG_HI, kmax=7, start_k=None):
    """Insert filler sentences (random slots between/around the text's sentences) until ntok(text) >= lo; None if it cannot land in [lo, hi]."""
    segs = _SENT.split(text)
    for _ in range(40):
        s = list(segs); k = start_k or rng.randint(1, kmax)
        for f in rng.sample(pool, min(k, len(pool))):
            s.insert(rng.randint(0, len(s)), f)
        t = " ".join(s)
        n = ntok(t)
        if lo <= n <= hi: return t
        if n < lo:
            start_k = (start_k or k) + 1
        else:
            start_k = max(1, (start_k or k) - 1)
    return None


def eval_fillers():
    d = json.load(open(os.path.join(HERE, "eval_filler_r7.json")))["fillers"]
    tg = set().union(*(gen2.grams(t, 5) for t in FILL_TRAIN))
    ts = {t.lower() for t in FILL_TRAIN}
    return [f for f in d if f.lower() not in ts and not (gen2.grams(f, 5) & tg)]


def build_long(ntok, per=1, seed=20261701, used=frozenset()):
    """192 long two-step questions: 24 families x 4 op pairs x (1 unseen + 1 seen final)."""
    T, H = gen.answer_split(); rng = random.Random(seed); e2 = gen.load(gen.EVAL_FILE)
    pool = eval_fillers(); rows = []; used = set(used)
    fams = []
    for fn in ("eval_layouts_r5_blind.json", "eval_layouts_r6_blind.json"):
        fams += [(fn[13:15] + "-" + f["name"], f["kind"], f["frames"]) for f in json.load(open(os.path.join(HERE, fn)))["families"]]
    for fname, kind, frames in fams:
        for o1, o2 in itertools.product(("ADD", "SUB"), repeat=2):
            texts = frames[f"{o1}-{o2}"]
            for ci, (cell, finals) in enumerate((("unseen", set(H)), ("seen", set(T)))):
                while True:
                    x, y, z = (rng.randint(10, 99) for _ in range(3))
                    v = gen_two.ok_values(x, y, z, o1, o2)
                    if v and v[1] in finals and (x, y, z) not in used: break
                used.add((x, y, z))
                for _ in range(500):
                    base = rng.choice(texts).format(name=rng.choice(e2["names"]), noun=rng.choice(e2["nouns"]), x=x, y=y, z=z)
                    t = lengthen(base, rng, pool, ntok)
                    if t: break
                assert t, ("cannot lengthen", fname)
                rows.append({"id": f"{fname}-{o1}{o2}-{cell}", "cell": f"{cell}/{fname}", "structure": kind, "steps": 2, "op1": o1, "op2": o2, "x": x, "y": y, "z": z,
                             "r1": v[0], "answer": v[1], "text": t, "ntok": ntok(t)})
    return rows
