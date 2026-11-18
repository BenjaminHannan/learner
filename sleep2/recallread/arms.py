"""The arms of Recall-then-read stage 1 and the ledger that keeps R and D3 on equal terms.

All arms read with the same reader prompt, the same 1.5k k_tokens context and 20 answer tokens; they differ only in how the QUERIES are made:
  D0   BM25(question)                                  reader: base (adapter off)
  D1   same retrieval as D0                            reader: slept (adapter on)
  D2   base closed-book key pass (40 tokens)           -> RRF(question + keys) -> base reader
  D3   round 1: BM25(question) -> base reads hits, writes 40-token keys -> round 2: RRF(question + keys) -> base reader  (equal-compute rival)
  D4   alias table keys (zero decode)                  -> RRF(question + keys) -> base reader
  R    slept LoRA-on key pass (40 tokens)              -> RRF(question + keys) -> base reader
  RD3  D3 plus R's slept keys added to round 2
  R_tau  R with keys gated by mean logprob >= tau (tau tuned on the 30 dev chains; ablation, no pass mark)
`gen(prompts, max_new, adapter)` returns one GenOut per prompt; adapter None = LoRA off, a name = that seed's LoRA on.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from . import keypass
from .retrieve import K_TOKENS, context_text, hit_at, retrieve
from .world import exact_match, has_word, is_abstain

ANS_MAX_NEW = 20
READ_SYS = "Answer with just the name. If the notes do not say, answer: unknown."
LORA_ARMS = ("D1", "R", "RD3", "R_tau")
BASE_ARMS = ("D0", "D2", "D3", "D4")  # seed-free: no LoRA anywhere, greedy, so one run serves both seeds
ALL_ARMS = ("D0", "D1", "D2", "D3", "D4", "R", "RD3", "R_tau")


@dataclass
class GenOut:
    text: str
    pieces: list[str] = field(default_factory=list)
    lps: list[float] = field(default_factory=list)
    n_prompt: int = 0
    n_new: int = 0


@dataclass
class Env:
    render: Callable      # (system, user) -> prompt string (model chat format, thinking closed)
    gen: Callable         # (prompts, max_new, adapter) -> list[GenOut]
    count_tokens: Callable
    index_full: object
    index_W: object
    alias_full: object = None
    alias_W: object = None

    def index_for(self, row):
        return self.index_W if row["index"] == "W" else self.index_full

    def alias_for(self, row):
        return self.alias_W if row["index"] == "W" else self.alias_full


def read_prompt(render, ctx: str, q: str) -> str:
    return render(READ_SYS, f"Notes from earlier chats:\n{ctx}\n\nQuestion: {q}")


def _clean(a: str) -> str:
    a = a.strip().splitlines()[0].strip() if a.strip() else ""
    return a


def _read(env, rows, rets, adapter):
    prompts = [read_prompt(env.render, context_text(env.index_for(r), ret.kept), r["q"]) for r, ret in zip(rows, rets)]
    return env.gen(prompts, ANS_MAX_NEW, adapter)


def _keys(env, rows, adapter):
    outs = env.gen([keypass.key_prompt(env.render, r["q"]) for r in rows], keypass.KEY_MAX_NEW, adapter)
    keys = [keypass.parse_keys(o.text) for o in outs]
    return outs, keys, [keypass.key_logprobs(o.pieces, o.lps, k) for o, k in zip(outs, keys)]


def _round1_keys(env, rows, rets):
    prompts = [keypass.round1_key_prompt(env.render, context_text(env.index_for(r), ret.kept), r["q"]) for r, ret in zip(rows, rets)]
    outs = env.gen(prompts, keypass.KEY_MAX_NEW, None)
    keys = [keypass.parse_keys(o.text) for o in outs]
    return outs, keys


def _row(arm, row, ret, keys, key_lps, key_outs, ans_out, rounds, extra=None):
    kin = list(key_outs)
    led = dict(key_calls=len(kin), key_max_new=keypass.KEY_MAX_NEW, key_new_tokens=[o.n_new for o in kin], read_calls=1, ans_max_new=ANS_MAX_NEW,
               k_tokens_budget=K_TOKENS, k_tokens_used=ret.k_tokens, retrieval_rounds=rounds,
               prefill_tokens=sum(o.n_prompt for o in kin) + ans_out.n_prompt, decode_tokens=sum(o.n_new for o in kin) + ans_out.n_new)
    r = dict(arm=arm, row_id=row["row_id"], split=row["split"], item=row["item"], q=row["q"], gold=row["gold"], index=row["index"], dev=row.get("dev", False),
             answer=_clean(ans_out.text), queries=ret.queries, keys=keys, key_lps=key_lps, ledger=led,
             bridge_named=(any(has_word(k, row["bridge"]) for k in keys) if (keys is not None and row.get("bridge")) else None),
             hit3_hop1=hit_at(ret.fused, row["hop1_turns"]), hit3_hop2=hit_at(ret.fused, row["hop2_turns"]),
             hop1_in_ctx=bool(set(ret.kept) & set(row["hop1_turns"])) if row["hop1_turns"] else None,
             hop2_in_ctx=bool(set(ret.kept) & set(row["hop2_turns"])) if row["hop2_turns"] else None)
    r["em"] = is_abstain(r["answer"]) if row["split"] == "never" else exact_match(row["gold"], r["answer"])
    r["key_gen"] = [(o.n_prompt, o.n_new) for o in kin]
    r.update(extra or {})
    return r


def run_arm(arm: str, rows: list[dict], env: Env, lora: str | None = None, tau_cache: dict | None = None) -> list[dict]:
    """Run one arm over `rows` (stage-synchronous: all key passes, then all retrievals, then all reads). lora: adapter name for D1/R/RD3/R_tau."""
    if arm in LORA_ARMS and not lora:
        raise ValueError(f"{arm} needs a LoRA adapter name")
    ct = env.count_tokens
    q_only = [retrieve(env.index_for(r), [r["q"]], ct) for r in rows]
    if arm in ("D0", "D1"):
        outs = _read(env, rows, q_only, lora if arm == "D1" else None)
        return [_row(arm, r, ret, None, None, [], o, 1) for r, ret, o in zip(rows, q_only, outs)]
    if arm in ("D2", "R", "R_tau"):
        if arm == "R_tau":  # R's key outputs replayed from its result rows, then gated
            rep = tau_cache["replay"]
            kouts = [GenOut("", n_prompt=rep[r["row_id"]]["key_gen"][0][0], n_new=rep[r["row_id"]]["key_gen"][0][1]) for r in rows]
            lps = [rep[r["row_id"]]["key_lps"] for r in rows]
            keys = [keypass.gate(rep[r["row_id"]]["keys"], l, tau_cache.get("tau")) for r, l in zip(rows, lps)]
        else:
            kouts, keys, lps = _keys(env, rows, lora if arm != "D2" else None)
        rets = [retrieve(env.index_for(r), [r["q"]] + k, ct) for r, k in zip(rows, keys)]
        outs = _read(env, rows, rets, None)
        ex = {"tau": (tau_cache or {}).get("tau")} if arm == "R_tau" else None
        return [_row(arm, r, ret, k, l, [ko], o, 1, ex) for r, ret, k, l, ko, o in zip(rows, rets, keys, lps, kouts, outs)]
    if arm == "D4":
        keys = [env.alias_for(r).expand(r["q"]) for r in rows]
        rets = [retrieve(env.index_for(r), [r["q"]] + k, ct) for r, k in zip(rows, keys)]
        outs = _read(env, rows, rets, None)
        return [_row(arm, r, ret, k, None, [], o, 1) for r, ret, k, o in zip(rows, rets, keys, outs)]
    if arm in ("D3", "RD3"):
        k1outs, k1 = _round1_keys(env, rows, q_only)
        extra_keys, kouts, lps = [[] for _ in rows], [], None
        if arm == "RD3":
            kouts, extra_keys, lps = _keys(env, rows, lora)
        keys = [a + [x for x in b if x not in a] for a, b in zip(k1, extra_keys)]
        rets = [retrieve(env.index_for(r), [r["q"]] + k, ct) for r, k in zip(rows, keys)]
        outs = _read(env, rows, rets, None)
        res = []
        for i, (r, ret, k, o) in enumerate(zip(rows, rets, keys, outs)):
            kin = [k1outs[i]] + ([kouts[i]] if kouts else [])
            res.append(_row(arm, r, ret, k, (lps[i] if lps else None), kin, o, 2,
                            dict(prefill_round1=q_only[i].k_tokens, keys_round1=k1[i], keys_slept=extra_keys[i] or None)))
        return res
    raise ValueError(arm)


def tune_tau(rows: list[dict], env: Env, lora: str, r_results: list[dict]) -> dict:
    """Pick tau on the dev chains (twohop_nat rows with dev=True): the candidate with the best exact-match accuracy, ties to the lowest tau.
    Candidates: no gate, plus the 20/40/60/80th percentile of the dev keys' mean logprobs. R's key outputs are replayed (no new key decoding)."""
    rr = {x["row_id"]: x for x in r_results}
    dev_rows = [r for r in rows if r.get("dev") and r["split"] == "twohop_nat"]
    allk = sorted(l for r in dev_rows for l in (rr[r["row_id"]]["key_lps"] or []) if l is not None)
    cands = [None] + (sorted({round(allk[int(p * (len(allk) - 1))], 4) for p in (0.2, 0.4, 0.6, 0.8)}) if allk else [])
    best, table = None, []
    for tau in cands:
        res = run_arm("R_tau", dev_rows, env, lora, {"tau": tau, "replay": rr})
        acc = sum(x["em"] for x in res) / max(len(res), 1)
        table.append(dict(tau=tau, dev_acc=round(acc, 4), n=len(res)))
        if best is None or acc > best[1] + 1e-12:
            best = (tau, acc)
    return dict(tau=best[0], dev_table=table)


# ---------------------------------------------------------------- ledger
EQUAL_FIELDS = ("key_calls", "key_max_new", "read_calls", "ans_max_new", "k_tokens_budget")


def assert_equal_budget(rows_a: list[dict], rows_b: list[dict], label: str = "R vs D3") -> dict:
    """R and D3 must have equal key-pass count, key decode budget, read count, answer budget and final k_tokens budget on every item, and
    neither may exceed those budgets in practice. Retrieval rounds and prefill differ by design (D3: 2 rounds and a bigger prefill, which favours D3)
    and are only summarised. Raises AssertionError on any mismatch."""
    a, b = {r["row_id"]: r["ledger"] for r in rows_a}, {r["row_id"]: r["ledger"] for r in rows_b}
    assert set(a) == set(b), f"{label}: the arms did not run the same rows"
    for k in a:
        la, lb = a[k], b[k]
        for f in EQUAL_FIELDS:
            assert la[f] == lb[f], f"{label}: ledger field {f} differs on {k}: {la[f]} vs {lb[f]}"
        assert la["key_calls"] + la["read_calls"] == lb["key_calls"] + lb["read_calls"], f"{label}: model passes differ on {k}"
        for l in (la, lb):
            assert all(n <= l["key_max_new"] for n in l["key_new_tokens"]), f"{label}: key decode over budget on {k}"
            assert l["k_tokens_used"] <= l["k_tokens_budget"], f"{label}: context over k_tokens budget on {k}"
    n = max(len(a), 1)
    mean = lambda d, f: sum(x[f] for x in d.values()) / n  # noqa: E731
    return dict(label=label, rows=len(a), prefill_a=mean(a, "prefill_tokens"), prefill_b=mean(b, "prefill_tokens"),
                decode_a=mean(a, "decode_tokens"), decode_b=mean(b, "decode_tokens"), rounds_a=mean(a, "retrieval_rounds"), rounds_b=mean(b, "retrieval_rounds"))
