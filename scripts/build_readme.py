#!/usr/bin/env python3
"""Build README.md (your GitHub profile page) from profile.toml."""
import argparse
import os
import pathlib
import tomllib

ROOT = pathlib.Path(__file__).resolve().parent.parent


def build(cfg: dict, user: str) -> str:
    out = [f"# {cfg.get('name', user)}", ""]
    if cfg.get("tagline"):
        out += [cfg["tagline"], ""]
    for line in cfg.get("about", []):
        out.append(f"- {line}")
    if cfg.get("about"):
        out.append("")
    if cfg.get("skills"):
        out += [" ".join(f"`{s}`" for s in cfg["skills"]), ""]
    if cfg.get("links"):
        out += [" · ".join(f"[{k}]({v})" for k, v in cfg["links"].items()), ""]
    if cfg.get("snake", True):
        base = f"https://raw.githubusercontent.com/{user}/{user}/output"
        out += [
            "<picture>",
            f'  <source media="(prefers-color-scheme: dark)" srcset="{base}/github-snake-dark.svg">',
            f'  <img alt="snake eating my contribution graph" src="{base}/github-snake.svg">',
            "</picture>",
            "",
        ]
    return "\n".join(out)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", default=str(ROOT / "README.md"))
    a = p.parse_args()
    cfg = tomllib.loads((ROOT / "profile.toml").read_text())
    user = os.environ.get("GITHUB_REPOSITORY_OWNER", "your-username")
    pathlib.Path(a.out).write_text(build(cfg, user))
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
