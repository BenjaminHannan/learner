#!/bin/bash
# exits when the number of *.done files (incl. resume) grows past the count given, or after 50 min
Q="$1"; base="$2"; for i in $(seq 1 300); do d=$(ls "$Q"/*.done 2>/dev/null | wc -l); [ "$d" -gt "$base" ] && break; sleep 10; done; ls -t "$Q"/*.done | head -3; tail -4 "$Q/log.txt"
