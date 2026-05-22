#!/usr/bin/env python3
"""Generate a Matrix-rain background PNG for the custom GRUB theme.

Outputs a 1920x1080 black image with vertical streams of katakana + digit
glyphs in three shades of green. Static (GRUB themes don't animate).

Usage: python3 gen_matrix_bg.py [output_path]
"""
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
GLYPH_SIZE = 22
COL_SPACING = 24
ROW_SPACING = 26

BG = (0, 0, 0)
HEAD = (168, 255, 176)
BODY = (0, 255, 65)
TAIL = (0, 59, 15)

KATAKANA = [chr(c) for c in range(0x30A0, 0x3100) if chr(c).isprintable()]
DIGITS = list("0123456789")
GLYPHS = KATAKANA + DIGITS + DIGITS

CJK_FONT = "/usr/share/fonts/noto-cjk/NotoSansCJK-Light.ttc"
LATIN_FONT = "/usr/share/fonts/TTF/JetBrainsMonoNerdFont-Regular.ttf"


def shade(color, factor):
    return tuple(max(0, min(255, int(c * factor))) for c in color)


def main(out_path: Path):
    random.seed(20260521)
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    cjk = ImageFont.truetype(CJK_FONT, GLYPH_SIZE)
    latin = ImageFont.truetype(LATIN_FONT, GLYPH_SIZE)

    n_cols = W // COL_SPACING
    rows_visible = H // ROW_SPACING + 2

    for ci in range(n_cols):
        x = ci * COL_SPACING + random.randint(-2, 2)
        head_row = random.randint(-rows_visible, rows_visible)
        stream_len = random.randint(8, 28)

        for k in range(stream_len):
            row = head_row - k
            if row < -1 or row > rows_visible:
                continue
            y = row * ROW_SPACING

            if k == 0:
                color = HEAD
            elif k < 3:
                color = shade(BODY, 1.1)
            elif k < stream_len * 0.6:
                color = BODY
            else:
                fade = 1 - (k - stream_len * 0.6) / (stream_len * 0.4 + 1)
                color = shade(TAIL, 0.6 + fade * 0.8)

            glyph = random.choice(GLYPHS)
            font = latin if glyph.isascii() else cjk

            if random.random() < 0.06 and k > 2:
                continue

            draw.text((x, y), glyph, font=font, fill=color)

    for _ in range(int(n_cols * 0.35)):
        ci = random.randint(0, n_cols - 1)
        x = ci * COL_SPACING + random.randint(-2, 2)
        row = random.randint(0, rows_visible - 1)
        y = row * ROW_SPACING
        glyph = random.choice(GLYPHS)
        font = latin if glyph.isascii() else cjk
        draw.text((x, y), glyph, font=font, fill=shade(TAIL, 0.7))

    img.save(out_path, "PNG", optimize=True)
    print(f"wrote {out_path} ({W}x{H})")


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/matrix_bg.png")
    main(out)
