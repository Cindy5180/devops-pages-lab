#!/usr/bin/env python3
"""Release gate for the Pages site. Exit code 1 blocks the deploy.

Checks:
  1. README.md contains both activity-log markers (START before END).
  2. _site/index.html exists and contains the README heading.
  3. Every internal link/src in every built HTML page resolves to a file.
"""
import argparse
import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urlparse, unquote

START, END = "<!--START_SECTION:activity-->", "<!--END_SECTION:activity-->"


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for key in ("href", "src"):
            if a.get(key):
                self.links.append(a[key])


def resolves(site, page_dir, link, baseurl):
    u = urlparse(link)
    if u.scheme in ("http", "https", "mailto", "tel", "data", "javascript") or u.netloc:
        return True  # external: not checked (flaky, out of our control)
    path = unquote(u.path)
    if not path:  # pure "#anchor"
        return True
    if path.startswith("/"):
        if baseurl and path.startswith(baseurl + "/"):
            path = path[len(baseurl):]
        elif baseurl and path == baseurl:
            path = "/"
        target = os.path.join(site, path.lstrip("/"))
    else:
        target = os.path.join(page_dir, path)
    candidates = [target, target + ".html", os.path.join(target, "index.html")]
    return any(os.path.isfile(c) for c in candidates)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--readme", default="README.md")
    p.add_argument("--site", default="_site")
    p.add_argument("--baseurl", default="")
    args = p.parse_args()
    errors = []

    # 1. markers
    readme = open(args.readme, encoding="utf-8").read()
    if START not in readme or END not in readme:
        errors.append("README.md is missing the activity-log markers")
    elif readme.index(START) > readme.index(END):
        errors.append("README.md activity markers are in the wrong order")

    # 2. homepage
    index = os.path.join(args.site, "index.html")
    if not os.path.isfile(index):
        errors.append("_site/index.html was not built")
    else:
        html = open(index, encoding="utf-8").read()
        if "Recent activity" not in html:
            errors.append("Homepage does not render the README (no 'Recent activity')")

    # 3. internal links
    checked = 0
    for root, _, files in os.walk(args.site):
        for f in files:
            if not f.endswith(".html"):
                continue
            page = os.path.join(root, f)
            parser = Links()
            parser.feed(open(page, encoding="utf-8", errors="ignore").read())
            for link in parser.links:
                checked += 1
                if not resolves(args.site, root, link, args.baseurl):
                    rel = os.path.relpath(page, args.site)
                    errors.append(f"Broken link in {rel}: {link}")

    print(f"Checked {checked} links/resources")
    if errors:
        print("VALIDATION FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("VALIDATION PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
