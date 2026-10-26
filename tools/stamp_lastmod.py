#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Stamp sitemap.xml <lastmod> from the real git commit date of each page.

Why this exists
---------------
`lastmod` is a recrawl hint. When it is older than the last real edit, Google
deprioritises the page and sits on a stale copy; when it is bumped on every
deploy regardless of content, the hint gets distrusted. Both failure modes are
maintenance bugs, not content bugs.

The three generators (gen_category / gen_pillar / gen_trending) each rewrite
only their own sitemap block and stamp it with `today`. The other entries were
hand-maintained, so they drifted: on 2026-10-26 nine pages still claimed
2026-10-12 while their files had last changed 2026-10-24.

This script derives the date from git instead of from a human, so it cannot
drift, and it only ever moves a date *forward* (a generator that already
stamped today is never rolled back).

Usage
-----
    python tools/stamp_lastmod.py            # write
    python tools/stamp_lastmod.py --dry-run  # report only
"""

import datetime
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITEMAP = os.path.join(ROOT, "sitemap.xml")
SITE = "https://ozfurnishing.com"


def git(*args):
    return subprocess.run(["git"] + list(args), cwd=ROOT, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")


def file_for(url):
    """https://ozfurnishing.com/sourcing/lighting -> sourcing/lighting.html"""
    path = url[len(SITE):].split("?")[0].split("#")[0].strip("/")
    if path == "":
        return "index.html"
    return path + ".html"


def main():
    dry = "--dry-run" in sys.argv
    with open(SITEMAP, encoding="utf-8") as fh:
        xml = fh.read()

    today = datetime.date.today().isoformat()
    changes, warnings = [], []

    def repl(m):
        block = m.group(0)
        loc = re.search(r"<loc>([^<]+)</loc>", block).group(1).strip()
        cur = re.search(r"<lastmod>([^<]+)</lastmod>", block)
        cur = cur.group(1).strip() if cur else ""
        rel = file_for(loc)

        if not os.path.exists(os.path.join(ROOT, rel)):
            warnings.append("%-34s no file at %s — left untouched" % (loc, rel))
            return block

        dirty = git("status", "--porcelain", "--", rel).stdout.strip()
        if dirty:
            # Uncommitted work: the commit date is about to be wrong, so use
            # today and say so rather than silently writing a stale date.
            new = today
            warnings.append("%-34s uncommitted changes -> using today" % loc)
        else:
            out = git("log", "-1", "--format=%ad", "--date=short", "--", rel)
            new = out.stdout.strip()
            if not new:
                warnings.append("%-34s not in git yet — left untouched" % loc)
                return block

        if cur and new <= cur:
            return block  # never move a date backwards

        changes.append("%-34s %s -> %s" % (loc, cur or "(none)", new))
        return block.replace("<lastmod>%s</lastmod>" % cur,
                             "<lastmod>%s</lastmod>" % new)

    new_xml = re.sub(r"  <url>.*?</url>", repl, xml, flags=re.S)

    for line in changes:
        print("  bump " + line)
    for line in warnings:
        print("  warn " + line)
    print("-" * 78)

    if not changes:
        print("sitemap lastmod already accurate — nothing to write")
        return 0

    if dry:
        print("%d would change (dry run, file untouched)" % len(changes))
        return 0

    with open(SITEMAP, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(new_xml)
    print("%d lastmod value(s) updated in sitemap.xml" % len(changes))
    return 0


if __name__ == "__main__":
    sys.exit(main())
