"""Re-score write_copy on a saved checkpoint with the Amendment 4 scorer (Tool.write_copy_u), on the same dev rows and settings as train.py's
final eval (--big-data's dev/in_dist.jsonl, eval batch 128, bf16 autocast on cuda). Writes WC.json beside nothing else.
python3 -m custom_io.rescore_wc --ck RUN/checkpoint.pt --data DATA --big-data DATA_BIG --out OUT/WC.json [--device cuda] [--bf16]"""
import argparse, contextlib, hashlib, json, os, time
import torch
from custom_io.models import load_model


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--ck', required=True)
    ap.add_argument('--data', required=True)
    ap.add_argument('--big-data', default=None)
    ap.add_argument('--out', required=True)
    ap.add_argument('--device', default='cuda' if torch.cuda.is_available() else 'cpu')
    ap.add_argument('--bf16', action='store_true')
    ap.add_argument('--eval-batch', type=int, default=128)
    a = ap.parse_args(argv)
    dev = torch.device(a.device)
    m = load_model(a.ck, dev)
    amp = (lambda: torch.autocast(dev.type, dtype=torch.bfloat16)) if a.bf16 and dev.type == 'cuda' else contextlib.nullcontext
    t0 = time.time()
    wc = m.write_copy_u(dict(data=a.data, big=a.big_data, device=dev, batch_size=a.eval_batch, amp=amp))
    ck = torch.load(a.ck, map_location='cpu', weights_only=False)
    path = os.path.join(a.big_data or a.data, 'dev', 'in_dist.jsonl')
    out = dict(write_copy_u=wc, checkpoint=a.ck, ck_sha256=hashlib.sha256(open(a.ck, 'rb').read()).hexdigest(), name=ck['name'], cfg=ck['cfg'],
               step=ck['step'], n_params=m.n_params(), in_dist_sha256=hashlib.sha256(open(path, 'rb').read()).hexdigest(), device=a.device, bf16=a.bf16,
               eval_batch=a.eval_batch, secs=round(time.time() - t0, 1))
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    json.dump(out, open(a.out, 'w'), indent=1)
    print(json.dumps(dict(event='rescore', passes=wc['passes'], **{k: {L: round(v['exact'], 1) for L, v in wc[k].items()} for k in ('operand', 'answer')})))


if __name__ == '__main__':
    main()
