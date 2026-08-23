#!/usr/bin/env python3
"""Static internal-link integrity for every committed page.

For each *.html file in the repository (generated pages included):
  * every internal href/src (site-absolute or relative, no scheme) must
    resolve to a committed file (directory links resolve via index.html);
  * every in-page fragment href="#x" must match an id in the same page;
  * every cross-page fragment /path/#x must match an id in the target page.

External URLs are not fetched here — support-URL liveness belongs to
verify_claims.py, and full external link checking is a manual/CI-weekly
concern. Exit 0 = no broken internal references.
"""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

failures: list[str] = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL  {msg}")


def resolve(page: pathlib.Path, target: str) -> pathlib.Path | None:
    path = target.split("#", 1)[0].split("?", 1)[0]
    if not path:
        return page
    base = ROOT if path.startswith("/") else page.parent
    candidate = (base / path.lstrip("/")).resolve()
    if candidate.is_dir():
        candidate = candidate / "index.html"
    return candidate if candidate.exists() else None


def ids_of(path: pathlib.Path, cache: dict) -> set:
    if path not in cache:
        cache[path] = set(re.findall(r'id="([^"]+)"', path.read_text()))
    return cache[path]


def main() -> int:
    pages = sorted(p for p in ROOT.rglob("*.html")
                   if ".git" not in p.parts and "node_modules" not in p.parts)
    id_cache: dict = {}
    checked = 0
    for page in pages:
        html = page.read_text()
        rel = page.relative_to(ROOT)
        for attr, target in re.findall(r'(href|src)="([^"]+)"', html):
            if target.startswith(("http://", "https://", "mailto:", "data:",
                                  "//", "javascript:")):
                continue
            checked += 1
            if target.startswith("#"):
                if target[1:] and target[1:] not in ids_of(page, id_cache):
                    fail(f"{rel}: broken in-page anchor {target}")
                continue
            resolved = resolve(page, target)
            if resolved is None:
                fail(f"{rel}: {attr} does not resolve — {target}")
                continue
            frag = target.split("#", 1)
            if len(frag) == 2 and frag[1] and resolved.suffix == ".html":
                if frag[1] not in ids_of(resolved, id_cache):
                    fail(f"{rel}: fragment #{frag[1]} missing in {target}")
    print(f"checked {checked} internal references across {len(pages)} pages")
    if failures:
        print(f"{len(failures)} broken internal reference(s).")
        return 1
    print("Internal links verified: every committed reference resolves.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
