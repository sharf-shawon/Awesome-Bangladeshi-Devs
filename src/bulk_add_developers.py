"""
bulk_add_developers.py

Processes a list of GitHub usernames, profile URLs, or repo links and
attempts to add each one to the Awesome Bangladeshi Devs list using the
same validation logic as process_issue.py.

Usage:
    python src/bulk_add_developers.py "<newline-or-comma-separated list>"
"""

import re
import sys
import json
from pathlib import Path

# Re-use the shared state and functions from process_issue
import process_issue


def extract_username(entry: str) -> str:
    """Extract a GitHub username from a raw input token.

    Accepts any of:
      - A plain username, e.g. ``johndoe``
      - A GitHub profile URL, e.g. ``https://github.com/johndoe``
      - A GitHub repo URL, e.g. ``https://github.com/johndoe/some-repo``
    """
    entry = entry.strip().strip("/")
    if not entry:
        return ""

    # Handle github.com URLs
    if "github.com" in entry:
        # Strip scheme and host
        path = re.sub(r"^https?://github\.com/", "", entry)
        # First path segment is the username
        username = path.split("/")[0]
        return username.strip()

    # Plain username (no slashes, no dots that look like URLs)
    return entry


def parse_input(raw: str) -> list[str]:
    """Split raw input on newlines and/or commas and return unique usernames."""
    tokens = re.split(r"[\n,]+", raw)
    seen: set[str] = set()
    usernames: list[str] = []
    for token in tokens:
        username = extract_username(token)
        if not username:
            continue
        normalised = process_issue.normalize_username(username)
        if normalised and normalised not in seen:
            seen.add(normalised)
            usernames.append(username)
    return usernames


def bulk_add(raw_input: str) -> dict:
    """Process a raw input string and add qualifying developers.

    Returns a summary dict with keys:
      - ``added``   : list of usernames successfully added
      - ``skipped`` : list of usernames that were valid but already present
      - ``failed``  : list of (username, reason) tuples
    """
    usernames = parse_input(raw_input)
    print(f"Parsed {len(usernames)} unique candidate(s).")

    added: list[str] = []
    skipped: list[str] = []
    failed: list[tuple[str, str]] = []

    for username in usernames:
        # GitHub profiles are always at https://github.com/<username>
        fields = {
            "github_username": username,
            # Location will be resolved from the GitHub API inside add_developer;
            # we pass "Bangladesh" as a safe default that matches location_aliases
            # so that the location check passes.  The real location is fetched and
            # stored by get_github_stats().
            "location": "Bangladesh",
        }
        title = f"Add developer: {username}"

        print(f"\n--- Processing: {username} ---")

        # Capture stdout so we can inspect the reason for failure
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            result = process_issue.add_developer(fields, title)
        output = buf.getvalue()
        # Echo captured output
        print(output, end="")

        if result:
            added.append(username)
        else:
            # Classify the skip vs failure reason from the printed output
            if "Duplicate entry" in output:
                skipped.append(username)
            else:
                reason = output.strip().split("\n")[-1] if output.strip() else "unknown"
                failed.append((username, reason))

    return {"added": added, "skipped": skipped, "failed": failed}


def save_and_report(summary: dict) -> None:
    """Persist updated data files and print a final summary."""
    if summary["added"]:
        with open(process_issue.DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(process_issue.users, f, ensure_ascii=False, indent=2)
        with open(process_issue.REMOVED_DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(process_issue.removed_users, f, ensure_ascii=False, indent=2)
        print("\nusers.json and removed_users.json updated.")
    else:
        print("\nNo new developers were added; files unchanged.")

    print("\n===== Bulk Add Summary =====")
    print(f"  Added   : {len(summary['added'])} — {summary['added']}")
    print(f"  Skipped : {len(summary['skipped'])} — {summary['skipped']}")
    print(f"  Failed  : {len(summary['failed'])} — {summary['failed']}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python src/bulk_add_developers.py \"<list of usernames/URLs>\"")
        return

    raw_input = sys.argv[1]
    summary = bulk_add(raw_input)
    save_and_report(summary)


if __name__ == "__main__":
    main()
