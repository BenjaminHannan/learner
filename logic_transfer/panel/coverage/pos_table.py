"""Static weight inspection (no forward pass, no training): how trained are the reader's absolute-position rows beyond the curriculum's length range?
Compares parent s200 vs D1b-3500 (94% logic) position embeddings: row norm by position bucket and movement ||pos_D1b - pos_parent||."""
import torch, json, sys
torch.set_num_threads(1)
S = "/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad"
def pos(path):
    ck = torch.load(path, map_location="cpu", weights_only=True)
    return ck["model"]["reader.pos.weight"].float().clone()
P = pos("/mnt/project-files/checkpoints/cio-1007/70-t1sdr-s200/T1SDR_s200/checkpoint.pt")
D = pos(S + "/lt2/diag/D1b/checkpoint-3500.pt")
out = {}
for a, b in [(0, 50), (50, 100), (100, 130), (130, 150), (150, 170), (170, 190), (190, 208)]:
    out[f"{a}-{b - 1}"] = dict(parent_row_norm=round(float(P[a:b].norm(dim=1).mean()), 2), d1b_row_norm=round(float(D[a:b].norm(dim=1).mean()), 2),
                              movement=round(float((D[a:b] - P[a:b]).norm(dim=1).mean()), 3))
print(json.dumps(out, indent=1))
json.dump(out, open("/tmp/claude-0/-home-user-learner/37e869c5-9fee-53ef-875e-19be57429294/scratchpad/panel/coverage/pos_table.json", "w"), indent=1)
