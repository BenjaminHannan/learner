"""How much did the team coach actually move practice? (TEAM-PASS-MARKS.md amendment of 2026-10-05.)

  python -m custom_io.team_alloc --run RUN_DIR --data DATA [--pools 50] [--mix 0.5]

From the saved final coach: on --pools seeded pools of 2*batch training rows, member i's sampling distribution is
q_i = (1 - mix) / P + mix * coach_i(row) / sum(coach_i); its total-variation distance from uniform is 0.5 * sum |q_i - 1/P|.
Prints the mean TV per member (void if the mean over members is under 0.05), the effective number of rows sampled
(1 / sum q_i^2, out of P), and each member's family exposure relative to uniform (top and bottom families)."""
import argparse, collections, json, os
import numpy as np
import torch
from custom_io.data import CharVocab, Dataset, collate, load_rows
from custom_io.team import Coach


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True); ap.add_argument('--data', required=True)
    ap.add_argument('--pools', type=int, default=50); ap.add_argument('--batch', type=int, default=256)
    ap.add_argument('--mix', type=float, default=0.5); ap.add_argument('--seed', type=int, default=12345)
    a = ap.parse_args(argv)
    ck = torch.load(os.path.join(a.run, 'checkpoint.pt'), map_location='cpu')
    names = [m['label'] for m in ck['members']]
    vocab = CharVocab(ck['chars'])
    coach = Coach(len(vocab), len(names))
    coach.load_state_dict(ck['coach'])
    coach.eval()
    rows = load_rows(os.path.join(a.data, 'train.jsonl'))
    ds = Dataset(rows, vocab)
    P, rng = 2 * a.batch, np.random.RandomState(a.seed)
    tv, ess = np.zeros(len(names)), np.zeros(len(names))
    fam_q, fam_u = [collections.Counter() for _ in names], collections.Counter()
    with torch.no_grad():
        for _ in range(a.pools):
            idx = rng.choice(len(ds), P, replace=False)
            pi = coach(collate([ds[j] for j in idx])).softmax(-1).numpy()
            for i in range(len(names)):
                q = (1 - a.mix) / P + a.mix * pi[:, i] / pi[:, i].sum()
                tv[i] += 0.5 * np.abs(q - 1 / P).sum() / a.pools
                ess[i] += 1 / (q ** 2).sum() / a.pools
                for j, w in zip(idx, q):
                    fam_q[i][rows[j]['family']] += w
            for j in idx:
                fam_u[rows[j]['family']] += 1 / P
    out = dict(run=a.run, tv={n: round(float(t), 4) for n, t in zip(names, tv)}, mean_tv=round(float(tv.mean()), 4),
               void=bool(tv.mean() < 0.05), ess_of={n: round(float(e), 1) for n, e in zip(names, ess)}, pool=P, exposure={})
    for i, n in enumerate(names):
        ratio = {f: fam_q[i][f] / fam_u[f] for f in fam_u}
        srt = sorted(ratio.items(), key=lambda x: x[1])
        out['exposure'][n] = dict(most=[(f, round(float(r), 2)) for f, r in srt[::-1][:5]], least=[(f, round(float(r), 2)) for f, r in srt[:5]])
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
