"""Fast CPU contracts for recovery candidates; no training wave or test-split access."""
from dataclasses import asdict, replace
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import premonition_recovery as C


def main():
    C.L.bootstrap()
    import torch
    torch.set_num_threads(1)
    batch = next(C.L.checked_train())[0]
    checks = 0

    def check(label, ok):
        nonlocal checks
        assert bool(ok), label
        checks += 1
        print("PASS " + label, flush=True)

    def losses(model, mode="teacher", p=0.0, weights=None):
        return model(batch, mode=mode, p_own=p, weights=weights,
                     generator=torch.Generator().manual_seed(77))

    def episode(model, data=batch):
        hidden = model.read(data)
        store = model.build_store(hidden, data)
        ep = model._start(data, hidden, store, model._mentions(data))
        index = torch.arange(data.q_visit.numel())
        return store, ep, index

    base = C.R.build("bypass-k1", 0)
    legacy = C.build(0)
    check("disabled options preserve all checkpoint keys and tensors",
          base.state_dict().keys() == legacy.state_dict().keys()
          and all(torch.equal(v, legacy.state_dict()[k]) for k, v in base.state_dict().items()))
    with torch.no_grad():
        for mode, p in (("gold", 0.0), ("teacher", 0.0), ("own", 0.75)):
            a, b = losses(base, mode, p), losses(legacy, mode, p)
            check(f"disabled options: exact {mode} loss parity",
                  all(torch.equal(a[k], b[k]) for k in ("lm", "ans", "ask", "halt", "loss")))
    kp = C.build(0, key_pool=True)
    with torch.no_grad():
        a, b = losses(legacy), losses(kp)
    check("key pooling starts with identical losses and adds 33 parameters",
          kp.num_parameters() == legacy.num_parameters() + 33
          and all(torch.equal(a[k], b[k]) for k in ("lm", "ans", "ask", "halt", "loss")))

    model = C.build(0, request="pooled", key_pool=True)
    check("pooled selectors add exactly 5202 parameters", model.num_parameters() == kp.num_parameters() + 5202)
    check("all historical weights retained unchanged", all(torch.equal(v, model.state_dict()[k])
                                                             for k, v in kp.state_dict().items()))
    check("no supplied relation location or relation-wire parameters",
          not any("relcut" in k or "shortcut" in k for k in model.state_dict()))
    store, ep, index = episode(model)
    old_question = ep.request_question.clone()
    rows, _, _, scores = model._step(ep, index, 0, store)
    check("Think does not overwrite original question candidates", torch.equal(old_question, ep.request_question))
    cards = store.top(scores, 1)
    raw, _, _ = store.gather(cards, ep.q_visit)
    model._insert(ep, store, index, cards)
    check("selector cards are raw fetched pooled values", torch.equal(ep.request_cards[:, 0], raw[:, 0]))
    old_cards = ep.request_cards.clone()
    rows, _, _, _ = model._step(ep, index, 1, store)
    check("Think does not overwrite fetched selector candidates", torch.equal(old_cards, ep.request_cards))
    query, attention = model._request(ep, index, rows)
    valid = torch.cat([ep.request_valid, ep.valid[:, model._card_slice]], 1)
    check("all unavailable candidates have exactly zero attention",
          (attention[:, :, :-1].masked_select(~valid[:, None].expand(-1, 2, -1)) == 0).all())
    changed_ep = replace(ep)
    changed_ep.request_question = ep.request_question.clone()
    changed_ep.request_valid = ep.request_valid
    changed_ep.request_cards = ep.request_cards + 10 * ep.valid[:, model._card_slice, None]
    changed_query, _ = model._request(changed_ep, index, rows)
    check("next request depends on fetched content", not torch.equal(query, changed_query))
    request_rows = rows.detach().clone().requires_grad_()
    q, _ = model._request(ep, index, request_rows)
    q[:, 0].sum().backward()
    check("request conditions on register 1, not control register 0",
          request_rows.grad[:, model._register_base + 1].abs().sum() > 0
          and request_rows.grad[:, model._register_base].abs().sum() == 0)
    for i in range(model.config.card_rows + 2):
        pick = torch.full_like(cards, store.null if i % 2 else 0)
        if i == 1:
            pick[::2] = -1
        before = ep.count.clone()
        old = ep.request_cards.clone()
        val, _, _ = store.gather(pick, ep.q_visit)
        real = pick[:, 0] >= 0
        old[index[real], before[real] % model.config.card_rows] = val[real, 0]
        model._insert(ep, store, index, pick)
        check(f"ring buffer tracks null, missing and evicted cards ({i})", torch.equal(ep.request_cards, old))
    selector = model.heads.address
    d = model.config.d_model
    empty_candidates = torch.randn(2, 3, d)
    empty_valid = torch.zeros(2, 3, dtype=torch.bool)
    for hard in (False, True):
        empty_query, attn = selector(torch.randn(2, d), empty_candidates, empty_valid, hard=hard)
        check(f"NULL handles empty candidates without NaN (hard={hard})",
              torch.isfinite(empty_query).all() and (attn[:, :, -1] == 1).all())

    def trace(data):
        with torch.no_grad():
            store, ep, ids = episode(model, data)
            result = []
            for step in range(4):
                _, _, ask, scores = model._step(ep, ids, step, store)
                result.extend([scores.clone(), ask.clone()])
                if step < 3:
                    model._insert(ep, store, ids, store.top(scores, 1))
            return result

    normal = trace(batch)
    changed = trace(replace(batch, gold_lines=torch.full_like(batch.gold_lines, -1),
                            answer=batch.answer.roll(1, 0), slices={}))
    check("all requests invariant to answer, gold-evidence and slice labels",
          all(torch.equal(a, b) for a, b in zip(normal, changed)))

    model.zero_grad(set_to_none=True)
    losses(model)["ask"].backward()
    check("search loss reaches both selector heads and the key pool",
          all(p.grad is not None and p.grad.abs().sum() > 0 for p in model.heads.address.parameters())
          and model.writer.key_pool.weight.grad.abs().sum() > 0)
    check("legacy query remains dormant in pooled mode", model.heads.query.weight.grad is None)
    answer_only = dict(lm=0.0, ask=0.0, ans=1.0, halt=0.0)
    plain = C.build(0, key_pool=True)
    credit = C.build(0, key_pool=True, score_only_st=True)
    a, b = losses(plain, weights=answer_only), losses(credit, weights=answer_only)
    check("score-only ST preserves hard-forward answer loss exactly", torch.equal(a["loss"], b["loss"]))
    a["loss"].backward()
    b["loss"].backward()
    retrieval = ("heads.query.weight", "writer.key.weight", "writer.key_pool.weight", "heads.log_kappa")
    pd, cd = dict(plain.named_parameters()), dict(credit.named_parameters())
    check("answer loss has no retrieval gradient in the hard baseline",
          all(pd[n].grad is None or pd[n].grad.abs().sum() == 0 for n in retrieval))
    check("answer loss reaches query, key, key pooling and scale through score-only ST",
          all(cd[n].grad is not None and cd[n].grad.abs().sum() > 0 for n in retrieval))
    with torch.no_grad():
        plain.eval()
        credit.eval()
        ap, _ = C.R.own_fixed(plain, batch, 4)
        ac, _ = C.R.own_fixed(credit, batch, 4)
        check("score-only ST keeps hard evaluation identical", torch.equal(ap, ac))
    store, ep, ids = episode(credit)
    values = store.values.detach().requires_grad_()
    null_value = store.null_value.detach().requires_grad_()
    detached_store = replace(store, values=values, null_value=null_value)
    scores = torch.randn(ids.numel(), store.lines + 1, requires_grad=True)
    credit._ins_scores, credit.insert_mode = scores, "st"
    value, _ = credit._soft_parts(detached_store, ep, ids)
    value.sum().backward()
    check("surrogate adds score gradients without direct value/null gradients",
          scores.grad.abs().sum() > 0 and values.grad is None and null_value.grad is None)
    credit._ins_scores, credit.insert_mode = None, "hard"

    combined = C.build(0, request="pooled", key_pool=True, score_only_st=True)
    combined_loss = losses(combined, weights=answer_only)["loss"]
    combined_loss.backward()
    check("answer-only credit composes with pooled selectors",
          all(p.grad is not None and p.grad.abs().sum() > 0 for p in combined.heads.address.parameters()))
    optimizer = torch.optim.AdamW(combined.parameters(), lr=1e-3)
    optimizer.step()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "model.pt"
        C.S.save_atomic(dict(format=C.FORMAT, config=asdict(combined.config),
                             recovery_options=combined.recovery_options, state_dict=combined.state_dict()), path)
        restored, _ = C.load(path)
        with torch.no_grad():
            a, b = losses(combined), losses(restored)
        check("checkpoint round-trip restores options and trained behavior exactly",
              restored.recovery_options == combined.recovery_options
              and all(torch.equal(a[k], b[k]) for k in ("lm", "ans", "ask", "halt", "loss")))
        import premonition_first_card_probe as P
        suite_model, _ = P.load_from("model", tmp)
        check("existing first-card and causal-pair suite loader accepts recovery checkpoints",
              P.fingerprint(suite_model) == P.fingerprint(combined) and not suite_model.training)
    print(f"ALL {checks} CHECKS PASSED", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
