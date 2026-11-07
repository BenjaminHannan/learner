"""Device-agnostic batched HANDS training core.

Shared by the Mac CPU benchmark and the BensPC CUDA worker so both measure the
same step. The caller supplies already loaded examples and the pixel_model
module; nothing here reads files or assumes a platform.
"""
import random
import time

import torch


def preload(rows, load_example):
    cache = []
    for row in rows:
        image, crop, intent, own, labels, weight = load_example(row)
        cache.append((image[0], crop[0], intent[0], own[0],
                      {key: value[0] for key, value in labels.items()}, float(weight)))
    return cache


def collate(cache, picks):
    images = torch.stack([cache[i][0] for i in picks])
    crops = torch.stack([cache[i][1] for i in picks])
    intents = torch.stack([cache[i][2] for i in picks])
    owns = torch.stack([cache[i][3] for i in picks])
    labels = {key: torch.stack([cache[i][4][key] for i in picks]) for key in cache[0][4]}
    weights = torch.ones(len(picks), dtype=torch.float32)
    return images, crops, intents, owns, labels, weights


def _move(batch, device):
    images, crops, intents, owns, labels, weights = batch
    return (images.to(device), crops.to(device), intents.to(device), owns.to(device),
            {key: value.to(device) for key, value in labels.items()}, weights.to(device))


def fit(net, cache, device, pixel_model, *, steps=800, batch_size=8, lr=0.0005,
        seed=101, gate=None, zero_intent=False, on_step=None, checkpoint_path=None,
        checkpoint_every=0, save_state=None):
    """Batched equivalent of trainer.fit with the same loss and sampling."""
    gate = gate or (lambda: None)
    optimizer = torch.optim.AdamW(net.parameters(), lr=lr)
    sampler = random.Random(seed)
    weights = [example[5] for example in cache]
    curve, step_ms = [], []
    net.train()
    for step in range(steps):
        gate()
        picks = sampler.choices(range(len(cache)), weights=weights, k=batch_size)
        started = time.perf_counter()
        batch = _move(collate(cache, picks), device)
        if zero_intent:
            batch = (batch[0], batch[1], torch.zeros_like(batch[2]), batch[3], batch[4], batch[5])
        output, _ = net(*batch[:4])
        loss = pixel_model.action_loss(output, batch[4], batch[5])
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
        optimizer.step()
        if device.type == 'cuda':
            torch.cuda.synchronize()
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        loss_value = float(loss.detach())
        curve.append({'step': step, 'loss': loss_value})
        step_ms.append(elapsed_ms)
        if on_step:
            on_step(step, loss_value, elapsed_ms)
        if checkpoint_path is not None and checkpoint_every and (step + 1) % checkpoint_every == 0:
            if save_state is None:
                raise ValueError('save_state required for checkpoints')
            save_state(net, checkpoint_path)
    net.eval()
    return curve, step_ms


def eval_loss(net, cache, device, pixel_model, *, batch_size=32, zero_intent=False):
    net.eval()
    total, count = 0.0, 0
    with torch.inference_mode():
        for start in range(0, len(cache), batch_size):
            chunk = list(range(start, min(start + batch_size, len(cache))))
            batch = _move(collate(cache, chunk), device)
            if zero_intent:
                batch = (batch[0], batch[1], torch.zeros_like(batch[2]), batch[3], batch[4], batch[5])
            output, _ = net(*batch[:4])
            total += float(pixel_model.action_loss(output, batch[4], batch[5])) * len(chunk)
            count += len(chunk)
    return total / count if count else None


def timing_summary(step_ms, warmup=3):
    kept = step_ms[warmup:] if len(step_ms) > warmup else step_ms
    ordered = sorted(kept)
    return {
        'steps': len(step_ms),
        'warmupExcluded': min(warmup, len(step_ms)),
        'meanMs': (sum(kept) / len(kept)) if kept else None,
        'medianMs': ordered[len(ordered) // 2] if ordered else None,
        'totalMs': sum(step_ms),
    }
