#!/usr/bin/env python3
"""
Reorganizes the wallpaper image pools across themes based on each image's
dominant average color. Walks all themes/<name>/images/ files, computes a
mean RGB → HSV per image, and moves it to whichever theme's target hue is
closest. Non-destructive: nothing is deleted, only moved between dirs.

Usage:
    organize_by_color.py            # dry-run preview
    organize_by_color.py --apply    # actually move files
    organize_by_color.py --verbose  # print per-image classification

Themes share hue families (gaming + red both ≈ 0°), and the algorithm splits
those families across each pair by minimum hue distance; if two themes target
the exact same hue, the closer one in the table below wins ties.
"""
import argparse
import colorsys
import shutil
import sys
from pathlib import Path
from PIL import Image

THEMES_DIR = Path.home() / ".config/hypr/themes"

# Target hue (degrees) for each theme. Where two themes share a family,
# offset them slightly so the algorithm gives each side of the family.
THEME_HUE = {
    "gaming":  358,  # pure intense red (a hair below 0)
    "red":     8,    # red slightly toward orange
    "orange":  30,
    "gold":    50,
    "nature":  108,  # cooler green (deeper landscape)
    "green":   135,  # warmer green
    "teal":    165,
    "cyan":    180,
    "blue":    210,
    "coding":  225,  # bluer-violet edge of blue
    "purple":  280,
    "magenta": 315,
}
THUMB = 96


def hue_distance(h1, h2):
    """Circular distance between hues in degrees, in [0, 180]."""
    d = abs(h1 - h2) % 360
    return min(d, 360 - d)


def mean_hsv(path):
    try:
        with Image.open(path) as im:
            im = im.convert("RGB")
            im.thumbnail((THUMB, THUMB))
            pixels = list(im.getdata())
    except Exception:
        return None
    n = len(pixels)
    if not n:
        return None
    r = sum(p[0] for p in pixels) / n / 255
    g = sum(p[1] for p in pixels) / n / 255
    b = sum(p[2] for p in pixels) / n / 255
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return (h * 360.0, s, v)


def best_theme(hsv, current):
    h, s, v = hsv
    # Near-grayscale (snowy mountains, monochrome shots): keep where it is so
    # we don't dump everything into one bucket.
    if s < 0.10:
        return current, None
    best = min(THEME_HUE, key=lambda t: hue_distance(h, THEME_HUE[t]))
    return best, hue_distance(h, THEME_HUE[best])


def collect():
    out = []
    for theme_dir in sorted(THEMES_DIR.iterdir()):
        if not theme_dir.is_dir():
            continue
        img_dir = theme_dir / "images"
        if not img_dir.is_dir():
            continue
        for p in img_dir.iterdir():
            if p.suffix.lower() in (".jpg", ".jpeg", ".png"):
                out.append((p, theme_dir.name))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="actually move files (default: dry-run)")
    ap.add_argument("--verbose", action="store_true", help="print per-image classification")
    args = ap.parse_args()

    all_imgs = collect()
    print(f"analyzing {len(all_imgs)} images …\n")

    plan = []  # (path, current, target, hue, sat, val, distance)
    for i, (p, cur) in enumerate(all_imgs, 1):
        hsv = mean_hsv(p)
        if hsv is None:
            continue
        target, dist = best_theme(hsv, cur)
        plan.append((p, cur, target, hsv, dist))
        if args.verbose:
            h, s, v = hsv
            print(f"  H={h:5.1f} S={s:.2f} V={v:.2f}  {cur:>8} → {target:<8}  {p.name}")
        elif i % 100 == 0:
            print(f"  scored {i}/{len(all_imgs)}")

    # Distribution preview
    before = {}
    after = {}
    moves = 0
    for p, cur, target, _, _ in plan:
        before[cur] = before.get(cur, 0) + 1
        after[target] = after.get(target, 0) + 1
        if cur != target:
            moves += 1

    print("\n=== distribution ===")
    print(f"  {'theme':<10} {'before':>7}  {'after':>7}  Δ")
    themes_all = sorted(set(before) | set(after) | set(THEME_HUE))
    for t in themes_all:
        b = before.get(t, 0)
        a = after.get(t, 0)
        print(f"  {t:<10} {b:>7}  {a:>7}  {a-b:+d}")
    print(f"\n  {moves} files would be moved")

    if not args.apply:
        print("\n(dry run — pass --apply to execute)")
        return

    # Apply moves
    moved = renamed_collision = failed = 0
    for p, cur, target, _, _ in plan:
        if cur == target:
            continue
        dest_dir = THEMES_DIR / target / "images"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / p.name
        if dest.exists():
            # collision: append parent theme name to disambiguate
            dest = dest_dir / f"{p.stem}__from-{cur}{p.suffix}"
            renamed_collision += 1
        try:
            shutil.move(str(p), str(dest))
            moved += 1
        except Exception as e:
            print(f"  ! move failed: {p} → {dest}: {e}")
            failed += 1

    print(f"\n=== applied ===")
    print(f"  moved={moved} collisions_renamed={renamed_collision} failed={failed}")
    print("\nfinal counts:")
    for theme_dir in sorted(THEMES_DIR.iterdir()):
        if theme_dir.is_dir() and (theme_dir / "images").is_dir():
            n = sum(1 for _ in (theme_dir / "images").iterdir())
            print(f"  {theme_dir.name:<10} {n}")


if __name__ == "__main__":
    main()
