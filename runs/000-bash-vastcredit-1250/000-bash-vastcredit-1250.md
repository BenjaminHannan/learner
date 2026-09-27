BASH-ONLY: yes
GPU: no. LOAD-LIGHT: yes
Director read-only vast check for the Thread manager (12:47 UTC 09-27). Rents nothing, creates nothing, prints no key, email or config. Prints only the credit/balance number and the running-instance count with ids, labels and $/h.
```bash
command -v vastai >/dev/null || { echo "vastai CLI missing"; exit 0; }
vastai show user --raw 2>/dev/null | python3 -c 'import json,sys; d=json.load(sys.stdin); print("credit", d.get("credit"), "balance", d.get("balance"))'
vastai show instances --raw 2>/dev/null | python3 -c 'import json,sys; d=json.load(sys.stdin); print("instances", len(d)); [print(i.get("id"), i.get("label"), i.get("actual_status"), round(i.get("dph_total") or 0,3)) for i in d]'
date -u
```
