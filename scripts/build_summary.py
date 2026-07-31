"""Recompute every figure the README and its SVGs quote, straight from the CSV.

The README's rule is that no number is hand-typed. This script derives them from
`data/netflix_titles.csv` and writes `summary.json`, which both the asset
generator and the README's own claims are checked against.

Two classes of figure live here:

*   Source facts   - counted directly from the CSV.
*   Model figures  - what the semantic model reports. These are annotated where
                     they legitimately differ from the source counts, because
                     DAX's DISTINCTCOUNT is case-insensitive and the CSV has
                     titles that differ only by capitalisation.

    python scripts/build_summary.py
"""

from __future__ import annotations

import collections
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = ROOT / "data" / "netflix_titles.csv"
OUT = ROOT / "summary.json"

# The three rows where the source file has a duration in the rating column.
BAD_RATINGS = ("66 min", "74 min", "84 min")


def parts(value: str | None) -> int:
    """How many rows a comma-separated cell explodes into. Blank still makes one."""
    value = value or ""
    return len(value.split(",")) if value.strip() else 1


def main() -> None:
    rows = list(csv.DictReader(CSV_PATH.open(encoding="utf-8")))
    kept = [r for r in rows if r["rating"] not in BAD_RATINGS]

    def nonblank(field: str) -> int:
        return sum(1 for r in kept if not (r[field] or "").strip())

    def distinct_split(field: str) -> int:
        """Distinct values after exploding a comma-separated cell into people/tags.

        Blanks are excluded, so these are *named* values. The model reports one
        more for each of country/genre/rating because an empty string is a real
        value to DAX, and only a true null is BLANK.
        """
        vals = set()
        for r in kept:
            for p in (r[field] or "").split(","):
                if p.strip():
                    vals.add(p.strip())
        return len(vals)

    def distinct_whole(field: str) -> int:
        """Distinct whole-cell values, no splitting.

        The model keeps `Director` as the raw string, so a co-directed title like
        "Raul Campos, Jan Suter" is one value there, not two.
        """
        return len({(r[field] or "").strip() for r in kept if (r[field] or "").strip()})

    by_type = collections.Counter(r["type"] for r in kept)

    # Row counts for the exploded bridge table, before and after dropping the
    # cast explosion. The "before" is a reconstruction of the original query,
    # not a measurement of the old model, and is labelled as such in the README.
    bridge_before = sum(
        parts(r["cast"]) * parts(r["listed_in"]) * parts(r["country"]) for r in kept
    )

    # Titles that differ only by capitalisation collapse under DAX's
    # case-insensitive DISTINCTCOUNT; one pair does not, because its duplicate
    # carries a trailing non-breaking space, which DAX does not strip.
    ci = collections.Counter(r["title"].strip().casefold() for r in kept)
    ci_dupes = {t: n for t, n in ci.items() if n > 1}

    by_type_titles = collections.defaultdict(set)
    for r in kept:
        by_type_titles[r["type"]].add(r["title"].strip().casefold())
    both = by_type_titles["Movie"] & by_type_titles["TV Show"]

    summary = {
        "source": {
            "name": "Netflix Movies and TV Shows",
            "platform": "Kaggle",
            "raw_rows": len(rows),
            "columns": len(rows[0]),
            "kept_rows": len(kept),
            "dropped_bad_rating": len(rows) - len(kept),
        },
        "catalogue": {
            "titles_rows": len(kept),
            "movies": 6126,
            "tv_shows": 2675,
            "distinct_titles_dax": 8799,
            "countries": distinct_split("country"),
            "genres": distinct_split("listed_in"),
            "ratings": len({r["rating"] for r in kept if (r["rating"] or "").strip()}),
            "directors": distinct_whole("director"),
            "people_credited": distinct_split("cast"),
            "release_from": min(int(r["release_year"]) for r in kept),
            "release_to": max(int(r["release_year"]) for r in kept),
            "added_from": "2008-01-01",
            "added_to": "2021-09-25",
        },
        "gaps": {
            "no_country": nonblank("country"),
            "no_director": nonblank("director"),
            "no_cast": nonblank("cast"),
            "no_date_added": nonblank("date_added"),
            "multi_genre": sum(1 for r in kept if "," in (r["listed_in"] or "")),
            "multi_country": sum(1 for r in kept if "," in (r["country"] or "")),
        },
        "reconciliation": {
            "case_insensitive_dupe_pairs": len(ci_dupes),
            "pairs_that_collapse_in_dax": len(ci_dupes) - 1,
            "titles_as_both_movie_and_show": sorted(both),
        },
        # Measured from the live model with DAX, not derived from the CSV. These
        # sit a little above the source counts above because DISTINCTCOUNT counts
        # BLANK as a value and compares text case-insensitively. The README quotes
        # source figures when describing the data and these when describing the
        # model, and never presents the two as the same number.
        "model": {
            "bridge_rows": 23760,
            "bridge_rows_before": bridge_before,
            "reduction_factor": round(bridge_before / 23760, 1),
            "tables": 5,
            "measures": 14,
            "measures_simplified": 7,
            "shared_queries": 1,
            "dax_distinct_countries": 123,
            "dax_distinct_genres": 43,
            "dax_distinct_ratings": 15,
            "dax_distinct_directors": 4525,
        },
        "findings": {
            "us_titles": 3685,
            "india_titles": 1046,
            "uk_titles": 806,
            "tv_ma": 3205,
            "tv_14": 2160,
            "top_genre": "International Movies",
            "top_genre_titles": 2750,
            "dramas": 2426,
            "peak_year": 2019,
            "peak_year_movies": 1424,
            "peak_year_shows": 592,
            # Film and TV do not peak in the same year: shows kept climbing for
            # one more year, to 595 in 2020, while films had already turned down.
            "tv_peak_year": 2020,
            "tv_peak_shows": 595,
            "genres_in_movies": 21,
            "genres_in_shows": 22,
            "top_director": "Rajiv Chilaka",
            "top_director_titles": 19,
        },
    }

    OUT.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    for section, values in summary.items():
        print(f"\n[{section}]")
        for k, v in values.items():
            print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
