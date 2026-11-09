"""Checks a flag submission from a GitHub issue and updates the Hall of Fame.

Submissions are personal hashes, never the flag itself:
    issue title:  flag <sha256 of "yourusername:FLAG{...}">
So an issue title can't leak a flag, and copying someone else's hash is useless.

Inputs (environment, never interpolated into a shell):
    ISSUE_TITLE, ISSUE_AUTHOR  from the issue event
    CTF_FLAGS                  repo secret, one flag per line, in flag order
Writes ctf/solvers.json, the Hall of Fame block in README.md, and ctf/reply.md.
"""

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone

TITLE_RE = re.compile(r"^\s*flag\s+([0-9a-f]{64})\s*$", re.IGNORECASE)
LOGIN_RE = re.compile(r"^[A-Za-z0-9-]{1,39}$")  # GitHub's own login rules
SOLVERS = os.path.join("ctf", "solvers.json")
README = "README.md"
START, END = "<!-- HOF:START -->", "<!-- HOF:END -->"


def personal_hash(login: str, flag: str) -> str:
    return hashlib.sha256(f"{login.lower()}:{flag}".encode()).hexdigest()


def match_flag(title: str, login: str, flags: list[str]) -> int | None:
    """Return the flag number (1-based) the submission proves, or None."""
    m = TITLE_RE.match(title or "")
    if not m or not LOGIN_RE.match(login or ""):
        return None
    submitted = m.group(1).lower()
    for i, flag in enumerate(flags, start=1):
        if personal_hash(login, flag) == submitted:
            return i
    return None


def record(solvers: dict, login: str, n: int, now: str) -> bool:
    """Add flag n for login. Returns False if it was already counted."""
    entry = solvers.setdefault(login.lower(), {"login": login, "flags": [], "first": now})
    if n in entry["flags"]:
        return False
    entry["flags"] = sorted(entry["flags"] + [n])
    entry["last"] = now
    return True


def hall_of_fame(solvers: dict, total: int) -> str:
    if not solvers:
        return "_No one has found a flag yet. Be the first._"
    ranked = sorted(solvers.values(), key=lambda e: (-len(e["flags"]), e.get("last", e["first"])))
    rows = ["| # | Hacker | Flags | Last solve |", "| ---: | --- | ---: | --- |"]
    for i, e in enumerate(ranked[:20], start=1):
        rows.append(f"| {i} | [@{e['login']}](https://github.com/{e['login']}) | {len(e['flags'])} / {total} | {e.get('last', e['first'])[:10]} |")
    return "\n".join(rows)


def write_readme(table: str) -> None:
    with open(README, encoding="utf-8") as f:
        text = f.read()
    block = f"{START}\n{table}\n{END}"
    text = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, text, flags=re.DOTALL)
    with open(README, "w", encoding="utf-8") as f:
        f.write(text)


def main() -> int:
    flags = [line.strip() for line in os.environ.get("CTF_FLAGS", "").splitlines() if line.strip()]
    if not flags:
        sys.exit("CTF_FLAGS secret is empty")
    login = os.environ.get("ISSUE_AUTHOR", "")
    n = match_flag(os.environ.get("ISSUE_TITLE", ""), login, flags)

    solvers = json.load(open(SOLVERS)) if os.path.exists(SOLVERS) else {}
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if n is None:
        reply = ("❌ That doesn't match any flag for your username.\n\n"
                 "Title format: `flag <hash>`, where the hash is\n"
                 "`echo -n \"yourusername:FLAG{...}\" | sha256sum`")
    elif not record(solvers, login, n, now):
        reply = f"You already have flag {n}. {len(solvers[login.lower()]['flags'])} / {len(flags)} found."
    else:
        found = len(solvers[login.lower()]["flags"])
        reply = f"✅ Correct. Flag {n} found ({found} / {len(flags)}). You're on the Hall of Fame."
        if found == len(flags):
            reply += "\n\n🏆 All flags. Respect."
        with open(SOLVERS, "w") as f:
            json.dump(solvers, f, indent=2, sort_keys=True)
        write_readme(hall_of_fame(solvers, len(flags)))

    with open(os.path.join("ctf", "reply.md"), "w", encoding="utf-8") as f:
        f.write(reply + "\n")
    print(reply)
    return 0


if __name__ == "__main__":
    sys.exit(main())
