"""Throwaway prototype of a procedurally generated text world (scratch only).

Purpose: measure how fast a pure-Python generator can emit controlled-English
text with (a) observation narration governed by hidden rules, (b) teacher
'tell' statements, (c) questions with answers and right/wrong feedback, and
(d) fresh nonce names every world instance. Also shows sample output.
"""
import random, time

SYL_ON = ["b", "d", "f", "g", "k", "l", "m", "n", "p", "r", "s", "t", "v", "z", "br", "gl", "tr", "sk"]
SYL_NU = ["a", "e", "i", "o", "u", "ai", "ou"]
SYL_CO = ["", "", "n", "l", "r", "s", "k"]
MATERIALS = ["glass", "wood", "metal", "cloth"]
KINDS = ["cup", "box", "ball", "key", "lamp", "coin", "bowl"]
COLORS = ["red", "blue", "green", "white", "black"]


def nonce(rng, used):
    while True:
        w = "".join(rng.choice(SYL_ON) + rng.choice(SYL_NU) + rng.choice(SYL_CO) for _ in range(rng.choice([2, 2, 3])))
        if w not in used:
            used.add(w)
            return w


class World:
    def __init__(self, seed, n_people=6, n_places=4, n_objects=8):
        rng = self.rng = random.Random(seed)
        used = set()
        self.people = [nonce(rng, used) for _ in range(n_people)]
        self.places = [nonce(rng, used) for _ in range(n_places)]
        self.objects = []
        for _ in range(n_objects):
            self.objects.append(dict(name=nonce(rng, used), kind=rng.choice(KINDS),
                                     mat=rng.choice(MATERIALS), color=rng.choice(COLORS)))
        # Hidden rules, re-randomised per world instance:
        self.fragile = rng.choice(MATERIALS)            # this material breaks when dropped
        self.friend = {p: rng.choice([q for q in self.people if q != p]) for p in self.people}  # follows friend
        self.loc = {p: rng.choice(self.places) for p in self.people}
        self.holder = {o["name"]: None for o in self.objects}
        self.broken = set()

    # --- observation stream: events governed by hidden rules ---
    def step(self):
        rng, out = self.rng, []
        p = rng.choice(self.people)
        act = rng.random()
        if act < 0.4:
            dest = rng.choice([x for x in self.places if x != self.loc[p]])
            self.loc[p] = dest
            out.append(f"{p} goes to the {dest} .")
            f = self.friend[p]                       # hidden social regularity
            if rng.random() < 0.8 and self.loc[f] != dest:
                self.loc[f] = dest
                out.append(f"{f} goes to the {dest} .")
        elif act < 0.7:
            free = [o for o in self.objects if self.holder[o["name"]] is None and o["name"] not in self.broken]
            if free:
                o = rng.choice(free)
                self.holder[o["name"]] = p
                out.append(f"{p} picks up the {o['color']} {o['kind']} {o['name']} .")
        else:
            held = [o for o in self.objects if self.holder[o["name"]] == p]
            if held:
                o = rng.choice(held)
                self.holder[o["name"]] = None
                out.append(f"{p} drops the {o['name']} .")
                if o["mat"] == self.fragile:          # hidden physical rule
                    self.broken.add(o["name"])
                    out.append(f"the {o['name']} breaks .")
        return out

    # --- teacher channel: told facts (one exposure) ---
    def tell(self):
        o = self.rng.choice(self.objects)
        return [f"teacher : the {o['name']} is made of {o['mat']} ."], ("mat", o["name"], o["mat"])

    # --- question + model answer + right/wrong feedback ---
    def quiz(self, answer_fn):
        p = self.rng.choice(self.people)
        truth = self.loc[p]
        guess = answer_fn(self, p)
        fb = "yes , right ." if guess == truth else f"no , {p} is in the {truth} ."
        return [f"teacher : where is {p} ?", f"learner : the {guess} .", f"teacher : {fb}"]


def random_answer(w, p):
    return w.rng.choice(w.places)


def episode(seed, n_steps=60):
    w = World(seed)
    lines = []
    for t in range(n_steps):
        lines += w.step()
        if t % 10 == 3:
            lines += w.tell()[0]
        if t % 10 == 7:
            lines += w.quiz(random_answer)
    return lines


if __name__ == "__main__":
    print("\n".join(episode(1)[:28]))
    t0, ntok, nep = time.time(), 0, 0
    while time.time() - t0 < 5.0:
        for line in episode(nep):
            ntok += len(line.split())
        nep += 1
    dt = time.time() - t0
    print(f"\n{nep} worlds, {ntok} word-tokens in {dt:.1f}s -> {ntok/dt:,.0f} tokens/s on one CPU core")
