"""ST1, self-taught traces (B3 group 2 sec. 5, architecture/B3-GROUP2-BUILD-2026-10-09.md): a stage that runs on a trained checkpoint, no new parts.
Q/A rows (no steps) of kinds held out of all trace teaching. Each round: for every question sample k traces (the model's own calls, the tool's real
replies, its answer; temperature fixed), keep the traces whose answer is right (the only hand part: at deployment, the world's feedback or a check
tool), train `updates` steps on batches that are half kept traces (model.trace_loss, teacher forced) and half ordinary training rows (model.loss).
All constants are fixed by the defaults (rounds 3, k 4, temperature 1.0, updates 500, lr 1e-4, batch 64, grad clip 1.0 as train.py): disclosed,
not tuned. Disclosed choices: identical traces of one question are kept once; the right-answer check is evalx.is_hit when the row has `accepted`,
else exact match after strip / lower; a round with nothing kept trains nothing (counted as `stalled`) and the next round samples again.
Model interface (another worker provides it):
  model.sample_traces(batch, temperature, generator) -> per row dict(calls=[(call_text, reply_text)], answer=str)
  model.trace_loss(batch, traces) -> (loss tensor, aux dict)      teacher forced on the given traces
  model.loss(batch) -> (loss tensor, aux dict)                    the ordinary loss
Draws only from torch.Generator(seed) (sampling) and random.Random(seed) (batch choice); nothing else is consumed."""
import random
import torch
from custom_io import evalx


def right(answer, row):
    """The answer check: evalx.is_hit against the row's accepted answers, else exact match after strip / lower."""
    if row.get('accepted'):
        return evalx.is_hit(answer, row)
    return str(answer).strip().lower() == str(row['answer']).strip().lower()


def kind_of(row):
    return row.get('family') or row.get('kind') or '?'


def sample_round(model, qa_rows, make_batch, k, temperature, batch_size, gen):
    """-> (kept [(row, trace)], stats). k traces per question, in chunks of batch_size questions; no gradients, model in eval mode."""
    was = model.training
    model.eval()
    kept, asked, samples, hit, got = [], {}, {}, {}, {}
    seen = {}
    with torch.no_grad():
        for i in range(0, len(qa_rows), batch_size):
            rows = qa_rows[i:i + batch_size]
            for j in range(k):
                traces = model.sample_traces(make_batch(rows), temperature, gen)
                assert len(traces) == len(rows), (len(traces), len(rows))
                for r, t in zip(rows, traces):
                    kd = kind_of(r)
                    if j == 0:
                        asked[kd] = asked.get(kd, 0) + 1
                    samples[kd] = samples.get(kd, 0) + 1
                    if not right(t['answer'], r):
                        continue
                    key = (r.get('id', id(r)), tuple(map(tuple, t['calls'])), t['answer'])
                    if key in seen:
                        continue
                    seen[key] = 1
                    kept.append((r, t))
                    hit[kd] = hit.get(kd, 0) + 1
                    got[(r.get('id', id(r)))] = 1
    model.train(was)
    return kept, dict(asked=asked, samples=samples, kept=hit, questions_with_kept=len(got))


def self_teach(model, qa_rows, train_rows, make_batch, opt, rounds=3, k=4, temperature=1.0, updates=500, lr=1e-4, batch_size=64, seed=0, log=print):
    """-> dict(rounds=[per-round stats], config). Per round stats: asked / samples / kept per kind, kept total, questions_with_kept, updates done,
    stalled (nothing kept: no training), first / last loss."""
    gen, rng = torch.Generator().manual_seed(seed), random.Random(seed)
    out = dict(config=dict(rounds=rounds, k=k, temperature=temperature, updates=updates, lr=lr, batch_size=batch_size, seed=seed), rounds=[])
    nk = batch_size // 2
    for rd in range(rounds):
        kept, st = sample_round(model, qa_rows, make_batch, k, temperature, batch_size, gen)
        st.update(round=rd + 1, kept_total=len(kept), updates=0, stalled=not kept, loss_first=None, loss_last=None)
        log(f"[st1] round {rd + 1}: kept {len(kept)} of {sum(st['samples'].values())} samples; by kind "
            + ', '.join(f"{kd} {st['kept'].get(kd, 0)}/{st['samples'][kd]}" for kd in sorted(st['samples'])))
        if kept:
            for g in opt.param_groups:
                g['lr'] = lr
            model.train()
            for u in range(updates):
                kb = rng.sample(kept, nk) if len(kept) >= nk else rng.choices(kept, k=nk)
                ob = rng.sample(train_rows, batch_size - nk) if len(train_rows) >= batch_size - nk else rng.choices(train_rows, k=batch_size - nk)
                lt, _ = model.trace_loss(make_batch([r for r, _ in kb]), [t for _, t in kb])
                lo, _ = model.loss(make_batch(ob))
                loss = 0.5 * lt + 0.5 * lo                       # 1:1 mix
                opt.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_([p for g in opt.param_groups for p in g['params']], 1.0)
                opt.step()
                st['updates'] += 1
                if u == 0:
                    st['loss_first'] = loss.item()
                st['loss_last'] = loss.item()
            log(f"[st1] round {rd + 1}: {st['updates']} updates, loss {st['loss_first']:.4f} -> {st['loss_last']:.4f}")
        else:
            log(f'[st1] round {rd + 1}: nothing kept, no training')
        out['rounds'].append(st)
    return out
