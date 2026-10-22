import sys, pathlib, torch
ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "scripts"), str(pathlib.Path(__file__).parent)]
import pytest
from vision_adapter import GridAdapter, FrozenPatchEncoder

def test_shapes_and_resize():
    enc = FrozenPatchEncoder(); ad = GridAdapter(96, grid=(4, 4))
    for side in (32, 64, 48):
        f, g = enc(torch.randn(2, 3, side, side))
        assert ad(f, g).shape == (2, 4, 4, 256)

def test_bad_grid_rejected():
    with pytest.raises(ValueError):
        GridAdapter(8)(torch.randn(1, 10, 8), (3, 3))

def test_encoder_frozen_adapter_trains():
    enc = FrozenPatchEncoder(); ad = GridAdapter(96, grid=(4, 4))
    assert not any(p.requires_grad for p in enc.parameters())
    f, g = enc(torch.randn(2, 3, 32, 32)); ad(f, g).sum().backward()
    assert all(p.grad is not None for p in ad.parameters())

def test_modality_tag_changes_latent():
    f = torch.randn(1, 16, 8)
    a, b = GridAdapter(8, (4, 4), modality="image"), GridAdapter(8, (4, 4), modality="audio")
    b.load_state_dict(a.state_dict()); b.modality_id.fill_(2)
    assert not torch.allclose(a(f, (4, 4)), b(f, (4, 4)))

def test_feeds_real_reasoner_with_notebook():
    import claude_fewex_net as N
    from sol_spatial_attention_core import AttentionReasoner
    torch.manual_seed(0)
    r = AttentionReasoner(N.Net("loop"), experts=2, active=1).eval()
    enc = FrozenPatchEncoder(); ad = GridAdapter(96, grid=(4, 4))
    f, g = enc(torch.randn(2, 3, 32, 32)); lat = ad(f, g)
    out = r.reason_latent(lat.detach(), notebook=torch.randn(2, 3, 256), cap=3)
    assert out["final_latent"].shape == (2, 16, 256)

def test_spatial_information_survives_pipe():
    """CPU toy: can a tiny readout on the adapter latent tell which quadrant holds a bright square (flattened grid, so position is kept)?
    Shown only for this toy; says nothing about real images or reasoning."""
    torch.manual_seed(0)
    enc = FrozenPatchEncoder(); ad = GridAdapter(96, grid=(4, 4), hidden=32); head = torch.nn.Linear(16 * 256, 4)
    def batch(n=64):
        y = torch.randint(0, 4, (n,)); x = torch.zeros(n, 3, 32, 32)
        for i, q in enumerate(y.tolist()):
            r, c = divmod(q, 2); x[i, :, r*16+4:r*16+12, c*16+4:c*16+12] = 1
        return x, y
    opt = torch.optim.Adam([*ad.parameters(), *head.parameters()], 3e-3)
    for _ in range(150):
        x, y = batch(); f, g = enc(x)
        loss = torch.nn.functional.cross_entropy(head(ad(f, g).flatten(1)), y); opt.zero_grad(); loss.backward(); opt.step()
    x, y = batch(256); f, g = enc(x)
    assert (head(ad(f, g).flatten(1)).argmax(-1) == y).float().mean() > 0.9

def test_pos2d_unique_and_notebook_mode_runs():
    from vision_adapter import pos2d
    p = pos2d(8, 8).reshape(64, -1)
    assert torch.cdist(p, p).fill_diagonal_(9).min() > 0.1
    import claude_fewex_net as N
    from sol_spatial_attention_core import AttentionReasoner
    r = AttentionReasoner(N.Net("loop"), experts=2, active=1).eval()
    enc = FrozenPatchEncoder(); ad = GridAdapter(96, grid=(8, 8))
    f, g = enc(torch.randn(2, 3, 64, 64)); nb = ad(f, g, as_notebook=True)
    assert nb.shape == (2, 64, 256)
    out = r.reason_latent(torch.randn(2, 1, 12, 256), notebook=nb.detach(), cap=3)
    assert out["final_latent"].shape == (2, 12, 256)  # query_n unchanged by notebook

def test_workspace_contract_and_zero_init():
    from workspace import image_to_workspace, SegmentEmbedding
    enc = FrozenPatchEncoder(); ad = GridAdapter(96, grid=(8, 8))
    f, g = enc(torch.randn(2, 3, 64, 64)); lat = ad(f, g).flatten(1, 2)
    ws = image_to_workspace(lat)
    assert ws.coords.shape == (2, 64, 3) and ws.valid.all()
    assert torch.equal(SegmentEmbedding()(ws), ws.tokens)  # zero-init: no change at start
