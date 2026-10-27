from __future__ import annotations

from contextlib import contextmanager
from collections import Counter
import json
import random
import sys

PROJECT = "/Users/ben-hannan/Desktop/projects/beautiful-model"
with open(PROJECT + "/runtime.local.json") as handle:
    _runtime = json.load(handle)
sys.path[0:0] = _runtime.get("import_roots", [])
sys.path.insert(0, PROJECT)

import torch
from torch import nn

from learnlab.ablation import Component, judge_component
from learnlab.leaks import QAExample, leak_report
from learnlab.metrics import ContinualMatrix, bootstrap_ci, expected_calibration_error
from learnlab.readonly import ReadOnlyViolation, read_only
from learnlab.splits import SplitRegistry, assign, assign_ranked
from learnlab.toy import episodes, make_registry


def show(name, value):
    print(f"{name}: {value}")


# read_only false negatives / edge cases
m = nn.Linear(1, 1, bias=False)
initial_weight = m.weight.detach().clone()
try:
    with read_only(m):
        m.weight.add_(1.0)
        raise RuntimeError("evaluation failed")
except Exception as exc:
    show("readonly_exception_after_mutation", type(exc).__name__)
show("readonly_exception_left_weight_mutated", not torch.equal(initial_weight, m.weight.detach()))

m = nn.Linear(2, 2, bias=False)
old_id = id(m.weight)
try:
    with read_only(m):
        m.weight = nn.Parameter(m.weight.detach().clone())
    replacement_detected = False
except ReadOnlyViolation:
    replacement_detected = True
show("readonly_same_value_parameter_replacement_detected", replacement_detected)
show("readonly_parameter_identity_changed", id(m.weight) != old_id)

m = nn.Linear(2, 2, bias=False)
try:
    with read_only(m):
        m.weight.requires_grad_(False)
    requires_grad_detected = False
except ReadOnlyViolation:
    requires_grad_detected = True
show("readonly_requires_grad_change_detected", requires_grad_detected)
show("readonly_requires_grad_after", m.weight.requires_grad)

m = nn.Linear(1, 1, bias=False)
before = m.weight.detach().clone()
try:
    with read_only(m):
        m.weight.add_(1.0)
        m.weight.sub_(1.0)
    reverted_detected = False
except ReadOnlyViolation:
    reverted_detected = True
show("readonly_mutate_then_revert_detected", reverted_detected)
show("readonly_mutate_then_revert_equal", torch.equal(before, m.weight.detach()))

m = nn.Linear(1, 1)
optimizer = torch.optim.Adam(m.parameters(), lr=1e-3)
p = next(iter(m.parameters()))
optimizer.state[p]["step"] = torch.tensor(7.0)
try:
    with read_only(m):
        optimizer.state[p]["step"].add_(1)
    optimizer_state_detected = False
except ReadOnlyViolation:
    optimizer_state_detected = True
show("readonly_optimizer_state_only_detected", optimizer_state_detected)
show("readonly_optimizer_step_after", float(optimizer.state[p]["step"]))

class NoFingerprint:
    pass

try:
    with read_only(None, [NoFingerprint()]):
        pass
except Exception as exc:
    show("readonly_store_without_fingerprint", type(exc).__name__)

m = nn.Module()
m.register_buffer("scratch", torch.tensor(1.0), persistent=False)
try:
    with read_only(m):
        m.scratch.add_(1.0)
    nonpersistent_detected = False
except ReadOnlyViolation:
    nonpersistent_detected = True
show("readonly_nonpersistent_buffer_detected", nonpersistent_detected)

m = nn.Module()
try:
    with read_only(m):
        m.new_parameter = nn.Parameter(torch.tensor(1.0))
    added_parameter_detected = False
except ReadOnlyViolation:
    added_parameter_detected = True
show("readonly_added_parameter_detected", added_parameter_detected)

m = nn.Module()
m.register_buffer("buf", torch.tensor(1.0))
try:
    with read_only(m):
        del m.buf
    removed_buffer_detected = False
except ReadOnlyViolation:
    removed_buffer_detected = True
show("readonly_removed_buffer_detected", removed_buffer_detected)


# split false negatives / edge cases
r = SplitRegistry()
# Simulate a buggy generator using the same item in train and test without record().
simulated_actual_use = {"train": {"n0"}, "test": {"n0"}}
try:
    r.assert_disjoint()
    omitted_record_caught = False
except Exception:
    omitted_record_caught = True
show("split_omitted_record_caught", omitted_record_caught)
show("split_simulated_actual_overlap", bool(simulated_actual_use["train"] & simulated_actual_use["test"]))

rank3 = assign_ranked("template", ["a", "b", "c"])
show("split_rank3_counts_default", dict(Counter(rank3.values())))

base = [f"t{i}" for i in range(8)]
base_map = assign_ranked("template", base)
shift = None
for i in range(1000):
    extra = f"extra{i}"
    new_map = assign_ranked("template", base + [extra])
    moved = [(x, base_map[x], new_map[x]) for x in base if base_map[x] != new_map[x]]
    if moved:
        shift = (extra, moved[0])
        break
show("split_membership_change_example", shift)

small_names = [f"n{i}" for i in range(3)]
small_counts = Counter(assign("name", n) for n in small_names)
show("split_small_name_pool_counts", dict(small_counts))

toy_registry = make_registry()
for split in ("train", "validation", "test"):
    episodes(toy_registry, split, 10)
show("split_toy_rule_family_counts", toy_registry.summary()["rule_family"])

try:
    invalid_rank = assign_ranked("template", [f"x{i}" for i in range(8)], fractions=(1.2, -0.1, -0.1))
    show("split_invalid_rank_fractions", dict(Counter(invalid_rank.values())))
except Exception as exc:
    show("split_invalid_rank_fractions", type(exc).__name__)

if shift is not None:
    extra, (moved_item, old_split, new_split) = shift
    r2 = SplitRegistry()
    r2.fix_family("template", base)
    r2.record("template", moved_item, old_split)
    r2.fix_family("template", base + [extra])
    try:
        r2.assert_disjoint()
        stale_family_caught = False
    except Exception:
        stale_family_caught = True
    show("split_refixed_family_stale_record_caught", stale_family_caught)
    show("split_refixed_family_now_assigns", r2.split_of("template", moved_item))


# leak detector false negatives
answers = ["red", "blue", "green", "gold"]
def first_line_dataset(n):
    out = []
    for i in range(n):
        answer = answers[i % len(answers)]
        rest = [a for a in answers if a != answer]
        rng = random.Random(i)
        rng.shuffle(rest)
        order = [answer] + rest
        context = "\n".join(f"{a} marker" for a in order)
        out.append(QAExample(context, "which marker?", answer))
    return out

first_train = first_line_dataset(400)
first_test = first_line_dataset(200)
first_report = leak_report(first_train, first_test)
first_rule_acc = sum(ex.context.split()[0] == ex.answer for ex in first_test) / len(first_test)
show("leak_first_line_rule_accuracy", first_rule_acc)
show("leak_first_line_report", first_report.as_dict())

order_train = []
order_test = []
for i in range(240):
    answer = "left" if i % 2 == 0 else "right"
    context = "alpha beta" if answer == "left" else "beta alpha"
    ex = QAExample(context, "choose", answer)
    (order_train if i < 160 else order_test).append(ex)
order_report = leak_report(order_train, order_test)
order_rule_acc = sum(((ex.context == "alpha beta") == (ex.answer == "left")) for ex in order_test) / len(order_test)
show("leak_word_order_rule_accuracy", order_rule_acc)
show("leak_word_order_report", order_report.as_dict())

# Direct answer leakage on 30% of examples: this one should be caught.
partial_train = []
partial_test = []
for i in range(800):
    answer = answers[i % 4]
    leak = (i % 10) < 3
    question = f"which? {answer}" if leak else "which?"
    ex = QAExample("neutral context", question, answer)
    (partial_train if i < 400 else partial_test).append(ex)
partial_report = leak_report(partial_train, partial_test)
show("leak_direct_30pct_report", partial_report.as_dict())

# Last-line target on 60% of examples: this should also be caught.
last_train = []
last_test = []
for i in range(800):
    answer = answers[i % 4]
    others = [a for a in answers if a != answer]
    if (i % 10) < 6:
        order = others + [answer]
    else:
        order = [answer] + others
    ex = QAExample("\n".join(f"{a} marker" for a in order), "which marker?", answer)
    (last_train if i < 400 else last_test).append(ex)
last_report = leak_report(last_train, last_test)
show("leak_target_last_60pct_report", last_report.as_dict())

# Search for a small iid clean sample that gets flagged purely by sampling noise.
false_positive = None
for seed in range(5000):
    rng = random.Random(seed)
    train = []
    test = []
    for i in range(48):
        token = rng.choice(["x", "y"])
        answer = rng.choice(["a", "b"])
        ex = QAExample(token, "q", answer)
        (train if i < 40 else test).append(ex)
    report = leak_report(train, test)
    if report.leaking:
        false_positive = (seed, report.as_dict(), Counter(x.answer for x in test))
        break
show("leak_iid_small_sample_false_positive", false_positive)


# ablation false positives / weak guards
calls = {"n": 0}
def drifting_eval():
    calls["n"] += 1
    return [1.0] * 20 if calls["n"] == 1 else [0.0] * 20

@contextmanager
def noop():
    yield

drift_verdict = judge_component(Component("noop", noop), drifting_eval, {"weak": [0.0] * 20})
show("ablation_noop_passes_when_evaluate_drifts", drift_verdict.as_dict())

state = {"on": True}
@contextmanager
def broken_lesion():
    state["on"] = False
    yield
    # deliberately does not restore

def state_eval():
    return [1.0 if state["on"] else 0.0] * 20

broken_verdict = judge_component(Component("broken_restore", broken_lesion), state_eval, {"weak": [0.0] * 20})
show("ablation_broken_restore_passed", broken_verdict.passed)
show("ablation_state_after_broken_restore", state["on"])

tiny_state = {"on": True}
@contextmanager
def tiny_toggle():
    tiny_state["on"] = False
    try:
        yield
    finally:
        tiny_state["on"] = True

def tiny_eval():
    return [1.0 if tiny_state["on"] else 0.0] * 4

tiny_verdict = judge_component(Component("tiny", tiny_toggle), tiny_eval, {"weak": [0.0] * 4})
show("ablation_n4_percentile_bootstrap_passed", tiny_verdict.passed)
show("ablation_n4_lesion_ci", tiny_verdict.lesion_drop)
show("ablation_n4_exact_one_sided_sign_p", 1 / 16)

small_gain_state = {"on": True}
@contextmanager
def small_gain_toggle():
    small_gain_state["on"] = False
    try:
        yield
    finally:
        small_gain_state["on"] = True

def small_gain_eval():
    return [0.501 if small_gain_state["on"] else 0.500] * 100

small_gain = judge_component(Component("tiny_gain", small_gain_toggle), small_gain_eval, {"base": [0.5] * 100})
show("ablation_default_zero_margin_allows_0p1pp", small_gain.passed)
show("ablation_default_zero_margin_ci", small_gain.baseline_margins["base"])


# metrics definitions / edge cases
cm = ContinualMatrix(3)
rows = [[0.8, 0.9, 0.1], [0.8, 0.6, 0.1], [0.8, 0.5, 0.9]]
for i, row in enumerate(rows):
    for j, value in enumerate(row):
        cm.record(i, j, value)
impl_forgetting = cm.forgetting()
chaudhry_style = ((max(rows[0][0], rows[1][0]) - rows[2][0]) + (max(rows[0][1], rows[1][1]) - rows[2][1])) / 2
show("metrics_forgetting_impl", impl_forgetting)
show("metrics_forgetting_max_all_prior_stages", chaudhry_style)

cm2 = ContinualMatrix(2)
cm2.record(-1, 0, 0.7)
show("metrics_negative_stage_silently_writes_last_row", cm2.scores)

try:
    ece0 = expected_calibration_error([0.9, 0.1], [True, False], bins=0)
    show("metrics_ece_bins_zero", ece0)
except Exception as exc:
    show("metrics_ece_bins_zero", type(exc).__name__)

try:
    bootstrap_ci([0.0, 1.0], samples=0)
except Exception as exc:
    show("metrics_bootstrap_samples_zero", type(exc).__name__)

show("cuda_available", torch.cuda.is_available())
