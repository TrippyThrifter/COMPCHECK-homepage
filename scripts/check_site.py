#!/usr/bin/env python3
"""Static checks for the CompCheck marketing site."""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
PREFIX = "/COMPCHECK-homepage/"

REQUIRED = [
    "index.html",
    "privacy.html",
    "terms.html",
    "contact.html",
    "404.html",
    "css/styles.css",
    "js/nav.js",
    "assets/favicon.svg",
    "assets/favicon-32.png",
    "assets/apple-touch-icon.png",
    "assets/og.png",
    "robots.txt",
    "sitemap.xml",
    ".nojekyll",
]

HTML_PAGES = [
    "index.html",
    "privacy.html",
    "terms.html",
    "contact.html",
    "404.html",
]

FORBIDDEN = [
    re.compile(r"sk_live_"),
    re.compile(r"sk_test_"),
    re.compile(r"rk_live_"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_"),
    re.compile(r"xox[baprs]-"),
    re.compile(r"client_secret"),
    re.compile(r"api[_-]?key\s*[:=]", re.I),
]

TEXT_SUFFIXES = {".html", ".css", ".js", ".yml", ".yaml", ".md", ".txt", ".xml", ".svg", ".py"}


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.h1 = 0
        self.titles = 0
        self.has_main = False
        self.has_lang = False
        self.metas: list[tuple[str, str]] = []
        self.hrefs: list[str] = []
        self.srcs: list[str] = []
        self.links: list[tuple[str, str]] = []
        self.imgs_missing_alt: list[str] = []
        self.buttons_missing_name = 0
        self._button_text = ""
        self._in_button = False
        self._in_title = False
        self.title_text = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {key: value or "" for key, value in attrs}
        if tag == "html" and attr.get("lang"):
            self.has_lang = True
        if "id" in attr and attr["id"]:
            self.ids.append(attr["id"])
        if tag == "h1":
            self.h1 += 1
        if tag == "title":
            self.titles += 1
            self._in_title = True
            self.title_text = ""
        if tag == "main":
            self.has_main = True
        if tag == "meta":
            key = attr.get("name") or attr.get("property") or ""
            self.metas.append((key, attr.get("content", "")))
        if tag == "a":
            self.hrefs.append(attr.get("href", ""))
        if tag in {"img", "script", "link"} and attr.get("href") and tag == "link":
            self.links.append((attr.get("rel", ""), attr.get("href", "")))
        if tag == "script" and attr.get("src"):
            self.srcs.append(attr["src"])
        if tag == "img":
            self.srcs.append(attr.get("src", ""))
            if "alt" not in attr:
                self.imgs_missing_alt.append(attr.get("src", ""))
        if tag == "button":
            self._in_button = True
            self._button_text = attr.get("aria-label", "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag == "button" and self._in_button:
            if not self._button_text.strip():
                self.buttons_missing_name += 1
            self._in_button = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title_text += data
        if self._in_button:
            self._button_text += data


def rel_lum(hex_color: str) -> float:
    value = hex_color.lstrip("#")
    channels = [int(value[index : index + 2], 16) / 255 for index in (0, 2, 4)]

    def channel(component: float) -> float:
        if component <= 0.04045:
            return component / 12.92
        return ((component + 0.055) / 1.055) ** 2.4

    red, green, blue = [channel(component) for component in channels]
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast(foreground: str, background: str) -> float:
    lighter = max(rel_lum(foreground), rel_lum(background))
    darker = min(rel_lum(foreground), rel_lum(background))
    return (lighter + 0.05) / (darker + 0.05)


def resolve_local(page: Path, url: str) -> Path | None:
    if not url or url.startswith(("mailto:", "tel:", "javascript:")):
        return None
    if url.startswith(("http://", "https://")):
        return None
    path = url.split("#", 1)[0]
    if not path:
        return None
    if path.startswith(PREFIX):
        relative = path[len(PREFIX) :]
        if relative in ("", "index.html"):
            return SITE / "index.html"
        return SITE / relative
    if path.startswith("/"):
        return SITE / path.lstrip("/")
    return (page.parent / path).resolve()


def fragment_target(page: Path, url: str) -> tuple[Path, str] | None:
    if "#" not in url or url.startswith(("http://", "https://", "mailto:")):
        return None
    path, fragment = url.split("#", 1)
    if not fragment:
        return None
    if not path:
        return page, fragment
    target = resolve_local(page, path)
    if target is None:
        return None
    return target, fragment


def check_contrast(errors: list[str]) -> None:
    pairs = [
        ("#1a2330", "#f4f1ea", 4.5, "body text on paper"),
        ("#3a4653", "#f4f1ea", 4.5, "secondary text on paper"),
        ("#3a4653", "#ffffff", 4.5, "secondary text on white"),
        ("#083f3d", "#f4f1ea", 4.5, "links on paper"),
        ("#ffffff", "#0e5c59", 4.5, "primary button"),
        ("#ffffff", "#083f3d", 4.5, "primary button hover"),
        ("#1a2330", "#fffcf8", 4.5, "light button"),
        ("#1a2330", "#e4f1f0", 4.5, "light button hover"),
        ("#083f3d", "#e4f1f0", 4.5, "sold status"),
        ("#6b3a12", "#f6eadb", 4.5, "asking status and notice"),
        ("#6b3a12", "#ffffff", 4.5, "sample stamp"),
        ("#3f2912", "#f6eadb", 4.5, "placeholder notice"),
        ("#e7edf0", "#1a2330", 4.5, "footer text"),
        ("#ffffff", "#1a2330", 4.5, "footer links and inverse button"),
        ("#e4f1f0", "#1a2330", 4.5, "footer link hover"),
        ("#0e5c59", "#ffffff", 3.0, "step numbers"),
    ]
    for foreground, background, minimum, label in pairs:
        ratio = contrast(foreground, background)
        if ratio < minimum:
            errors.append(f"Contrast {ratio:.2f}:1 for {label} is below {minimum}:1")


def main() -> int:
    errors: list[str] = []

    for relative in REQUIRED:
        if not (SITE / relative).is_file():
            errors.append(f"Missing required file: site/{relative}")

    pages: dict[Path, PageParser] = {}
    for name in HTML_PAGES:
        path = SITE / name
        if not path.is_file():
            continue
        parser = PageParser()
        parser.feed(path.read_text(encoding="utf-8"))
        pages[path] = parser
        if not parser.has_lang:
            errors.append(f"{name} is missing a lang attribute")
        if parser.h1 != 1:
            errors.append(f"{name} has {parser.h1} h1 elements")
        if parser.titles != 1 or not parser.title_text.strip():
            errors.append(f"{name} is missing a title")
        if not parser.has_main:
            errors.append(f"{name} is missing a main landmark")
        meta = dict(parser.metas)
        if not meta.get("description"):
            errors.append(f"{name} is missing a meta description")
        if not meta.get("viewport"):
            errors.append(f"{name} is missing a viewport meta tag")
        if name != "404.html" and not any(rel == "canonical" and href for rel, href in parser.links):
            errors.append(f"{name} is missing a canonical link")
        if len(parser.ids) != len(set(parser.ids)):
            errors.append(f"{name} has duplicate ids")
        if parser.imgs_missing_alt:
            errors.append(f"{name} has images without alt text")
        if parser.buttons_missing_name:
            errors.append(f"{name} has buttons without an accessible name")

    for page, parser in pages.items():
        for url in parser.hrefs + parser.srcs + [href for _, href in parser.links]:
            target = resolve_local(page, url)
            if target is not None and not target.is_file():
                errors.append(f"{page.name} links to missing file: {url}")
            fragment = fragment_target(page, url)
            if fragment is None:
                continue
            target_page, frag = fragment
            if target_page == page:
                if frag not in parser.ids:
                    errors.append(f"{page.name} links to missing id #{frag}")
                continue
            if target_page in pages and frag not in pages[target_page].ids:
                errors.append(f"{page.name} links to missing id {target_page.name}#{frag}")

    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.resolve() == Path(__file__).resolve():
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in FORBIDDEN:
            if pattern.search(text):
                errors.append(f"Forbidden pattern {pattern.pattern} in {path.relative_to(ROOT)}")

    workflow = ROOT / ".github" / "workflows" / "pages.yml"
    if not workflow.is_file():
        errors.append("Missing GitHub Pages workflow")
    else:
        workflow_text = workflow.read_text(encoding="utf-8")
        for snippet in (
            "actions/checkout@v6",
            "actions/configure-pages@v5",
            "actions/upload-pages-artifact@v4",
            "actions/deploy-pages@v4",
            "pages: write",
            "id-token: write",
            "path: site",
            "github-pages",
        ):
            if snippet not in workflow_text:
                errors.append(f"Pages workflow is missing {snippet}")

    check_contrast(errors)

    if errors:
        print("\n".join(errors))
        return 1
    print(f"Checked {len(pages)} pages and required assets.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
