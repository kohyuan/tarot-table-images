# タロットテーブル Threads のピックカードの画像を作るコード
#
# 使い方:
#   python3 make_images.py --spec spec.json --out 出力フォルダ [--cards 水彩画のフォルダ]
#
# ピックカードのコメントに付ける「3枚開けた画面」と、投稿に付ける伏せた3枚の画像を作る。
# --cards を渡すと、3枚とも水彩画があるときは水彩画版で作り、1枚でも無ければシンプル版で作る。
# 水彩画のファイル名は「番号_日本語_英語_向き.png」。番号は card_id（M14、C02 など）でもローマ数字（XIV など）でもよい。
# 向きは upright か reversed。逆位置のファイルが無ければ、正位置の絵を上下逆にして使う。
#
# spec.json の形:
#   {"run_date": "2026-10-18",
#    "items": [
#      {"post_id": "T0016", "kind": "open", "scheduled_at": "2026-10-19 23:00",
#       "caption": "10/20(火) - 26(月) 仕事・勉強",
#       "cards": ["W10", "P07", "P12"], "pos": ["R", "R", "R"]}
#    ]}
#
# 出力:
#   出力フォルダ/img/<post_id>.png  … 1200x675 の3枚開けた画面
#   出力フォルダ/img/back.png       … 伏せた3枚（毎回同じ）
#
# シンプル版のカードの絵はアプリ（tarot-table リポジトリ）の deck/art.mjs をそのまま使う。
# 背景・大きさ・位置はこのファイルの中で固定しているので、毎回ずれない。
# X 用のコード（Artifact のページ「タロットテーブル 投稿画像」の tools/make_images.txt）を写して、ページ用の出力を外したもの。
# 置き場所：GitHub の kohyuan/tarot-table-images の tools/make_images.py（このファイル）。

import argparse, base64, io, json, os, re, subprocess, sys, tempfile

REPO = os.environ.get("TAROT_REPO", "/home/claude/tarot-table")
W, H = 1200, 675

NODE = r"""
import { byId } from '__REPO__/deck/cards.mjs';
import { cardSvg, backSvg } from '__REPO__/deck/art.mjs';
import { readFileSync, writeFileSync } from 'fs';
const S = {W:'wands', C:'cups', S:'swords', P:'pentacles'};
const id = c => c[0] === 'M' ? `major-${c.slice(1)}` : `${S[c[0]]}-${c.slice(1)}`;
const items = JSON.parse(readFileSync(process.argv[2], 'utf8'));
const out = {};
out.back = backSvg();
for (const it of items) {
  if (it.kind === 'open') out[it.post_id] = it.cards.map((c, i) => {
    const card = byId[id(c)]; if (!card) throw new Error('unknown card ' + c);
    return cardSvg(card, { reversed: it.pos[i] === 'R' });
  });
  else if (it.kind === 'one') {
    const card = byId[id(it.card)]; if (!card) throw new Error('unknown card ' + it.card);
    out[it.post_id] = [cardSvg(card, { reversed: it.pos === 'R' })];
  }
}
writeFileSync(process.argv[3], JSON.stringify(out));
"""

CSS = """
html,body{margin:0;width:1200px;height:675px;overflow:hidden}
body{background:radial-gradient(ellipse at 50% 40%,#2a2150 0%,#151030 55%,#0b0918 100%);
 font-family:'Noto Serif CJK JP','Noto Serif CJK SC',serif;color:#e6cf9c}
.cap{position:absolute;top:16px;left:0;right:0;text-align:center;font-size:22px;letter-spacing:3px;opacity:.75}
.row{position:absolute;top:58px;left:0;right:0;display:flex;justify-content:center;gap:60px}
.slot{width:300px;text-align:center}
.card svg{width:300px;height:500px;display:block;filter:drop-shadow(0 8px 18px rgba(0,0,0,.55))}
.lab{margin-top:14px;font-size:26px;letter-spacing:4px;opacity:.9}
"""

def page(caption, slots):
    cards = "".join(f'<div class="slot"><div class="card">{svg}</div><div class="lab">{lab}</div></div>' for svg, lab in slots)
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body><div class="cap">{caption}</div><div class="row">{cards}</div></body></html>'

POS = {"U": "正位置", "R": "逆位置"}

ROMAN = ["0","I","II","III","IV","V","VI","VII","VIII","IX","X","XI","XII","XIII","XIV","XV","XVI","XVII","XVIII","XIX","XX","XXI"]

def card_key(filename):
    """水彩画のファイル名から (card_id, 向き U/R) を取り出す。分からなければ None。"""
    base = os.path.splitext(os.path.basename(filename))[0]
    parts = base.split("_")
    if len(parts) < 2:
        return None
    head, last = parts[0], parts[-1].lower()
    pos = {"upright": "U", "reversed": "R"}.get(last)
    if pos is None:
        return None
    if re.fullmatch(r"M\d\d|[WCSP](0[1-9]|1[0-4])", head):
        return head, pos
    if head in ROMAN:
        return "M%02d" % ROMAN.index(head), pos
    return None

def load_cards(folder):
    found = {}
    if folder and os.path.isdir(folder):
        for f in os.listdir(folder):
            k = card_key(f)
            if k:
                found[k] = os.path.join(folder, f)
    return found

def crop_card(path, rotate):
    """背景つきの正方形の画像なら、カードの部分だけを切り出す。全面がカードならそのまま。"""
    from PIL import Image, ImageChops
    im = Image.open(path).convert("RGB")
    w, h = im.size
    bg = im.getpixel((3, 3))
    diff = ImageChops.difference(im, Image.new("RGB", im.size, bg)).convert("L").point(lambda v: 255 if v > 60 else 0)
    box = diff.getbbox()
    if box and (box[2] - box[0]) < w * 0.95:
        im = im.crop(box)
    if rotate:
        im = im.rotate(180)
    buf = io.BytesIO(); im.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

def wc_page(caption, uris, labels):
    css = CSS + ".slot{width:330px}.wc{width:330px;height:470px;object-fit:contain;display:block;border-radius:8px;filter:drop-shadow(0 8px 18px rgba(0,0,0,.55))}.row{top:52px}"
    cards = "".join(f'<div class="slot"><img class="wc" src="{u}"><div class="lab">{l}</div></div>' for u, l in zip(uris, labels))
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body><div class="cap">{caption}</div><div class="row">{cards}</div></body></html>'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cards")
    a = ap.parse_args()
    wc = load_cards(a.cards)
    if not os.path.exists(os.path.join(REPO, "deck", "art.mjs")):
        sys.exit(f"カードの絵のコードが見つからない: {REPO}/deck/art.mjs")
    spec = json.load(open(a.spec, encoding="utf-8"))
    items = [it for it in spec["items"] if it["kind"] == "open"]
    os.makedirs(os.path.join(a.out, "img"), exist_ok=True)
    tmp = tempfile.mkdtemp()
    js = os.path.join(tmp, "svg.mjs"); open(js, "w").write(NODE.replace("__REPO__", REPO))
    ij = os.path.join(tmp, "items.json"); json.dump(items, open(ij, "w"))
    sj = os.path.join(tmp, "svgs.json")
    subprocess.run(["node", js, ij, sj], check=True)
    svgs = json.load(open(sj))

    pages = {"back": page("The Tarot Table", [(svgs["back"], l) for l in ["左", "中", "右"]])}
    art = {}
    for it in items:
        labels = [f'{lr} {POS[it["pos"][i]]}' for i, lr in enumerate(["左", "中", "右"])]
        have = all((c, "U") in wc or (c, "R") in wc for c in it["cards"])
        if have:
            uris = []
            for c, p in zip(it["cards"], it["pos"]):
                if (c, p) in wc:
                    uris.append(crop_card(wc[(c, p)], False))
                else:
                    other = "U" if p == "R" else "R"
                    uris.append(crop_card(wc[(c, other)], True))
            pages[it["post_id"]] = wc_page(it["caption"], uris, labels)
            art[it["post_id"]] = "watercolor"
        else:
            pages[it["post_id"]] = page(it["caption"], [(svgs[it["post_id"]][i], labels[i]) for i in range(3)])
            art[it["post_id"]] = "simple"

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={"width": W, "height": H})
        for name, html in pages.items():
            f = os.path.join(tmp, name + ".html"); open(f, "w", encoding="utf-8").write(html)
            pg.goto("file://" + f); pg.wait_for_timeout(150)
            pg.screenshot(path=os.path.join(a.out, "img", name + ".png"))
        b.close()

    print("ok", len(pages), "images", json.dumps(art, ensure_ascii=False))


if __name__ == "__main__":
    main()
