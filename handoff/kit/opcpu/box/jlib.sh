# Sourced by every job script (box/job-*.sh). Machine-only replacements for what the Mac jobs do with git, uv, shasum, df and perl.
# The pinned tree (git archive of the pinned commit) sits in $OPC_R; each job unpacks what its queue file archives into its OWN private folder.
: "${OPC_R:?}" "${OPC_PYX:?}" "${OPC_IN:?}" "${OPC_OUT:?}"
PY="$OPC_PYX -B"                                   # replaces: uv run --offline --no-project --python 3.12 --with torch --with numpy python -B
unpack() { _w=$1; shift; mkdir -p "$_w" && tar -c -C "$OPC_R" "$@" | tar -x -C "$_w"; }     # replaces: git archive REF paths | tar -x -C W
freegb() { df -BG "$HOME" | awk 'NR==2{gsub("G","",$4); print $4}'; }                        # replaces: df -g /
alarm() { _s=$1; shift; timeout -s ALRM "$_s" "$@"; }                                        # replaces: perl -e 'alarm shift; exec @ARGV' SECONDS cmd
