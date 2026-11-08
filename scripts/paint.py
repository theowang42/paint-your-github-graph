#!/usr/bin/env python3
"""Paint a pattern into ONE past year of your GitHub contribution graph.

The painter page (docs/index.html) turns text, shapes and drawing into a pattern
code and puts it in the new repo's description. This script reads it back and
makes one backdated commit per contribution. Without --commit it only previews.

    python3 scripts/paint.py --repo 2002-born --description "Time paint 2002 · 22:0440440/..."
"""
import argparse
import datetime as dt
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
# Template files a painting repo doesn't need. LICENSE stays (MIT asks for it); the
# workflow files stay too: a workflow's own token may not delete workflow files.
CLEANUP = ["scripts", "docs", "profile.toml", ".gitignore", "README.zh-CN.md"]

# Pattern code: "<week column>:<row0>/<row1>/.../<row6>", rows Sunday..Saturday.
# Each row is digits 0-4 (0 = empty, 4 = darkest); "0(12)" = twelve 0s.
ROW = r"(?:[0-4](?:\(\d{1,2}\))?)+"
CODE = rf"(\d{{1,2}}):({ROW}(?:/{ROW}){{6}})"


def parse_code(text: str) -> tuple[int, list[str]]:
    m = re.search(rf"(?<![\d:]){CODE}(?![\d(/])", text or "")
    if not m:
        sys.exit("No pattern code found. Create the repo from the painter page.")
    rows = [re.sub(r"([0-4])\((\d+)\)", lambda x: x[1] * int(x[2]), r) for r in m[2].split("/")]
    if len({len(r) for r in rows}) != 1 or len(rows[0]) > 54:
        sys.exit("Bad pattern code: rows differ in length or are too wide.")
    return int(m[1]), rows


def plan(year: int, col: int, rows: list[str]) -> dict[dt.date, int]:
    """Pattern -> {day: commits}. Column 0 is the week holding Jan 1."""
    jan1 = dt.date(year, 1, 1)
    start = jan1 - dt.timedelta(days=(jan1.weekday() + 1) % 7)  # Sunday on/before Jan 1
    days = {}
    for r, line in enumerate(rows):
        for c, ch in enumerate(line):
            if ch != "0":
                d = start + dt.timedelta(days=(col + c) * 7 + r)
                if d.year != year:
                    sys.exit(f"A cell lands on {d}, outside {year}.")
                days[d] = int(ch)
    if not days:
        sys.exit("The pattern is empty.")
    return days


def preview(year: int, days: dict[dt.date, int]) -> str:
    jan1 = dt.date(year, 1, 1)
    lead = (jan1.weekday() + 1) % 7  # empty cells before Jan 1 in the first column
    out = [[" "] * 54 for _ in range(7)]
    for i in range((dt.date(year + 1, 1, 1) - jan1).days):
        d = jan1 + dt.timedelta(days=i)
        out[(i + lead) % 7][(i + lead) // 7] = " ░▒▓█"[days[d]] if d in days else "·"
    head = f"{year} preview: {sum(days.values())} contributions on {len(days)} days"
    return "\n".join([head] + ["".join(r).rstrip() for r in out])


def git(*args: str, env: dict | None = None) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True, text=True,
                          capture_output=True, env=env).stdout.strip()


def commit(year: int, title: str, days: dict[dt.date, int], grid: str) -> None:
    log = ROOT / "painting.log"
    if log.exists():
        sys.exit("This repo is already painted. To redo it, delete the repo and create a new one.")
    if git("status", "--porcelain"):
        sys.exit("The repo has uncommitted changes.")
    # The first commit also swaps in the README and removes the template files.
    # Every commit is dated inside the painted year, so nothing lands on today.
    git("rm", "-rq", "--ignore-unmatch", *CLEANUP)
    (ROOT / "README.md").write_text(
        f"# {year} · {title}\n\n"
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
    p = argparse.ArgumentParser(description="Paint a past year of your contribution graph (preview by default)")
    p.add_argument("--repo", required=True, help="repo name, <year>-<name>, e.g. 2002-born")
    p.add_argument("--description", default="", help="repo description holding the pattern code")
    p.add_argument("--pattern", help="pattern code (overrides --description)")
    p.add_argument("--commit", action="store_true", help="actually make the commits")
    a = p.parse_args()

    m = re.fullmatch(r"(\d{4})-([A-Za-z0-9-]+)", a.repo)
    if not m:
        sys.exit(f"Repo name {a.repo!r} must look like <year>-<name>, e.g. 2002-born.")
    year = int(m[1])
    if not 1970 <= year < dt.date.today().year:
        sys.exit(f"Year must be 1970-{dt.date.today().year - 1}. Past years only.")
    title = " ".join("♥" if w == "HEART" else w for w in m[2].upper().split("-") if w)

    days = plan(year, *parse_code(a.pattern or a.description))
    grid = preview(year, days)
    print(grid)
    if a.commit:
        commit(year, title, days, grid)
    else:
        print("\nPreview only. Nothing was committed.")


if __name__ == "__main__":
    main()
