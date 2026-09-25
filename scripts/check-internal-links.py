from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import sys

ROOT = Path(__file__).resolve().parents[1]
SKIP_SCHEMES = ("http:", "https:", "mailto:", "tel:", "javascript:", "data:")

class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = set()
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])

html_files = [p for p in ROOT.rglob("*.html") if ".git" not in p.parts]
known = {p.resolve() for p in html_files}
ids = {}
links = {}
for p in html_files:
    parser = Parser()
    parser.feed(p.read_text(encoding="utf-8", errors="replace"))
    ids[p.resolve()] = parser.ids
    links[p.resolve()] = parser.links

errors = []
for src, hrefs in links.items():
    for href in hrefs:
        h = href.strip()
        if not h or h == "#" or h.startswith(SKIP_SCHEMES):
            continue
        parts = urlsplit(h)
        path = unquote(parts.path)
        fragment = unquote(parts.fragment)
        if not path:
            target = src
        elif path.startswith("/"):
            target = ROOT / path.lstrip("/")
        else:
            target = src.parent / path
        if path.endswith("/") or (target.exists() and target.is_dir()):
            target = target / "index.html"
        target = target.resolve()
        if target not in known:
            errors.append(f"{src.relative_to(ROOT)} -> {href} (missing target)")
            continue
        if fragment and fragment not in ids.get(target, set()):
            errors.append(f"{src.relative_to(ROOT)} -> {href} (missing fragment #{fragment})")

if errors:
    print(f"Found {len(errors)} broken internal links:")
    for e in errors:
        print(" -", e)
    sys.exit(1)
print(f"OK: checked {len(html_files)} HTML files; no broken internal HTML links found.")
