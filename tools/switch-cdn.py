"""Switch local image references to the Cloudflare R2 CDN domain (and back).

    python tools/switch-cdn.py cdn.ozfurnishing.com     # local -> R2 CDN
    python tools/switch-cdn.py --local                  # R2 CDN -> local

Run this after uploading assets/img/* to the oz-assets bucket and connecting
the cdn.ozfurnishing.com custom domain.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_PREFIX = "/assets/img/"
FILES = [
    "assets/style.css",
    "index.html",
    "c-sourcing.html",
    "b2b-procurement.html",
    "process.html",
    "about.html",
    "inquiry.html",
    "404.html",
]
CDN_RE = re.compile(r"https://cdn\.ozfurnishing\.com/")


def main() -> int:
    args = [a for a in sys.argv[1:]]
    if not args:
        print(__doc__)
        return 1

    if args[0] == "--local":
        target = LOCAL_PREFIX
        pattern = CDN_RE
        direction = "CDN -> local"
    else:
        host = args[0].rstrip("/")
        if not host.startswith("https://"):
            host = "https://" + host
        target = host + "/"
        pattern = re.compile(re.escape(LOCAL_PREFIX))
        direction = "local -> CDN"

    total = 0
    for rel in FILES:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            continue
        src = open(path, encoding="utf-8").read()
        out, n = pattern.subn(target, src)
        if n:
            open(path, "w", encoding="utf-8").write(out)
            print("%-24s %d replaced" % (rel, n))
            total += n

    print("%s: %d references updated" % (direction, total))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
