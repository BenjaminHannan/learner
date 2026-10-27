import copy, torch
from torch import nn
from learnlab.readonly import read_only, ReadOnlyViolation
from learnlab.toy import CardStore, Fact

def probe(name, fn, expect_caught):
    try:
        fn(); caught = False
    except ReadOnlyViolation: caught = True
    except Exception as e: caught = f"other:{type(e).__name__}"
    flag = "OK " if caught == expect_caught else "MISS"
    print(f"{flag} {name}: caught={caught}")

# 1 reassign param (not in place)
m = nn.Linear(4, 2)
def f1():
    with read_only(m): m.weight = nn.Parameter(m.weight.detach() + 1)
probe("param reassigned", f1, True)

# 2 add param / remove param
m = nn.Linear(4, 2)
def f2():
    with read_only(m): m.extra = nn.Parameter(torch.zeros(1))
probe("param added", f2, True)
m = nn.Linear(4, 2)
def f2b():
    with read_only(m): del m.bias; m.register_parameter("bias", None)
probe("param removed", f2b, True)

# 3 non-persistent buffer changed
m = nn.Module(); m.register_buffer("cache", torch.zeros(3), persistent=False)
def f3():
    with read_only(m): m.cache.add_(1)
probe("non-persistent buffer changed", f3, True)

# 4 plain tensor attribute (unregistered state, e.g. a memory matrix)
m = nn.Linear(4, 2); m.memory = torch.zeros(4)
def f4():
    with read_only(m): m.memory += 1
probe("unregistered tensor attribute", f4, True)

# 5 python-level state inside module (list of cards)
m = nn.Linear(4, 2); m.cards = []
def f5():
    with read_only(m): m.cards.append("nera+where=mill")
probe("python list state on module", f5, True)

# 6 train then restore before exit (test-time training + reset)
m = nn.Linear(4, 1)
def f6():
    with read_only(m):
        saved = copy.deepcopy(m.state_dict())
        opt = torch.optim.SGD(m.parameters(), lr=0.1)
        with torch.enable_grad():
            loss = m(torch.randn(8, 4)).pow(2).mean(); loss.backward(); opt.step()
        m.load_state_dict(saved)
probe("train then restore inside block", f6, True)

# 7 gradient step escapes torch.no_grad via enable_grad (no restore)
m = nn.Linear(4, 1)
def f7():
    with read_only(m):
        with torch.enable_grad():
            m(torch.randn(8, 4)).sum().backward()
probe("grads accumulated (.grad) only", f7, True)  # .grad changed -> future opt.step uses test grads
print("   .grad after eval is None?", m.weight.grad is None)

# 8 optimizer state mutated
m = nn.Linear(4, 1); opt = torch.optim.Adam(m.parameters())
m(torch.randn(2,4)).sum().backward(); opt.step(); opt.zero_grad()
def f8():
    with read_only(m):
        for g in opt.param_groups: g["lr"] = 123.0
        for st in opt.state.values(): st["exp_avg"].add_(5)
probe("optimizer state mutated", f8, True)

# 9 exception inside block masks a violation; caller treats error as wrong answer
store = CardStore()
def answer_that_writes_then_raises():
    store.write(Fact("nera", "cup", "barn")); raise KeyError("parse fail")
def f9():
    try:
        with read_only(None, [store]):
            answer_that_writes_then_raises()
    except KeyError:
        pass  # evaluator scores it as wrong and continues
probe("write then exception (caller catches)", f9, True)
print("   store now has", store.cards)

# 10 LRU-style 'touch' on read: reorders cards -> changes FIFO eviction, same fingerprint
store = CardStore(capacity=2)
store.write(Fact("a","cup","barn")); store.write(Fact("b","key","mill"))
def f10():
    with read_only(None, [store]):
        v = store.cards.pop(("a","cup")); store.cards[("a","cup")] = v   # touch
probe("card reorder (LRU touch) in CardStore", f10, True)
store.write(Fact("c","coin","shed"))
print("   after next write, evicted:", "b" if ("b","key") not in store.cards else "a", "(unreordered store would evict a)")

# 11 enabled flag left off (lesion not restored) invisible to store fingerprint
store = CardStore()
def f11():
    with read_only(None, [store]): store.enabled = False
probe("store.enabled toggled", f11, True)

# 12 RNG state consumed during eval (bit-exact resume)
m = nn.Dropout(0.5)
torch.manual_seed(0); s0 = torch.get_rng_state().clone()
def f12():
    with read_only(m): torch.randn(3)
probe("global RNG advanced during eval", f12, True)
