import random, hashlib
from dataclasses import replace
from collections import Counter
from learnlab.leaks import QAExample, leak_report
from learnlab.toy import make_registry, episodes, generate_episode, PLACES, TEMPLATES, Fact, OBJECTS

def rep(tag, train, test):
    r = leak_report(train, test)
    d = {k: round(v, 3) for k, v in r.detectors.items()}
    print(f"{'FLAGGED' if r.leaking else 'missed '} {tag}: floor={r.floor:.3f} (chance {r.chance:.3f}, presence {r.presence_chance:.3f}) det={d} -> {r.leaking_detectors}")
    return r

def base(split, n, start=0):
    return episodes(make_registry(), split, n, start=start)

def mutate(eps, fn, rate, seed):
    rng = random.Random(seed); out = []
    for e in eps:
        out.append(fn(e, rng) if rng.random() < rate else e.example())
    return out

def aiq(e, rng):
    ex = e.example(); return QAExample(ex.context, f"{ex.question} Is it the {e.target.place}?", ex.answer)

def move_target(e, pos):
    lines = list(e.lines); ti = e.facts.index(e.target)
    line = lines.pop(ti); lines.insert(pos if pos >= 0 else len(lines) + 1 + pos, line)
    return QAExample("\n".join(lines), e.question, e.target.place)

tr, te = base("train", 400), base("test", 300)
rep("clean", [e.example() for e in tr], [e.example() for e in te])
print("-- answer-in-question at partial rates")
for rate in (0.1, 0.2, 0.3, 0.4):
    rep(f"aiq {int(rate*100)}%", mutate(tr, aiq, rate, 1), mutate(te, aiq, rate, 2))
print("-- target line moved to LAST at partial rates (uniform = 25%)")
for rate in (0.2, 0.3, 0.4):
    rep(f"last {int(rate*100)}% extra", mutate(tr, lambda e, r: move_target(e, -1), rate, 3), mutate(te, lambda e, r: move_target(e, -1), rate, 4))
print("-- other position biases")
rep("target always FIRST", [move_target(e, 0) for e in tr], [move_target(e, 0) for e in te])
rep("target always SECOND", [move_target(e, 1) for e in tr], [move_target(e, 1) for e in te])

print("-- answer prior skew: target place is 'barn' with prob p (uniform = 12.5%)")
def skew(e, rng):
    t = e.target; newt = Fact(t.name, t.obj, "barn")
    facts = tuple(newt if f == t else f for f in e.facts)
    lines = tuple(l.replace(f" {t.place}", " barn") if (t.name in l and t.obj in l) else l for l in e.lines)
    return QAExample("\n".join(lines), e.question, "barn")
for p in (0.3, 0.4):
    rep(f"skew barn {int(p*100)}%", mutate(tr, skew, p, 5), mutate(te, skew, p, 6))

print("-- world regularity: object determines place (cup->barn etc) for target facts 60% of time")
OBJPLACE = dict(zip(OBJECTS, PLACES))
def objplace(e, rng):
    t = e.target; p = OBJPLACE[t.obj]
    lines = tuple(l.replace(f" {t.place}", f" {p}") if (t.name in l and t.obj in l) else l for l in e.lines)
    return QAExample("\n".join(lines), e.question, p)
rep("obj->place 60%", mutate(tr, objplace, 0.6, 7), mutate(te, objplace, 0.6, 8))

print("-- target fact always stated by the 'teacher' (surface cue on the target line only)")
def teacher(e, rng):
    lines = list(e.lines); ti = e.facts.index(e.target); lines[ti] = "Teacher says: " + lines[ti]
    return QAExample("\n".join(lines), e.question, e.target.place)
rep("teacher-marked target", [teacher(e, None) for e in tr], [teacher(e, None) for e in te])

print("-- capitalised answers (village names/places will be capitalised)")
cap = lambda ex: QAExample(ex.context.replace(ex.answer, ex.answer.capitalize()), ex.question, ex.answer.capitalize())
cap_ctx = lambda e: QAExample("\n".join(l.replace(e.target.place, e.target.place.capitalize()) for l in e.lines), e.question, e.target.place.capitalize())
rep("capitalised + target always last", [cap_ctx(e) for e in episodes(make_registry(), 'train', 400, leak='target_last')],
    [cap_ctx(e) for e in episodes(make_registry(), 'test', 300, leak='target_last')])

print("-- 'who' questions: answer is a (held-out) name, target always last")
def who(e):
    t = e.facts[-1]
    return QAExample("\n".join(e.lines), f"Who keeps the {t.obj} in the {t.place}?", t.name)
rep("who-question, target last 100%", [who(e) for e in tr], [who(e) for e in te])

print("-- leak present only in the test generator (train clean)")
rep("test-only aiq 100%", [e.example() for e in tr], mutate(te, aiq, 1.0, 9))
rep("test-only target first 100%", [e.example() for e in tr], [move_target(e, 0) for e in te])
