BASH-ONLY: yes
GPU: no. LOAD-LIGHT: yes
Director read-only vast check, re-run of 000-bash-vastcredit-1250 (the Mac's /usr/local/bin/python3 is an x86 binary: "Bad CPU type"). Rents nothing, creates nothing, prints no key, email or config: only the credit/balance numbers and per-instance id, label, status and $/h.
```bash
command -v vastai >/dev/null || { echo "vastai CLI missing"; exit 0; }
vastai show user --raw 2>/dev/null | grep -oE '"(credit|balance)": *-?[0-9.]+'
vastai show instances --raw 2>/dev/null | perl -MJSON::PP -e 'local $/; my $d=decode_json(<STDIN>); print "instances ", scalar(@$d), "\n"; printf "%s %s %s %.3f\n", $_->{id}, $_->{label}//"-", $_->{actual_status}//"-", $_->{dph_total}//0 for @$d'
date -u
```
