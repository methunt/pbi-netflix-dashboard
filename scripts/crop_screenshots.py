"""Crop raw Power BI page captures to the report canvas.

The bridge captures the whole Desktop client area, which includes the collapsed
filter pane on the right and a little chrome elsewhere. Cropping by hand is not
reproducible, and a brightness threshold does not work here because the report's
own background is a near-flat dark grey only a few points off the surrounding
chrome.

So: scan inward from each edge for the first row/column whose pixel standard
deviation exceeds a threshold. Chrome is flat, content varies.

The crop is then checked against the page size declared in page.json. A silently
wrong crop ships a misleading image, so a ratio mismatch exits non-zero.

    python scripts/crop_screenshots.py
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "screenshots" / "_raw"
OUT = ROOT / "screenshots"
PAGES = ROOT / "powerbi" / "Netflix.Report" / "definition" / "pages"

# A row/column counts as content once its std dev clears this. Tuned against the
# near-flat #1A1A1A report background; low enough to catch the dark canvas edge,
# high enough to ignore JPEG-ish noise in the flat chrome.
THRESHOLD = 6.0
RATIO_TOLERANCE = 0.04
# Mean luminance below which a row counts as the dark report canvas rather than
# a pale Desktop notification bar.
BANNER_MAX_MEAN = 90


def declared_ratio() -> float:
    """Width/height from the PBIR page definitions. Both pages must agree."""
    ratios = set()
    for page in PAGES.iterdir():
        pj = page / "page.json"
        if not pj.exists():
            continue
        j = json.loads(pj.read_text(encoding="utf-8-sig"))
        w, h = j.get("width"), j.get("height")
        if w and h:
            ratios.add(round(w / h, 4))
    if len(ratios) != 1:
        sys.exit(f"pages declare inconsistent sizes: {ratios}")
    return ratios.pop()


def content_box(img: Image.Image) -> tuple[int, int, int, int]:
    """First row/column from each edge whose deviation says 'this is content'."""
    g = img.convert("L")
    w, h = g.size
    px = g.load()

    # Sample rather than read every pixel; a 3x capture is ~5400px wide and the
    # full scan is needlessly slow for no extra accuracy.
    step = max(1, min(w, h) // 400)

    def col_dev(x: int) -> float:
        return statistics.pstdev([px[x, y] for y in range(0, h, step)])

    def row_dev(y: int) -> float:
        return statistics.pstdev([px[x, y] for x in range(0, w, step)])

    left = next((x for x in range(w) if col_dev(x) > THRESHOLD), 0)
    right = next((x for x in range(w - 1, -1, -1) if col_dev(x) > THRESHOLD), w - 1)
    top = next((y for y in range(h) if row_dev(y) > THRESHOLD), 0)
    bottom = next((y for y in range(h - 1, -1, -1) if row_dev(y) > THRESHOLD), h - 1)
    return left, top, right + 1, bottom + 1


def drop_top_banner(img: Image.Image, left: int, top: int, right: int, bottom: int) -> int:
    """Skip a light notification bar sitting above the report canvas.

    Power BI Desktop shows a pale "pending changes in your queries" strip after a
    model edit. It is chrome, not report content, but it is high-contrast so the
    deviation scan happily calls it content. The report itself is dark
    end-to-end, so the first genuinely dark row is where the canvas starts.

    A no-op on a capture that has no banner.
    """
    g = img.convert("L")
    px = g.load()
    step = max(1, (right - left) // 300)
    limit = top + (bottom - top) // 4  # a banner is never a quarter of the page

    for y in range(top, limit):
        row = [px[x, y] for x in range(left, right, step)]
        if sum(row) / len(row) < BANNER_MAX_MEAN:
            return y
    return top


def main() -> int:
    want = declared_ratio()
    OUT.mkdir(parents=True, exist_ok=True)
    raws = sorted(RAW.glob("*.png"))
    if not raws:
        sys.exit(f"no captures in {RAW}")

    boxes = {}
    for src in raws:
        img = Image.open(src)
        left, top, right, bottom = content_box(img)
        top = drop_top_banner(img, left, top, right, bottom)

        # The collapsed filter pane sits to the right of the canvas and carries a
        # vertical "Filters" label, so it reads as content and inflates the width.
        # The canvas itself is exactly the declared ratio, so any excess width is
        # chrome: trim it off the right rather than accept a lopsided crop.
        height = bottom - top
        want_width = round(height * want)
        if right - left > want_width:
            right = left + want_width
        boxes[src] = (img.size, (left, top, right, bottom))

    # Every page is the same canvas in the same window, so the left and right
    # edges are the same for all of them. Detecting width per image does not give
    # one answer: a capture carrying Desktop's notification banner loses height at
    # the top, and the ratio rule then trims that shortfall off the right, cutting
    # real content out of the frame. So take the widest box found across captures
    # of the same size and impose its horizontal edges on every frame; only the
    # top edge stays per-frame, because only that one genuinely differs.
    shared: dict[tuple[int, int], tuple[int, int, int, int]] = {}
    for size, box in boxes.values():
        best = shared.get(size)
        if best is None or (box[2] - box[0]) > (best[2] - best[0]):
            shared[size] = box

    failed = False
    for src, (size, own) in boxes.items():
        img = Image.open(src)
        ref = shared[size]
        left, right = ref[0], ref[2]
        top = own[1]
        bottom = min(img.height, top + round((right - left) / want))
        note = "" if (left, top, right, bottom) == own else "  (widened to the shared canvas)"

        crop = img.crop((left, top, right, bottom))
        got = crop.width / crop.height
        drift = abs(got - want) / want

        status = "ok"
        if drift > RATIO_TOLERANCE:
            status = f"RATIO MISMATCH (want {want:.3f}, got {got:.3f})"
            failed = True

        dest = OUT / src.name
        crop.save(dest, optimize=True)
        print(f"{src.name}: {img.size} -> {crop.size}  ratio {got:.3f}  {status}{note}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
