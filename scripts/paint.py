#!/usr/bin/env python3
"""Paint text or a drawn pattern onto ONE past year of your GitHub contribution graph.

One painting = one repo, named <year>-<text>, e.g. 2002-born.
Default is preview only. --commit makes the commits (the workflow does this
once, when the repo is created).

    python3 scripts/paint.py --repo 2002-born                      # preview
    python3 scripts/paint.py --year 1999 --text HELLO              # preview
    python3 scripts/paint.py --repo 2002-cat --pattern "20:0110/..."  # drawn on the preview page
    python3 scripts/paint.py --repo 2002-cat --description "Time paint 2002 · 20:0110/..."
    python3 scripts/paint.py --repo 2002-born --commit
"""
import argparse
import datetime as dt
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# 7-row pixel font. "#" = lit, "." = empty. Rows separated by "/".
FONT_SRC = {
    "A": ".###./#...#/#...#/#####/#...#/#...#/#...#",
    "B": "####./#...#/#...#/####./#...#/#...#/####.",
    "C": ".###./#...#/#..../#..../#..../#...#/.###.",
    "D": "####./#...#/#...#/#...#/#...#/#...#/####.",
    "E": "#####/#..../#..../####./#..../#..../#####",
    "F": "#####/#..../#..../####./#..../#..../#....",
    "G": ".###./#...#/#..../#.###/#...#/#...#/.###.",
    "H": "#...#/#...#/#...#/#####/#...#/#...#/#...#",
    "I": "#####/..#../..#../..#../..#../..#../#####",
    "J": "..###/...#./...#./...#./...#./#..#./.##..",
    "K": "#...#/#..#./#.#../##.../#.#../#..#./#...#",
    "L": "#..../#..../#..../#..../#..../#..../#####",
    "M": "#...#/##.##/#.#.#/#.#.#/#...#/#...#/#...#",
    "N": "#...#/#...#/##..#/#.#.#/#..##/#...#/#...#",
    "O": ".###./#...#/#...#/#...#/#...#/#...#/.###.",
    "P": "####./#...#/#...#/####./#..../#..../#....",
    "Q": ".###./#...#/#...#/#...#/#.#.#/#..#./.##.#",
    "R": "####./#...#/#...#/####./#.#../#..#./#...#",
    "S": ".####/#..../#..../.###./....#/....#/####.",
    "T": "#####/..#../..#../..#../..#../..#../..#..",
    "U": "#...#/#...#/#...#/#...#/#...#/#...#/.###.",
    "V": "#...#/#...#/#...#/#...#/#...#/.#.#./..#..",
    "W": "#...#/#...#/#...#/#.#.#/#.#.#/#.#.#/.#.#.",
    "X": "#...#/#...#/.#.#./..#../.#.#./#...#/#...#",
    "Y": "#...#/#...#/.#.#./..#../..#../..#../..#..",
    "Z": "#####/....#/...#./..#../.#.../#..../#####",
    "0": ".###./#...#/#..##/#.#.#/##..#/#...#/.###.",
    "1": "..#../.##../..#../..#../..#../..#../.###.",
    "2": ".###./#...#/....#/...#./..#../.#.../#####",
    "3": "####./....#/....#/.###./....#/....#/####.",
    "4": "...#./..##./.#.#./#..#./#####/...#./...#.",
    "5": "#####/#..../####./....#/....#/#...#/.###.",
    "6": ".###./#..../#..../####./#...#/#...#/.###.",
    "7": "#####/....#/...#./..#../.#.../.#.../.#...",
    "8": ".###./#...#/#...#/.###./#...#/#...#/.###.",
    "9": ".###./#...#/#...#/.####/....#/....#/.###.",
    " ": ".../.../.../.../.../.../...",
    "!": "#/#/#/#/#/./#",
    "-": ".../.../.../###/.../.../...",
    ".": "././././././#",
    "♥": ".##.##./#######/#######/#######/.#####./..###../...#...",
}
FONT = {k: v.split("/") for k, v in FONT_SRC.items()}

# "#" and digits 1-4 -> commits per day. More commits = darker green.
LEVEL = {"#": 4, "1": 1, "2": 2, "3": 3, "4": 4}


def text_to_rows(text: str) -> list[str]:
    text = text.upper().replace("<3", "♥")
    rows = [""] * 7
    for i, ch in enumerate(text):
        glyph = FONT.get(ch)
        if glyph is None:
            sys.exit(f"Unsupported character {ch!r}. Use A-Z 0-9 space ! - . ♥ (or <3).")
        for r in range(7):
            rows[r] += ("." if i else "") + glyph[r]
    return rows


def year_grid(year: int) -> tuple[dt.date, int]:
    """First Sunday on/before Jan 1, and number of week columns GitHub shows."""
    jan1 = dt.date(year, 1, 1)
    start = jan1 - dt.timedelta(days=(jan1.weekday() + 1) % 7)
    weeks = (dt.date(year, 12, 31) - start).days // 7 + 1
    return start, weeks


def plan(year: int, rows: list[str], start_col: int | None = None) -> dict[dt.date, int]:
    """rows: 7 strings. start_col None = centre it (text); else the week column (pattern code)."""
    if len(rows) != 7:
        sys.exit("A pattern must have exactly 7 rows (Sun-Sat).")
    width = max(len(r) for r in rows)
    start, weeks = year_grid(year)
    if start_col is None:
        if width > weeks - 2:
            sys.exit(f"Too wide: {width} columns, {year} fits {weeks - 2}. Use about 8 letters or fewer.")
        start_col = (weeks - width) // 2
    days = {}
    for r, line in enumerate(rows):
        for c, ch in enumerate(line):
            if ch in LEVEL:
                d = start + dt.timedelta(days=(start_col + c) * 7 + r)
                if d.year != year:
                    sys.exit(f"A cell lands on {d}, outside {year}.")
                days[d] = LEVEL[ch]
    if not days:
        sys.exit("The pattern is empty.")
    return days


# Pattern code, made by the preview page: "<week column>:<row0>/<row1>/.../<row6>".
# Each row is digits 0-4 (0 = empty, 4 = darkest); "0(12)" = twelve 0s (keeps it short
# enough to fit in a repo description, max 350 chars).
ROW = r"(?:[0-4](?:\(\d{1,2}\))?)+"
CODE = rf"(\d{{1,2}}):({ROW}(?:/{ROW}){{6}})"


def parse_pattern(code: str) -> tuple[int, list[str]]:
    m = re.fullmatch(CODE, code.strip())
    if not m:
        sys.exit("Bad pattern code. Copy it again from the preview page.")
    rows = [re.sub(r"([0-4])\((\d+)\)", lambda x: x[1] * int(x[2]), r)
            for r in m.group(2).split("/")]
    if len({len(r) for r in rows}) != 1 or len(rows[0]) > 54:
        sys.exit("Bad pattern code: rows differ in length or are too wide.")
    return int(m.group(1)), rows


def code_in(description: str) -> str | None:
    """The page puts the code in the repo description: "Time paint 2002 · 20:0110/..."."""
    m = re.search(rf"(?<![\d:]){CODE}(?![\d(/])", description or "")
    return m.group(0) if m else None


def preview(year: int, days: dict[dt.date, int]) -> str:
    start, weeks = year_grid(year)
    shade = {0: "·", 1: "░", 2: "▒", 3: "▓", 4: "█"}
    out = [f"{year} preview: {sum(days.values())} contributions on {len(days)} days"]
    for r in range(7):
        line = ""
        for c in range(weeks):
            d = start + dt.timedelta(days=c * 7 + r)
            line += " " if d.year != year else shade[days.get(d, 0)]
        out.append(line)
    return "\n".join(out)


def git(*args: str, env: dict | None = None) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, text=True,
                          capture_output=True, env=env).stdout.strip()


def parse_repo(name: str) -> tuple[int, str]:
    """2002-born -> (2002, "BORN"); 1999-hi-heart -> (1999, "HI ♥")."""
    m = re.fullmatch(r"(\d{4})-([A-Za-z0-9-]+)", name)
    if not m:
        sys.exit(f"Repo name {name!r} must look like <year>-<text>, e.g. 2002-born.")
    words = ["♥" if w.lower() == "heart" else w for w in m.group(2).split("-") if w]
    return int(m.group(1)), " ".join(words)


# Template files a painting repo doesn't need. The workflow file stays:
# GitHub won't let a workflow's own token delete workflow files.
CLEANUP = ["scripts", "docs", "profile.toml", ".gitignore"]


def commit(year: int, text: str, days: dict[dt.date, int], grid: str) -> None:
    log = ROOT / "painting.log"
    if log.exists():
        sys.exit("This repo is already painted. To redo it, delete the repo and create a new one.")
    if git("status", "--porcelain"):
        sys.exit("The repo has uncommitted changes.")
    # First commit: the README + cleanup. Every commit, this one included, is dated
    # inside the painted year, so nothing lands on today's square.
    git("rm", "-rq", "--ignore-unmatch", *CLEANUP)
    (ROOT / "README.md").write_text(
        f"# {year} · {text.upper()}\n\n"
        f"Backdated commits that draw this into the {year} contribution graph.\n"
        f"Just art. No code was written in {year}.\n\n```\n{grid}\n```\n"
    )
    n = 0
    for d in sorted(days):
        for i in range(days[d]):
            stamp = f"{d.isoformat()}T12:{i:02d}:00+0000"  # noon UTC = same day almost everywhere
            with log.open("a") as f:
                f.write(f"{stamp}\n")
            git("add", "-A")
            env = {**os.environ, "GIT_AUTHOR_DATE": stamp, "GIT_COMMITTER_DATE": stamp}
            git("commit", "-q", "-m", f"timepaint {year}", env=env)
            n += 1
    print(f"Made {n} commits. Undo: delete this repo.")


def main() -> None:
    p = argparse.ArgumentParser(description="Paint text or a pattern into a past year of your contribution graph (preview by default)")
    p.add_argument("--repo", help="repo name, <year>-<text>, e.g. 2002-born")
    p.add_argument("--year", type=int)
    p.add_argument("--text")
    p.add_argument("--pattern", help="pattern code from the preview page; default: the text in the repo name")
    p.add_argument("--description", help="repo description; a pattern code in it is used (--pattern wins)")
    p.add_argument("--commit", action="store_true", help="actually make the commits")
    a = p.parse_args()
    # --pattern > code in the repo description > text in the repo name
    a.pattern = a.pattern or code_in(a.description)

    if a.repo:
        year, text = parse_repo(a.repo)
    elif a.year and (a.text or a.pattern):
        year, text = a.year, a.text or "pattern"
    else:
        sys.exit("Usage: --repo 2002-born, or --year 2002 --text BORN, optionally with --pattern CODE")

    this_year = dt.date.today().year
    if not 1970 <= year < this_year:
        sys.exit(f"Year must be 1970-{this_year - 1}. Past years only.")

    if a.pattern:
        col, rows = parse_pattern(a.pattern)
        days = plan(year, rows, col)
    else:
        days = plan(year, text_to_rows(text))
    grid = preview(year, days)
    print(grid)

    if not a.commit:
        print("\nPreview only. Nothing was committed.")
        return
    commit(year, text, days, grid)


if __name__ == "__main__":
    main()
