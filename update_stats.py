"""Fetch live GitHub profile stats and inject them into README.md.

Runs in the GitHub Action (and locally). Reads the public user API for
``vedantdev37`` and rewrites the block between the STATS markers in the
README. Uses ``GITHUB_TOKEN`` when present to lift the anonymous rate limit,
but works without it too.
"""

import os
import re
import sys

import requests

USERNAME = os.environ.get("GH_USERNAME", "vedantdev37")
README_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "README.md")

START = "<!-- STATS:START -->"
END = "<!-- STATS:END -->"


def fetch_stats():
    headers = {"Accept": "application/vnd.github+json"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    resp = requests.get(
        f"https://api.github.com/users/{USERNAME}", headers=headers, timeout=30
    )
    resp.raise_for_status()
    data = resp.json()
    return {
        "public_repos": data.get("public_repos", 0),
        "followers": data.get("followers", 0),
        "following": data.get("following", 0),
    }


def build_block(stats):
    # Rendered inside the terminal <pre> box in README.md. Keep the leading
    # "│" gutter on every line so the box border stays continuous AND so no
    # line is blank (a blank line would end GitHub's HTML block).
    return (
        f"{START}\n"
        f"│   repositories .... {stats['public_repos']}\n"
        f"│   followers ....... {stats['followers']}\n"
        f"│   following ....... {stats['following']}\n"
        f"{END}"
    )


def main():
    stats = fetch_stats()

    with open(README_PATH, "r", encoding="utf-8") as f:
        readme = f.read()

    if START not in readme or END not in readme:
        sys.exit(f"Could not find STATS markers ({START} / {END}) in README.md")

    new_block = build_block(stats)
    updated = re.sub(
        re.escape(START) + r".*?" + re.escape(END),
        new_block,
        readme,
        flags=re.DOTALL,
    )

    if updated != readme:
        with open(README_PATH, "w", encoding="utf-8") as f:
            f.write(updated)
        print(f"Updated stats: {stats}")
    else:
        print(f"Stats unchanged: {stats}")


if __name__ == "__main__":
    main()
