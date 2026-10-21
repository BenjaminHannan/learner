"""Run a deterministic forward+backward and print hashes of the loss and every gradient. Used by test_joint.py in two processes
(original code vs current code with every V1 flag OFF, and with the bridge attached at zero) to prove bit-equality.
  python ref_dump.py d|b2 [bridge]   (cwd/PYTHONPATH decides which code tree is imported)"""
import hashlib, json, os, sys
import torch

mode, bridge = sys.argv[1], (len(sys.argv) > 2 and sys.argv[2] == "bridge")
torch.manual_seed(0)
torch.use_deterministic_algorithms(True)


def digest(tensors):
    h = hashlib.sha256()
    for t in tensors:
        h.update(t.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


if mode == "d":
    from premonition.config import MiniConfig
    from premonition.model import PremonitionMini
    from premonition.toy import ToySpec, toy_stream
    from premonition.train import label_free
    spec = ToySpec()
    torch.manual_seed(0)
    model = PremonitionMini(MiniConfig.preset("D", "tiny", vocab_size=spec.vocab_size, window=64))
    batch = label_free(next(iter(toy_stream(spec, 8, 0))))
    br = None
    if bridge:
        from v1.joint import Bridge
        br = Bridge(model.config.d_model, 256).attach(model, type("C", (), {"bridge_in": None, "bridge_out": None})())
    out = model(batch, mode="teacher", p_own=0.0, generator=torch.Generator().manual_seed(0))
    out["loss"].backward()
    grads = [p.grad if p.grad is not None else torch.zeros(()) for p in model.parameters()]
    print(json.dumps({"loss": digest([out["loss"]]), "grads": digest(grads), "bridge": bool(bridge)}))
else:
    from custom_io.data import CharVocab, Dataset, collate, load_rows, to_device
    from custom_io.models import build
    ckpt = os.environ["B2_CKPT"]
    skills = os.environ["SKILLS_TRAIN"]
    ck = torch.load(ckpt, map_location="cpu", weights_only=False)
    vocab = CharVocab(ck["chars"])
    model = build(ck["name"], vocab, **ck["cfg"])
    model.load_state_dict(ck["model"])
    model.train()
    rows = load_rows(skills, limit=64)
    if bridge:
        from v1.joint import Bridge
        D = type("D", (), {"bridge_in": None, "heads": type("H", (), {"halt": torch.nn.Linear(2, 1)})()})()
        Bridge(128, 256).attach(D, model)
    batch = to_device(collate([Dataset(rows, vocab, strict=False)[i] for i in range(len(rows))]), "cpu")
    loss, _ = model.loss(batch)
    loss.backward()
    grads = [p.grad if p.grad is not None else torch.zeros(()) for p in model.parameters()]
    print(json.dumps({"loss": digest([loss]), "grads": digest(grads), "bridge": bool(bridge)}))
