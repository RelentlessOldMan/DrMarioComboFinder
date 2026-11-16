#!/bin/bash
# Ensemble scan: several heuristic settings per seed (results are noisy, so each one is a separate try).
# Usage: scan_big.sh level n0 n1 out.jsonl [depth] [beam] [min]   (CFGS: settings separated by ";")
lv=$1; n0=$2; n1=$3; out=$4; depth=${5:-80}; beam=${6:-2000}; min=${7:-16}
for ((n = n0; n < n1; n++)); do
  IFS=";" read -ra cfgs <<< "${CFGS:-shape=0.25 look=2}"
  for cfg in "${cfgs[@]}"; do
    engine/dm.exe search level=$lv n0=$n n1=$((n + 1)) depth=$depth beam=$beam $cfg min=$min per=20 2>/dev/null \
      | grep kills | sed "s/}\$/,\"cfg\":\"$cfg\"}/" >> "$out"
  done
done
