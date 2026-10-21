#!/bin/bash
# 8通りの音（左・中・右の正逆 UUU〜RRR）を作り直す時に使う。普段は使わない。
# 必要なもの：Lemo-Opuscar の音の部品（LIB=…/lemo-opuscar、楽器の音源をダウンロード済み）、python3（numpy, soundfile）、ffmpeg
set -e
SRC=$(cd "$(dirname "$0")" && pwd); OUT=$(dirname "$SRC"); W=$(mktemp -d)
for v in UUU UUR URU URR RUU RUR RRU RRR; do
  mkdir -p "$W/$v"; cp "$SRC/mix.py" "$W/$v/"
  python3 - "$SRC/events.json" "$W/$v/events.json" "$v" <<'PY'
import json, sys
e = json.load(open(sys.argv[1]))
for x in e['ev']:
    if x['type'] == 'reveal': x['rev'] = sys.argv[3][x['i']] == 'R'
json.dump(e, open(sys.argv[2], 'w'))
PY
  python3 "$W/$v/mix.py" >/dev/null
  M=$(ffmpeg -hide_banner -i "$W/$v/out/mix.wav" -af loudnorm=I=-14:TP=-1.2:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
  g() { echo "$M" | python3 -c "import json,sys;print(json.load(sys.stdin)['$1'])"; }
  ffmpeg -y -loglevel error -i "$W/$v/out/mix.wav" -af "loudnorm=I=-14:TP=-1.2:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true" -ar 48000 -c:a aac -b:a 192k "$OUT/$v.m4a"
  echo "$v.m4a"
done
rm -rf "$W"
