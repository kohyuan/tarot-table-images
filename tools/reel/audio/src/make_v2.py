#!/usr/bin/env python3
# 悩みの形（1枚9秒・ホーム画面なし・41.8秒）の音を、今の音（33.3秒）をつなぎ直して作る。
# 使い方（tools/reel で）： python3 audio/src/make_v2.py
# 必要なもの：python3（numpy）、ffmpeg。楽器の音源は要らない（今の8通りの .m4a を切ってつなぐだけ）。
#
# つなぎ方（s は、今の音でそのカードをめくり始める時刻 6.9 / 13.9 / 20.9）
#   始まり       ：0 〜 6.9 をそのまま
#   カード1枚(9秒)：s 〜 s+4.67 ／ s+2.77 〜 s+4.67 の分散和音をもう一度（1.9秒を2.0秒に伸ばす）／ s+4.67 〜 s+7.0
#   終わり(7.9秒) ：27.9 〜 32.15（3枚を並べる所とハンドベル。ボタンの音の手前まで）／ 9.67 〜 13.33 の分散和音 → 最後の1.2秒で消す
import os, subprocess, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); AUD = os.path.dirname(HERE); OUT = os.path.join(AUD, 'v2')
SR = 48000; XF = 0.08   # つなぎ目は 0.08 秒重ねる
def load(f):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', f, '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).astype(np.float64)
def cut(x, a, b): return x[int(round(a * SR)):int(round(b * SR))]
def stretch(x, sec):   # 音の高さを変えずに長さを sec 秒にする
    tempo = (len(x) / SR) / sec
    p = subprocess.run(['ffmpeg', '-v', 'error', '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-i', '-', '-af', f'atempo={tempo:.6f}', '-f', 'f32le', '-'], input=x.astype(np.float32).tobytes(), capture_output=True, check=True)
    y = np.frombuffer(p.stdout, np.float32).reshape(-1, 2).astype(np.float64); n = int(round(sec * SR))
    return y[:n] if len(y) >= n else np.pad(y, ((0, n - len(y)), (0, 0)))
def join(parts):       # 前の部品の終わりと次の部品の始まりを XF 秒重ねてつなぐ（各部品は前後に XF/2 ずつ長く切ってある）
    k = int(XF * SR); out = parts[0].copy(); w = np.sin(np.linspace(0, np.pi / 2, k))[:, None]
    for p in parts[1:]:
        out[-k:] = out[-k:] * w[::-1] + p[:k] * w; out = np.concatenate([out, p[k:]])
    return out
for v in ['UUU', 'UUR', 'URU', 'URR', 'RUU', 'RUR', 'RRU', 'RRR']:
    x = load(os.path.join(AUD, v + '.m4a')); h = XF / 2
    parts = [cut(x, 0, 6.9 + h)]
    for i in range(3):
        s = 6.9 + 7 * i
        parts += [cut(x, s - h, s + 4.67 + h), np.concatenate([cut(x, s + 2.77 - h, s + 2.77), stretch(cut(x, s + 2.77, s + 4.67), 2.0), cut(x, s + 4.67, s + 4.67 + h)]), cut(x, s + 4.67 - h, s + 7.0 + h)]
    parts += [cut(x, 27.9 - h, 32.15 + h), cut(x, 9.67 - h, 13.33)]
    y = join(parts); n = int(round(41.8 * SR)); y = y[:n] if len(y) >= n else np.pad(y, ((0, n - len(y)), (0, 0)))
    k = int(1.2 * SR); y[-k:] *= np.linspace(1, 0, k)[:, None] ** 1.5
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'f32le', '-ac', '2', '-ar', str(SR), '-i', '-', '-c:a', 'aac', '-b:a', '192k', os.path.join(OUT, v + '.m4a')], input=y.astype(np.float32).tobytes(), check=True)
    print(v + '.m4a', round(len(y) / SR, 2), '秒  最大', round(float(np.abs(y).max()), 3))
