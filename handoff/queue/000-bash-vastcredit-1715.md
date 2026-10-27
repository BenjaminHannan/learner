BASH-ONLY: yes
GPU: no. LOAD-LIGHT: yes
Director read-only vast check (2026-09-27T17:15:56Z) for the Thread manager's hourly spend line. Rents nothing, creates nothing, prints no key, email or config: only credit/balance and per-instance id, label, status and $/h.
```bash
command -v vastai >/dev/null || { echo "vastai CLI missing"; exit 0; }
vastai show user --raw 2>/dev/null | grep -oE '"(credit|balance)": *-?[0-9.]+'
vastai show instances --raw 2>/dev/null | perl -MJSON::PP -e 'local $/; my $d=decode_json(<STDIN>); print "instances ", scalar(@$d), "\n"; printf "%s %s %s %.3f\n", $_->{id}, $_->{label}//"-", $_->{actual_status}//"-", $_->{dph_total}//0 for @$d'
date -u
```
