"""Build the looping page tour from the cropped captures.

Four frames, in the order a reader meets the report: the profile picker, then
each of the three views the left rail switches between. The three dashboard
views are bookmark states, captured by scripts/capture_bookmarks.py.

    python scripts/build_tour_gif.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "screenshots"
OUT = ROOT / "assets" / "tour.gif"

# Order matters: this is the order a reader meets the report in.
FRAMES = ["Home.png", "Berlin.png", "Movies.png", "TVShows.png"]
WIDTH = 1000
MS_PER_FRAME = 2800


def main() -> None:
    frames = []
    for name in FRAMES:
        src = SHOTS / name
        if not src.exists():
            raise SystemExit(f"missing capture: {src}")
        im = Image.open(src).convert("RGB")
        im = im.resize((WIDTH, round(im.height * WIDTH / im.width)), Image.LANCZOS)
        # Flat dark UI quantises well, so cutting the palette costs little and
        # saves more than shrinking the frame would.
        frames.append(im.quantize(colors=128, method=Image.MEDIANCUT))

    frames[0].save(
        OUT,
        save_all=True,
        append_images=frames[1:],
        duration=MS_PER_FRAME,
        loop=0,
        optimize=True,
    )
    kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT.relative_to(ROOT)}  {len(frames)} frames  {kb:.0f} KB")


if __name__ == "__main__":
    main()
