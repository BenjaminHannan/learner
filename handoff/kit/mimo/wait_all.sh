#!/bin/bash
Q="$1"; for i in $(seq 1 330); do n=$(ls "$Q"/*.md 2>/dev/null | grep -v reply | wc -l); d=$(ls "$Q"/*.done 2>/dev/null | wc -l); [ "$d" -ge "$n" ] && break; sleep 10; done; cat "$Q/log.txt"
