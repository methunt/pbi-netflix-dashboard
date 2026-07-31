"""Capture the bookmark views the Desktop Bridge CLI cannot reach on its own.

The dashboard's Summary / Movies / TV Shows views are bookmarks, and the bridge
has no bookmark command. But a bookmark is just a recorded visibility state, and
PBIR stores visibility on disk - so the state can be applied to the page files,
reloaded, and captured.

Each bookmark's `explorationState` carries two things this cares about:

    visualContainers      per-visual hidden flags (here, the red nav indicators)
    visualContainerGroups per-group hidden flags (here, the actual chart sets)

The script writes one state, reloads Desktop, captures, then moves to the next -
and always restores the report files from git at the end, including on failure.
Nothing is left modified.

    python scripts/capture_bookmarks.py --pid 8784
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / "powerbi" / "Netflix.Report"
DEFN = REPORT_DIR / "definition"
BOOKMARKS = DEFN / "bookmarks"
VISUALS = DEFN / "pages" / "ReportSection" / "visuals"
RAW = ROOT / "screenshots" / "_raw"
PAGE_ID = "ReportSection"

# Bookmark file stem -> output name. Default Summary is already the on-disk
# state and is captured by the ordinary screenshot run, so it is not repeated.
WANTED = {
    "Bookmark39d5e201f4587c6eddb3": "Movies",
    "Bookmark17bbaeeb5e7653c4dbee": "TVShows",
}


def run(*cmd: str) -> str:
    # The Power BI CLIs are npm shims, which on Windows are `.cmd` files that
    # CreateProcess will not resolve on its own. shutil.which finds the real
    # entry point so this still runs without a shell.
    exe = shutil.which(cmd[0]) or cmd[0]
    proc = subprocess.run([exe, *cmd[1:]], capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)}\n{proc.stdout}\n{proc.stderr}")
    return proc.stdout


def hidden_state(stem: str) -> dict[str, bool]:
    """Flatten a bookmark into {visual id: should be hidden}."""
    j = json.loads((BOOKMARKS / f"{stem}.bookmark.json").read_text(encoding="utf-8-sig"))
    section = j["explorationState"]["sections"][PAGE_ID]

    state: dict[str, bool] = {}
    for vid, v in section.get("visualContainers", {}).items():
        state[vid] = v.get("singleVisual", {}).get("display", {}).get("mode") == "hidden"
    for gid, g in section.get("visualContainerGroups", {}).items():
        state[gid] = bool(g.get("isHidden"))
        for cid, c in (g.get("children") or {}).items():
            state[cid] = bool(c.get("isHidden"))
    return state


def apply_state(state: dict[str, bool]) -> int:
    """Write the visibility flags into the page's visual.json files."""
    touched = 0
    for vid, hide in state.items():
        path = VISUALS / vid / "visual.json"
        if not path.exists():
            continue
        j = json.loads(path.read_text(encoding="utf-8-sig"))
        before = j.get("isHidden", False)
        if hide:
            j["isHidden"] = True
        else:
            # Absent means visible; keep the file canonical rather than writing false.
            j.pop("isHidden", None)
        if before != hide:
            touched += 1
        # utf-8 without a BOM: Desktop refuses to open a PBIP file carrying one.
        path.write_text(json.dumps(j, indent=2) + "\n", encoding="utf-8")
    return touched


def error_count() -> int:
    """Validator error count for the report as it currently sits on disk.

    This report already fails `validate` untouched - 39 PBIR_PROJECTION_MISSING_
    NATIVE_QUERY_REF errors that Power BI Desktop itself authored and renders
    fine. So "must pass" is the wrong gate; "must not get worse than the
    baseline" is the one that actually catches damage from this script.
    """
    proc = subprocess.run(
        [shutil.which("powerbi-report-author") or "powerbi-report-author",
         "validate", str(REPORT_DIR)],
        capture_output=True, text=True,
    )
    try:
        return json.loads(proc.stdout)["data"]["errorCount"]
    except (json.JSONDecodeError, KeyError) as e:
        raise RuntimeError(f"could not read validator output: {e}\n{proc.stdout[:400]}")


def snapshot(ids: set[str]) -> dict[Path, bytes]:
    """Exact bytes of every file this run may touch.

    Restoring from an in-memory snapshot rather than `git checkout` means the
    script does not require a clean working tree, so it can run alongside other
    uncommitted work without either clobbering it or refusing to start.
    """
    saved = {}
    for vid in ids:
        path = VISUALS / vid / "visual.json"
        if path.exists():
            saved[path] = path.read_bytes()
    return saved


def restore(saved: dict[Path, bytes]) -> None:
    for path, data in saved.items():
        path.write_bytes(data)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pid", required=True)
    ap.add_argument("--scale", default="3")
    args = ap.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    baseline = error_count()
    print(f"baseline validator errors: {baseline}")

    touched: set[str] = set()
    for stem in WANTED:
        touched |= set(hidden_state(stem))
    saved = snapshot(touched)

    try:
        for stem, name in WANTED.items():
            changed = apply_state(hidden_state(stem))
            print(f"{name}: {changed} visuals retargeted")
            now = error_count()
            if now > baseline:
                raise RuntimeError(
                    f"{name}: validation regressed, {baseline} -> {now} errors"
                )
            run("powerbi-desktop", "reload", "--pid", args.pid)
            run(
                "powerbi-desktop", "screenshot", PAGE_ID,
                "--pid", args.pid,
                "--output", str(RAW / f"{name}.png"),
                "--scale", args.scale,
                "--wait-seconds", "90",
            )
            print(f"{name}: captured -> screenshots/_raw/{name}.png")
    finally:
        restore(saved)
        print(f"restored {len(saved)} report files to their pre-run contents")
        # Leave Desktop showing the real files again, not the last applied state.
        try:
            run("powerbi-desktop", "reload", "--pid", args.pid)
        except RuntimeError as e:
            print(f"warning: could not reload Desktop after restore: {e}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
