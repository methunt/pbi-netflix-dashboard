"""Draw the semantic model's shape: one CSV, one shared query, three tables.

Hand-written rather than fed through build_readme_assets.py because the layout is
specific to this model - a bridge table and a title-grain table fed by the same
Power Query expression, plus a calendar that is fed by nothing, is not a shape
the generic banner builder knows about.

The same two-variant rule still applies, so the palette is a dict and both files
come out of one pass. Row counts are read from summary.json so the boxes cannot
drift from the data.

    python scripts/build_schema_svg.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FACTS = json.loads((ROOT / "summary.json").read_text(encoding="utf-8"))
OUT = ROOT / "assets"

FONT = "system-ui,-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Consolas,'Liberation Mono',monospace"

LIGHT = {
    "name": "light",
    "card": "#F6F8FA", "card2": "#EEF1F5", "border": "#D0D7DE",
    "text": "#1F2328", "muted": "#656D76",
    "red": "#E50914", "cyan": "#0891B2", "violet": "#7C3AED", "good": "#059669",
    "wash": "0.10", "line": "#8C959F",
}
DARK = {
    "name": "dark",
    "card": "#161B22", "card2": "#1C2128", "border": "#30363D",
    "text": "#E6EDF3", "muted": "#8B949E",
    "red": "#FF404A", "cyan": "#22D3EE", "violet": "#8B5CF6", "good": "#10B981",
    "wash": "0.22", "line": "#484F58",
}

# Drawn at 1200 and read in GitHub's ~900px column, so every size here arrives
# at 0.75x. Nothing may fall below ~11px rendered, which sets the floor at 15 in
# the source - and the row pitch has to move with it.
W, H = 1200, 600
ROW_PITCH = 23


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def table_box(x, y, w, title, subtitle, cols, accent, p, delay):
    """A table card: accent bar, name, grain note, and its key columns."""
    rows = "".join(
        f'<text x="{x + 18}" y="{y + 80 + i * ROW_PITCH}" font-family="{MONO}" '
        f'font-size="15.5" fill="{p["muted"]}">{esc(c)}</text>'
        for i, c in enumerate(cols)
    )
    h = 64 + len(cols) * ROW_PITCH + 16
    return f"""
  <g class="rise" style="animation-delay:{delay:.2f}s">
    <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10"
          fill="{p['card']}" stroke="{p['border']}"/>
    <rect x="{x}" y="{y}" width="{w}" height="4" rx="2" fill="{accent}"/>
    <text x="{x + 18}" y="{y + 32}" font-family="{FONT}" font-size="18.5"
          font-weight="700" fill="{p['text']}">{esc(title)}</text>
    <text x="{x + 18}" y="{y + 55}" font-family="{FONT}" font-size="15"
          fill="{p['muted']}">{esc(subtitle)}</text>
    {rows}
  </g>""", h


def build(p: dict) -> str:
    m, c, g = FACTS["model"], FACTS["catalogue"], FACTS["gaps"]

    # x/y are laid out by hand: source on the left, the shared query and the
    # calendar in the middle, and the two grains the report reads on the right.
    src, src_h = table_box(
        40, 210, 300, "netflix_titles.csv",
        f"{FACTS['source']['raw_rows']:,} rows  ·  {FACTS['source']['columns']} columns",
        ["show_id, type, title", "director, cast, country",
         "date_added, release_year", "rating, duration", "listed_in, description"],
        p["muted"], p, 0.10,
    )

    shared, shared_h = table_box(
        380, 110, 300, "NetflixSource", "shared query  ·  cleansed once",
        ["drop 3 bad-rating rows", "parse date_added", "strip the 's' from show_id",
         "rename to business names", "trim list columns"],
        p["cyan"], p, 0.22,
    )

    # The calendar comes from its own query, not from the CSV, so nothing flows
    # into it - it only flows out, into the bridge.
    dates, dates_h = table_box(
        380, 345, 300, "Date", "calendar  ·  its own query",
        ["Date  ·  Year  ·  Quarter", "Month  ·  Month Name  ·  Day",
         "marked as the date table"],
        p["good"], p, 0.34,
    )

    bridge, bridge_h = table_box(
        720, 100, 440, "Netflix", f"bridge grain  ·  {m['bridge_rows']:,} rows",
        ["one row per title x genre x country",
         "Genre, Country  <- split from lists",
         "Type, Rating, Director, Title", "Date Added  -> Date[Date]"],
        p["red"], p, 0.46,
    )

    titles, titles_h = table_box(
        720, 330, 440, "Dim Title", f"title grain  ·  {c['titles_rows']:,} rows",
        ["one row per title, nothing split",
         "Cast, Release Year, Title, Type", "ID  <- joined from Netflix"],
        p["violet"], p, 0.58,
    )

    # Centres of every card, so the flow lines land on the boxes rather than
    # near them. The bridge is entered twice, at two different heights, so the
    # calendar's line does not sit on top of the shared query's.
    src_mid = 210 + src_h / 2
    shared_mid = 110 + shared_h / 2
    dates_mid = 345 + dates_h / 2
    bridge_mid = 100 + bridge_h / 2
    bridge_low = 100 + bridge_h - 42
    titles_mid = 330 + titles_h / 2
    rel_y = 330 + titles_h + 14

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}"
     width="{W}" height="{H}" role="img"
     aria-label="Model shape: one Kaggle CSV feeds a shared Power Query expression called NetflixSource, which feeds two tables - Netflix, a {m['bridge_rows']:,}-row bridge with genre and country split out, and Dim Title, a {c['titles_rows']:,}-row table at one row per title. A separate Date calendar joins the bridge on Date Added.">
  <style>
    .rise {{ animation: rise .55s cubic-bezier(.2,.7,.3,1) both; }}
    @keyframes rise {{ from {{ transform: translateY(9px) }} to {{ transform: translateY(0) }} }}
    .flow {{ stroke-dasharray: 7 6; animation: flow 1.6s linear infinite; }}
    @keyframes flow {{ to {{ stroke-dashoffset: -26 }} }}
    @media (prefers-reduced-motion: reduce) {{
      .rise, .flow {{ animation: none }}
    }}
  </style>

  <text x="40" y="46" font-family="{FONT}" font-size="26" font-weight="700"
        fill="{p['text']}">One CSV, one shared query, two grains and a calendar</text>
  <text x="40" y="76" font-family="{FONT}" font-size="16"
        fill="{p['muted']}">Splitting the list columns is what makes the questions answerable.</text>

  {src}
  {shared}
  {dates}
  {bridge}
  {titles}

  <g stroke="{p['line']}" stroke-width="2" fill="none" opacity="0.85">
    <path class="flow" d="M340 {src_mid:.0f} H360 V{shared_mid:.0f} H380"/>
    <path class="flow" d="M680 {shared_mid:.0f} H700 V{bridge_mid:.0f} H720"/>
    <path class="flow" d="M680 {shared_mid:.0f} H700 V{titles_mid:.0f} H720"/>
    <path class="flow" d="M680 {dates_mid:.0f} H694 V{bridge_low:.0f} H720"/>
  </g>

  <g class="rise" style="animation-delay:0.70s">
    <rect x="722" y="{rel_y:.0f}" width="436" height="28" rx="14"
          fill="{p['violet']}" fill-opacity="{p['wash']}" stroke="{p['violet']}" stroke-opacity="0.5"/>
    <text x="940" y="{rel_y + 19:.0f}" text-anchor="middle" font-family="{MONO}"
          font-size="15" fill="{p['text']}">Netflix[ID]  many : 1  Dim Title[ID]</text>
  </g>

  <g class="rise" style="animation-delay:0.78s">
    <rect x="722" y="{rel_y + 34:.0f}" width="436" height="28" rx="14"
          fill="{p['good']}" fill-opacity="{p['wash']}" stroke="{p['good']}" stroke-opacity="0.5"/>
    <text x="940" y="{rel_y + 53:.0f}" text-anchor="middle" font-family="{MONO}"
          font-size="15" fill="{p['text']}">Netflix[Date Added]  many : 1  Date[Date]</text>
  </g>
</svg>
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for p in (LIGHT, DARK):
        dest = OUT / f"schema-{p['name']}.svg"
        dest.write_text(build(p), encoding="utf-8")
        print(f"wrote {dest.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
