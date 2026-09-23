#!/usr/bin/env python3
"""Registered check for experiment 61: ModernBERT eager reseal (design doc 66).

Imports the experiment-58 loader (scripts/fable_modernbert58_loader.py, NOT edited)
and compares it against the transformers reference loaded TWICE -- once with
attn_implementation='eager' and once with 'sdpa' -- on 40 NEW sentences
(20 scientific-abstract style incl. long 80-120 token ones, 20 everyday;
none from the 58 sentence list), fp32, CPU.

Sealed marks (artifacts/fable-modernbert61-20260921/PASSMARKS.md):
  E1 token ids match reference on 40/40 sentences
  E2 max last-hidden |ours - eager| < 1e-4 over all 40
  E3 max last-hidden |ours - sdpa|  < 1e-3 over all 40 (recorded)
  E4 per-token char spans cover the text (whitespace-only gaps) on 40/40
  E5 padded-batch vs single-sentence max diff < 1e-4
Also measured and reported (no mark): CPU forward ms/sentence at batch 1
and batch 16, and peak RSS.

Run (Mac CPU, snapshot cached, no network):
  export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
  uv run --offline --no-project --python 3.12 --with torch --with numpy \\
    --with transformers python -B scripts/fable_modernbert61_check.py \\
    $HOME/.cache/huggingface/hub/models--answerdotai--ModernBERT-base/snapshots/8949b909ec900327062f0ebf497f51aef5e6f0c8
"""
from __future__ import annotations

import argparse
import os
import resource
import sys
import time
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fable_modernbert58_loader import load  # noqa: E402 (reused, not edited)

import torch  # noqa: E402

MAX_LEN = 512

# ---------------------------------------------------------------- 20 scientific
SCI = [
    "We study how protein folding rates depend on solvent viscosity and temperature.",
    "CRISPR screens identified three novel regulators of mitochondrial biogenesis in HeLa cells.",
    "The catalyst achieved 94% selectivity at 320 Kelvin and ambient pressure (Table 2).",
    "RNA sequencing of 214 tumour samples revealed a conserved interferon signature (p < 0.001).",
    "We prove convergence of the stochastic optimizer under non-convex Lipschitz assumptions.",
    "Ocean pH declined by 0.11 units since 1850, threatening calcifying plankton (Fig. 3).",
    "A 12-week trial (n = 1,408) found systolic pressure fell 6.2 mmHg versus placebo.",
    "Gravitational lensing maps dark matter filaments between galaxy clusters at z ~ 0.4.",
    "We report a compiler pass that cuts register spills by 31% on SPECint 2017 benchmarks.",
    "Dendritic calcium spikes gate synaptic plasticity during slow-wave sleep in mice.",
    "Quantum error rates dropped below threshold after dynamical decoupling (Section 4.1).",
    "Satellite telemetry shows Arctic sea-ice extent shrinking 13% per decade since 1979.",
    "We introduce a finite-element scheme for fracture propagation in heterogeneous rock.",
    "Gut microbiome diversity predicted vaccine response better than age or sex (AUC 0.81).",
    # long ones (target 80-120 BPE tokens each)
    "We present a longitudinal analysis of 2,340 patients in which whole-genome sequencing, "
    "proteomic profiling, and clinical imaging were combined to stratify risk of cardiovascular "
    "events over ten years; a gradient-boosted model reached an area under the curve of 0.87, "
    "outperforming traditional Framingham scores by eleven points, and ablation studies confirmed "
    "that imaging features contributed most to early-stage predictions (see Supplementary Table 6).",
    "Our field experiment across 48 grassland plots shows that nitrogen deposition above 25 kg per "
    "hectare per year reduces plant species richness by 19%, alters mycorrhizal colonization, and "
    "shifts decomposition dynamics, with effects persisting three seasons after treatment ended; "
    "mixed-effects models accounting for rainfall and soil pH confirm the decline is significant "
    "at the 1% level in every bioregion surveyed (Methods, Extended Data Fig. 4).",
    "We derive closed-form bounds for the generalization error of overparameterized networks trained "
    "with label noise, showing that early stopping at the interpolation threshold recovers Bayes-optimal "
    "risk whenever the noise rate stays below 20%; experiments on CIFAR-10, ImageNet subsets, and two "
    "medical imaging benchmarks support the theory, and Appendix C extends the result to transformers "
    "with rotary position embeddings under mild spectral assumptions.",
    "A randomized controlled trial of 3,112 adults with treatment-resistant depression compared "
    "ketamine-assisted psychotherapy against electroconvulsive therapy over 24 weeks, finding remission "
    "rates of 52% versus 47% with fewer reported adverse events in the ketamine arm; secondary outcomes "
    "included sleep quality, cognitive battery scores, and relapse at twelve months, all pre-registered "
    "(ClinicalTrials.gov NCT0XXXXXX) and analysed by intention to treat with multiple imputation.",
    "We reconstruct Holocene temperature variability from 214 lake-sediment cores spanning six continents, "
    "applying Bayesian age-depth modelling and alkenone paleothermometry to resolve centennial-scale "
    "fluctuations; the composite record reveals a coherent Medieval warm anomaly of +0.4 degrees Celsius "
    "and confirms that twentieth-century warming exceeds any century in the past 2,000 years with posterior "
    "probability above 0.99 (Supplementary Information, Section 9).",
    "This paper proposes a distributed consensus protocol tolerant to one-third Byzantine faults that "
    "commits transactions in two network round trips under synchrony and degrades gracefully otherwise; "
    "evaluated on 128 cloud nodes across five regions, it sustains 41,000 operations per second at 190 ms "
    "median latency, and formal verification in TLA+ covers safety for arbitrary message reorderings "
    "plus liveness whenever the network stabilizes for at least nine seconds (Section 7).",
]

# ----------------------------------------------------------------- 20 everyday
EVERYDAY = [
    "Can you pick up milk and bread on your way home tonight?",
    "The bus was ten minutes late, so I walked to the library instead.",
    "Happy birthday! I hope your trip to the coast was wonderful.",
    "My neighbour's dog barks every morning at six o'clock sharp.",
    "We watched three episodes last night and fell asleep on the couch.",
    "The plumber quoted four hundred dollars to fix the leaking sink.",
    "Did you remember to lock the back door before we left?",
    "She scored the winning goal two minutes before full time.",
    "Our flight boards at gate 14B; please arrive an hour early.",
    "I have been learning to bake sourdough since January this year.",
    "The kids built a snowman taller than their dad in the park.",
    "Please send me the photos from Saturday's barbecue when you can.",
    "He reads about twenty pages every night before turning off the lamp.",
    "The café on Fifth Street makes the best cinnamon rolls in town.",
    "They moved into a small blue house near the railway station.",
    "My phone battery died right in the middle of the video call.",
    "We need flour, sugar, eggs, butter, and vanilla for the cake.",
    "The dentist appointment got rescheduled to Thursday afternoon.",
    "She tied her shoes, grabbed her umbrella, and ran for the train.",
    "Our team won five games in a row and lost only twice all season.",
]

SENTENCES: list[str] = SCI + EVERYDAY
assert len(SENTENCES) == 40
assert len(SCI) == 20 and len(EVERYDAY) == 20


def spans_cover(text: str, spans: list[tuple[int, int]]) -> tuple[bool, str]:
    """Body spans (excluding CLS/SEP) must cover every non-whitespace char.

    NOTE (fixed before the registered re-run): the first version required the
    spans to tile without overlap. That is wrong -- subword pieces of one
    pre-token word all carry that word's span, so identical spans legitimately
    repeat. The sealed bar only requires coverage with whitespace-only gaps,
    which is the union test implemented here.
    """
    t = unicodedata.normalize("NFC", text)
    body = spans[1:-1]
    if not body:
        return (len(t.strip()) == 0, "empty body on non-blank text")
    covered = bytearray(len(t))
    for k, (a, b) in enumerate(body):
        if not (0 <= a <= b <= len(t)):
            return False, f"span {k} ({a},{b}) out of bounds (len {len(t)})"
        if a == b:
            return False, f"span {k} is empty"
        for p in range(a, b):
            covered[p] = 1
    bad = [p for p in range(len(t)) if not covered[p] and not t[p].isspace()]
    if bad:
        return False, f"{len(bad)} non-ws chars uncovered, first at {bad[0]}: {t[max(0, bad[0]-10):bad[0]+10]!r}"
    return True, "ok"


def main(snapshot: str) -> int:
    from transformers import AutoModel, AutoTokenizer  # reference library, Mac only

    t0 = time.time()
    ours, tok, info = load(snapshot)
    load_s = info["load_s"]
    assert ours.emb.weight.dtype == torch.float32, ours.emb.weight.dtype
    ref_tok = AutoTokenizer.from_pretrained(snapshot)
    ref_eager = AutoModel.from_pretrained(
        snapshot, attn_implementation="eager", torch_dtype=torch.float32
    ).eval()
    ref_sdpa = AutoModel.from_pretrained(
        snapshot, attn_implementation="sdpa", torch_dtype=torch.float32
    ).eval()
    for ref in (ref_eager, ref_sdpa):
        assert ref.config.torch_dtype in (torch.float32, None) or True
        assert next(ref.parameters()).dtype == torch.float32

    n_tok_ok, n_span_ok = 0, 0
    worst_eager, worst_sdpa = 0.0, 0.0
    worst_tok_len = 0
    singles: list[torch.Tensor] = []
    with torch.no_grad():
        for s in SENTENCES:
            ids, spans = tok.encode(s, MAX_LEN)
            ref_ids = ref_tok(s, truncation=True, max_length=MAX_LEN)["input_ids"]
            match = ids == ref_ids
            n_tok_ok += match
            if not match:
                print("token mismatch:", repr(s[:60]), ids[:16], ref_ids[:16])
            worst_tok_len = max(worst_tok_len, len(ids))
            ok, why = spans_cover(s, spans)
            n_span_ok += ok
            if not ok:
                print("span gap:", repr(s[:60]), why)
            x = torch.tensor([ids])
            m = torch.ones_like(x, dtype=torch.bool)
            h_ours = ours(x, m)
            singles.append(h_ours[0].detach())
            h_e = ref_eager(input_ids=x, attention_mask=m.long()).last_hidden_state
            h_s = ref_sdpa(input_ids=x, attention_mask=m.long()).last_hidden_state
            worst_eager = max(worst_eager, (h_ours - h_e).abs().max().item())
            worst_sdpa = max(worst_sdpa, (h_ours - h_s).abs().max().item())
        # E5: one padded batch of all 40 vs the singles
        ids_b, mask_b, _ = tok.batch(SENTENCES, MAX_LEN)
        hb = ours(ids_b, mask_b)
        pad_diff = 0.0
        for i in range(len(SENTENCES)):
            n = int(mask_b[i].sum())
            pad_diff = max(pad_diff, (hb[i, :n] - singles[i][:n]).abs().max().item())
        # timing (no mark): warmup then batch-1 and batch-16 means
        for i in range(len(SENTENCES)):
            n = int(mask_b[i].sum())
            ours(ids_b[i : i + 1, :n], mask_b[i : i + 1, :n])
        r = 3
        t1 = time.time()
        for _ in range(r):
            for i in range(len(SENTENCES)):
                n = int(mask_b[i].sum())
                ours(ids_b[i : i + 1, :n], mask_b[i : i + 1, :n])
        ms_b1 = (time.time() - t1) / (r * len(SENTENCES)) * 1000
        t2 = time.time()
        for _ in range(r):
            for j in range(0, len(SENTENCES), 16):
                sl = slice(j, j + 16)
                ours(ids_b[sl], mask_b[sl])
        ms_b16 = (time.time() - t2) / (r * len(SENTENCES)) * 1000
    total_s = time.time() - t0
    rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6  # bytes on macOS

    e1 = n_tok_ok == 40
    e2 = worst_eager < 1e-4
    e3 = worst_sdpa < 1e-3
    e5 = pad_diff < 1e-4
    e4 = n_span_ok == 40
    print(f"params {info['params']:,}  skipped {info['skipped']}")
    print(f"E1 token ids {n_tok_ok}/40")
    print(f"E2 max|ours-eager| {worst_eager:.2e}  (bar < 1e-4)")
    print(f"E3 max|ours-sdpa|  {worst_sdpa:.2e}  (bar < 1e-3, recorded)")
    print(f"E4 span cover {n_span_ok}/40  longest {worst_tok_len} tokens")
    print(f"E5 pad-vs-single {pad_diff:.2e}  (bar < 1e-4)")
    print(f"timing: batch1 {ms_b1:.1f} ms/sent, batch16 {ms_b16:.1f} ms/sent, "
          f"peakRSS {rss_mb:.0f} MB (recorded, no mark)")
    print(f"load {load_s:.1f}s  check-total {total_s:.1f}s")
    marks = [("E1", e1), ("E2", e2), ("E3", e3), ("E4", e4), ("E5", e5)]
    for name, ok in marks:
        print(f"{name} {'PASS' if ok else 'FAIL'}")
    print("CHECK", "PASS" if all(ok for _, ok in marks) else "FAIL")
    return 0 if all(ok for _, ok in marks) else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("snapshot", help="ModernBERT-base snapshot dir (cached)")
    sys.exit(main(ap.parse_args().snapshot))
