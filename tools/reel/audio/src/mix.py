# 案P・通しの1本の音：静かで神秘的に。
# 始まり：カードが流れる音 → 裏返るたびに鉄琴 → 3枚が置かれる音。問いでハンドベル、考える3秒は小さな時計の音。
# めくるたびに鐘とハープ（逆位置は少し低く暗い和音）。並べて見せるところでハープ、ホーム画面でハンドベル、最後にボタンの音。
import sys, os, json, numpy as np, soundfile as sf
HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.environ.get('LIB', os.path.abspath(os.path.join(HERE, '../..')))
sys.path.insert(0, LIB); sys.path.insert(0, os.path.join(LIB, 'core/audio'))
from sfx import *
from core.audio import sampler as S
E = json.load(open(os.path.join(HERE, 'events.json'))); DUR = E['dur']; EV = E['ev']; N = int(DUR * SR)
rng = np.random.default_rng(4)
def nz(d): return rng.standard_normal(int(round(d * SR)))
def T(d): return np.arange(int(round(d * SR))) / SR
def fade(x, a=.005, b=.03):
    n = len(x); ia, ib = min(n, int(a * SR)), min(n, int(b * SR))
    if ia: x[:ia] *= np.linspace(0, 1, ia)
    if ib: x[-ib:] *= np.linspace(1, 0, ib)
    return x
def air(d, v=1.0): t = T(d); return fade(lp(bp(nz(d), 200, 2600), 2000) * np.sin(np.pi * t / d) ** 2 * .07 * v, .1, .2)
def flap(v=1.0):
    out = np.zeros(int(.42 * SR)); wh = bp(nz(.3), 500, 5000) * np.sin(np.linspace(0, np.pi, int(.3 * SR))) ** 1.5 * .25
    ft = T(.14); fl = lp(nz(.14), 1600) * np.exp(-ft / .02) * .45 + np.sin(2 * np.pi * 110 * ft) * np.exp(-ft / .035) * .25
    out[:len(wh)] += wh; i = int(.26 * SR); out[i:i + len(fl)] += fl[:len(out) - i]; return out * v
def tick(v=1.0): t = T(.05); return fade(bp(nz(.05), 2500, 7000) * np.exp(-t / .006) * .25 * v + np.sin(2 * np.pi * 1900 * t) * np.exp(-t / .01) * .08 * v, .0005, .01)
def riffle(d, v=1.0):
    out = np.zeros(int(d * SR)); t = 0.0
    while t < d - .03:
        tt = T(.025); c = bp(nz(.025), 1800, 6500) * np.exp(-tt / .004) * (.5 + .5 * rng.random())
        i = int(t * SR); out[i:i + len(c)] += c[:len(out) - i]; t += .018 + .03 * rng.random() * (1 + t / d)
    x = np.linspace(0, 1, len(out)); return fade(out * np.minimum(1, x * 8) * (1 - .7 * x) * .5 * v, .02, .3)
def whoosh2(v=1.0): d = .35; t = T(d); return fade(bp(nz(d), 400, 4500) * np.sin(np.pi * t / d) ** 2 * .22 * v, .01, .05)
def pat(v=1.0): t = T(.12); return fade(lp(nz(.12), 600) * np.exp(-t / .02) * .5 * v + np.sin(2 * np.pi * 150 * t) * np.exp(-t / .03) * .22 * v)
buf = np.zeros((N, 2))
def put(x, at, g=1.0, pan=0.0):
    x = np.asarray(x, np.float64)
    if x.ndim == 2: x = x.mean(1)
    add(buf, x, at, g, pan)
mus = []
for p, v in [('D3', .3), ('A3', .24)]: mus.append(dict(t=.3, inst='organ_soft', pitch=p, dur=DUR, vel=v, pan=-.1, attack=1.5))
GL = ['D6', 'E6', 'F6', 'G6', 'A6', 'C7', 'D7']
for e in EV:
    t, ty, pan = e['t'], e['type'], e.get('pan', 0.0)
    if ty == 'slide': put(riffle(e['dur']), t, 1.0, .3); put(whoosh2(1.4), t, 1.0, .6)
    elif ty == 'tick': put(pat(.35), t, 1.0, pan); mus.append((t, 'glockenspiel', GL[e['j'] - 7], .9, .22, pan))
    elif ty == 'gather': put(whoosh2(1.0), t, 1.0, 0)
    elif ty == 'land': put(pat(.9), t, 1.0, pan); mus.append((t, 'hand_chimes', ['D6', 'A5', 'F5'][e['slot']], 1.6, .36, pan))
    elif ty == 'open':
        for j, p in enumerate(['D4', 'A4', 'D5', 'F5', 'A5']): mus.append((t + j * .11, 'harp', p, 2.2, .4, -.3 + .15 * j))
    elif ty == 'question': mus.append((t, 'hand_chimes', 'A5', 2.4, .4, 0)); mus.append((t + .35, 'hand_chimes', 'D6', 2.4, .34, .1))
    elif ty == 'think':
        for k in range(int(e['dur'] / .5)): put(tick(.9 if k % 2 == 0 else .6), t + k * .5, 1.0, .2 if k % 2 else -.2)
    elif ty == 'rise': put(air(.7, 1.1), t, 1.0, pan); mus.append((t + .1, 'harp', 'A3', 2.0, .32, -.2))
    elif ty == 'flip': put(flap(1.0), t, 1.0, 0)
    elif ty == 'reveal':
        if e['rev']:   # 逆位置：少し低く、影のある響き
            mus.append((t, 'tubular_bells', 'A4', 3.5, .4, 0))
            for j, p in enumerate(['D3', 'F3', 'A3', 'C4', 'D4', 'F4']): mus.append((t + .04 + j * .08, 'harp', p, 3.0, .38, -.3 + .1 * j))
        else:
            mus.append((t, 'tubular_bells', 'D5', 3.5, .42, 0))
            for j, p in enumerate(['D4', 'F4', 'A4', 'C5', 'E5', 'F5', 'A5']): mus.append((t + .04 + j * .07, 'harp', p, 3.0, .4, -.3 + .1 * j))
            for j, p in enumerate(['A5', 'D6', 'E6', 'A6']): mus.append((t + .25 + j * .18, 'glockenspiel', p, 1.6, .28, -.3 + .2 * j))
        # 読みの間の静かな分散和音
        arp = ['D4', 'A4', 'F5', 'A4', 'E5', 'A4', 'D5', 'A4'] if not e['rev'] else ['D3', 'A3', 'F4', 'A3', 'E4', 'A3', 'D4', 'A3']
        for j, p in enumerate(arp): mus.append((t + 1.3 + j * .38, 'harp', p, 1.4, .24, -.2 + .05 * j))
    elif ty == 'word': mus.append((t, 'hand_chimes', ['F6', 'C6', 'A5'][e['i']], 2.0, .3, .2))
    elif ty == 'return': put(whoosh2(.7), t, 1.0, pan); put(pat(.4), t + .45, 1.0, pan)
    elif ty == 'summary':
        for j, p in enumerate(['D4', 'F4', 'A4', 'D5', 'F5', 'A5', 'D6']): mus.append((t + j * .09, 'harp', p, 3.0, .38, -.3 + .1 * j))
    elif ty == 'home':
        for j, p in enumerate(['F3', 'C4', 'A4']): mus.append((t + j * .05, 'harp', p, 3.5, .36, -.1 + .1 * j))
        for j, p in enumerate(['C6', 'F6']): mus.append((t + .6 + j * .6, 'hand_chimes', p, 2.5, .36, .1))
    elif ty == 'tap':
        put(S.hit('woodblock', 'b', .45), t, .7, .1); put(pat(.45), t, 1.0, .1)
        for j, p in enumerate(['F5', 'A5', 'C6']): mus.append((t + .02 + j * .07, 'glockenspiel', p, 1.4, .4, .1))
M = S.render(mus, dur=DUR + 3, master=False); M = S.room(M, size=.7, mix=.28)[:N]
if len(M) < N: M = np.pad(M, ((0, N - len(M)), (0, 0)))
FX = np.stack([S.room(buf, size=.6, mix=.2)[:N, c] for c in range(2)], 1)
mix = M + FX * 2.0
k = int(.4 * SR); mix[-k:] *= np.linspace(1, 0, k)[:, None]
for c in range(2): mix[:, c] = limit(mix[:, c], .95)
os.makedirs(os.path.join(HERE, 'out'), exist_ok=True); sf.write(os.path.join(HERE, 'out', 'mix.wav'), mix.astype(np.float32), SR)
print('peak', float(np.abs(mix).max()))
