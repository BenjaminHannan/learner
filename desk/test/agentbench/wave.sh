#!/bin/zsh
# AGENT1 bench: one run of all 20 tasks as 3 waves (7/7/6 tasks, each < 30 min at the 240 s task cap), each under the real-model lock.
# usage: wave.sh <label> <run#> [agentKit names, e.g. sso,diet]   -> /tmp/aon/agentbench/<label>-r<run#>/
cd "$(dirname "$0")/../.." || exit 1
E=${ELECTRON:-/tmp/aon/ui1-electron/Electron.app/Contents/MacOS/Electron}
label=$1; n=$2; kit=${3:-}; out=/tmp/aon/agentbench/$label-r$n
W1=school_due_week,school_steer,school_told_url,school_chem_due,school_fieldtrip,shop_price,shop_compare
W2=shop_cart,shop_buy_ask,library_hours,library_steer,library_renew,library_contact,runclub_backout
W3=news_paging,recipe_temp,account_radio,mail_login,bank_code,pizza_search
for w in $W1 $W2 $W3; do
  until [[ $(sysctl -n kern.memorystatus_vm_pressure_level) == 1 ]] && (( $(sysctl -n vm.loadavg | awk '{print int($2)}') <= 8 )); do sleep 20; done
  env -u ELECTRON_RUN_AS_NODE /tmp/aon/realmodel-lock.sh AGENT1 $E test/agentbench/run.js --out $out --label $label --run $n --tasks $w --cap 240 --maxSteps 25 --kit "$kit" --profile /tmp/aon/agentbench/profile 2>&1 | grep -v ':ERROR:\|sandbox_extension\|Fontconfig'
done
