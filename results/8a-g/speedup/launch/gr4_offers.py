"""gr4_offers.py KIT_VAST_PY [--max-dph 0.46] [--n 12]: read-only offer search for GPU-RUN-4. The kit's own search query (verified, on-demand, 1 GPU, reliability >= 0.98, CUDA >= 12.8,
disk >= 60 GB, >= 300 Mb/s, >= 8 effective cores), RTX 4090 only, dph_total <= --max-dph (PREREG-launch-defer.md money: $0.46/h), printing also machine_id, host_id and cpu_name so the two
boxes can be picked on different hosts (mark 6). Creates nothing; the proxy adds the Vast key."""
import argparse, importlib.util, json

ap = argparse.ArgumentParser()
ap.add_argument('kit'); ap.add_argument('--max-dph', type=float, default=0.46); ap.add_argument('--n', type=int, default=12)
a = ap.parse_args()
spec = importlib.util.spec_from_file_location('vast', a.kit)
vast = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vast)
q = {'verified': {'eq': True}, 'rentable': {'eq': True}, 'rented': {'eq': False}, 'type': 'on-demand', 'num_gpus': {'eq': 1}, 'gpu_ram': {'gte': 23000}, 'reliability': {'gte': 0.98},
     'cuda_max_good': {'gte': 12.8}, 'disk_space': {'gte': 60}, 'inet_down': {'gte': 300}, 'cpu_cores_effective': {'gte': 8}, 'order': [['dph_total', 'asc']], 'limit': 300}
offers = [o for o in (vast.call('POST', '/bundles/', q).get('offers') or []) if o.get('gpu_name') == 'RTX 4090' and (o.get('dph_total') or 9) <= a.max_dph]
for o in offers[: a.n]:
    print(json.dumps({k: o.get(k) for k in ('id', 'machine_id', 'host_id', 'dph_total', 'reliability', 'cpu_name', 'cpu_cores_effective', 'cpu_ram', 'inet_down', 'disk_space',
                                             'cuda_max_good', 'driver_version', 'geolocation')}))
print(json.dumps(dict(n_offers_under_cap=len(offers), max_dph=a.max_dph)))
