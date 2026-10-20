#!/usr/bin/env python3
"""タロットテーブル リールの仮の動画を作る。

本物の動画ができるまでの代わり。日付・テーマ・見出しと、伏せた3枚（左・中・右）を
縦型（1080x1920）の静止画にし、無音の音声を付けた短い MP4 にする。

使い方:
  python3 make_reel_placeholder.py --post-id R0001 --headline "明日からの7日間 10/22(木)~10/28(水)の恋愛" \
      --theme 恋愛 --date 2026-10-21 --out out/R0001.mp4
"""
import argparse
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
SECONDS = 6          # Instagram のリールは3秒以上が必要
FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
]

BG = (30, 24, 48)
FG = (245, 238, 225)
SUB = (190, 180, 210)
CARD = (88, 70, 130)
CARD_EDGE = (214, 186, 120)


def font(size, path=None):
    for p in ([path] if path else []) + FONT_CANDIDATES:
        if p and os.path.exists(p):
            return ImageFont.truetype(p, size, index=0)
    sys.exit("日本語のフォントが見つかりません。--font で場所を渡してください。")


def wrap(draw, text, f, max_w):
    lines, cur = [], ""
    for ch in text:
        if draw.textlength(cur + ch, font=f) > max_w and cur:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def center(draw, y, text, f, fill):
    w = draw.textlength(text, font=f)
    draw.text(((W - w) / 2, y), text, font=f, fill=fill)


def make_frame(args, path):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    f_tag = font(44, args.font)
    f_big = font(64, args.font)
    f_mid = font(52, args.font)
    f_small = font(40, args.font)

    center(d, 170, "仮の動画", f_big, CARD_EDGE)
    center(d, 270, f"{args.post_id}  投稿の日 {args.date}", f_tag, SUB)

    y = 420
    for line in wrap(d, args.headline, f_mid, W - 160):
        center(d, y, line, f_mid, FG)
        y += 76

    # 伏せた3枚
    cw, ch, gap = 270, 450, 45
    x0 = (W - (cw * 3 + gap * 2)) / 2
    top = 780
    for i, label in enumerate(["左", "中", "右"]):
        x = x0 + i * (cw + gap)
        d.rounded_rectangle([x, top, x + cw, top + ch], radius=22, fill=CARD,
                            outline=CARD_EDGE, width=6)
        d.rounded_rectangle([x + 28, top + 28, x + cw - 28, top + ch - 28], radius=14,
                            outline=CARD_EDGE, width=3)
        lw = d.textlength(label, font=f_mid)
        d.text((x + (cw - lw) / 2, top + ch + 30), label, font=f_mid, fill=FG)

    center(d, 1440, f"テーマ：{args.theme}", f_mid, FG)
    center(d, 1600, "本物の動画ができたら差し替えます", f_small, SUB)
    img.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--post-id", required=True)
    ap.add_argument("--headline", required=True)
    ap.add_argument("--theme", required=True)
    ap.add_argument("--date", required=True, help="投稿の日 YYYY-MM-DD")
    ap.add_argument("--out", required=True)
    ap.add_argument("--font", default=None)
    args = ap.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        frame = os.path.join(tmp, "frame.png")
        make_frame(args, frame)
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-loop", "1", "-framerate", "30", "-i", frame,
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-t", str(SECONDS),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high",
            "-r", "30", "-g", "60",
            "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
            "-shortest", "-movflags", "+faststart",
            args.out,
        ]
        subprocess.run(cmd, check=True)
    print(args.out)


if __name__ == "__main__":
    main()
