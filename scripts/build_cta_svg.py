"""Draw the "open the live report" button.

Kept out of build_readme_assets.py because that generator draws a centred pill,
and this one is a left-aligned bar with a play glyph - a different shape, not a
different palette. One file only: the button is a saturated gradient carrying
white text, so it reads the same on all four GitHub surfaces and does not need
a light/dark pair.

Drawn at 2x and displayed at width="665", so halve every size here to judge how
it lands. Nothing may render below ~11px.

    python scripts/build_cta_svg.py
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "cta.svg"

FONT = "system-ui,-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"

LABEL = "Open the live report"
SUBLABEL = "Power BI service  ·  runs in your browser  ·  no sign-in, no cloud account"

W, H = 1330, 260
# The bar itself, inset so the drop shadow has room to fall inside the canvas.
BX, BY, BW, BH, R = 20, 46, 1292, 168, 34


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build() -> str:
    cy = BY + BH / 2
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}"
     width="{W}" height="{H}" role="img" aria-label="{esc(LABEL)}">
  <style>
    .rise {{ animation: rise .5s cubic-bezier(.2,.7,.3,1) both; }}
    @keyframes rise {{ from {{ transform: translateY(8px) }} to {{ transform: translateY(0) }} }}
    .sheen {{ animation: sheen 5s ease-in-out infinite 1.2s; }}
    @keyframes sheen {{ from {{ transform: translateX(-260px) }}
                        to   {{ transform: translateX({W}px) }} }}
    @media (prefers-reduced-motion: reduce) {{
      .rise, .sheen {{ animation: none }}
    }}
  </style>
  <defs>
    <linearGradient id="bar" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#4C6EF5"/>
      <stop offset="55%" stop-color="#6D63F0"/>
      <stop offset="100%" stop-color="#9257EC"/>
    </linearGradient>
    <linearGradient id="sheenfade" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#FFFFFF" stop-opacity="0"/>
      <stop offset="50%" stop-color="#FFFFFF" stop-opacity="0.14"/>
      <stop offset="100%" stop-color="#FFFFFF" stop-opacity="0"/>
    </linearGradient>
    <filter id="sh" x="-10%" y="-60%" width="120%" height="240%">
      <feDropShadow dx="0" dy="10" stdDeviation="14" flood-color="#6D63F0"
                    flood-opacity="0.34"/>
    </filter>
    <clipPath id="clip">
      <rect x="{BX}" y="{BY}" width="{BW}" height="{BH}" rx="{R}"/>
    </clipPath>
  </defs>

  <g class="rise">
    <rect x="{BX}" y="{BY}" width="{BW}" height="{BH}" rx="{R}"
          fill="url(#bar)" filter="url(#sh)"/>
    <g clip-path="url(#clip)">
      <rect class="sheen" x="{BX}" y="{BY}" width="200" height="{BH}" fill="url(#sheenfade)"/>
    </g>

    <g transform="translate(104 {cy:.0f})">
      <circle r="38" fill="none" stroke="#FFFFFF" stroke-opacity="0.72" stroke-width="4"/>
      <path d="M-10 -17 L-10 17 L20 0 Z" fill="#FFFFFF"/>
    </g>

    <text x="180" y="{cy - 8:.0f}" font-family="{FONT}" font-size="38"
          font-weight="700" fill="#FFFFFF">{esc(LABEL)}</text>
    <text x="180" y="{cy + 34:.0f}" font-family="{FONT}" font-size="26"
          fill="#FFFFFF" fill-opacity="0.86">{esc(SUBLABEL)}</text>
  </g>
</svg>
"""


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(), encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
