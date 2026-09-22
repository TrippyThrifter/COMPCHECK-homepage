#!/usr/bin/env python3
"""Validate the static CompCheck marketing site."""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
WORKFLOW = ROOT / ".github" / "workflows" / "pages.yml"

REQUIRED_PAGES = (
    "index.html",
    "privacy.html",
    "terms.html",
    "contact.html",
    "404.html",
)
PLACEHOLDER_PAGES = ("privacy.html", "terms.html", "contact.html")
ALLOWED_URL_PREFIXES = (
    "https://trippythrifter.github.io/COMPCHECK-homepage",
    "https://schema.org",
)
VOID_TAGS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "source",
    "track",
    "wbr",
}
URL_RE = re.compile(r"https?://[^\s\"'<>]+")
SECRET_RES = (
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"sk_live_[0-9A-Za-z]+"),
    re.compile(r"sk_test_[0-9A-Za-z]+"),
    re.compile(r"xox[baprs]-[0-9A-Za-z-]+"),
    re.compile(r"github_pat_[0-9A-Za-z_]+"),
    re.compile(r"(?i)api[_-]?key\s*[:=]\s*['\"][^'\"]+['\"]"),
)
PRIVATE_REPO = "cursor-" + "app-" + "dev"


class PageParser(HTMLParser):
    def __init__(self, name: str) -> None:
        super().__init__(convert_charrefs=True)
        self.name = name
        self.stack: list[str] = []
        self.errors: list[str] = []
        self.ids: set[str] = set()
        self.links: list[tuple[str, str]] = []
        self.has_title = False
        self.has_viewport = False
        self.has_description = False
        self.has_lang = False
        self.has_main = False
        self.has_h1 = False
        self.skip_link = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {key: value for key, value in attrs}
        if tag == "html" and attributes.get("lang"):
            self.has_lang = True
        if tag == "title":
            self.has_title = True
        if tag == "meta" and attributes.get("name") == "viewport":
            self.has_viewport = True
        if tag == "meta" and attributes.get("name") == "description":
            content = attributes.get("content") or ""
            self.has_description = True
            if not 40 <= len(content) <= 170:
                self.errors.append(
                    f"meta description length {len(content)} is outside 40-170"
                )
        if tag == "main":
            self.has_main = True
        if tag == "h1":
            self.has_h1 = True
        element_id = attributes.get("id")
        if element_id:
            if element_id in self.ids:
                self.errors.append(f"duplicate id #{element_id}")
            self.ids.add(element_id)
        for attr in ("href", "src"):
            value = attributes.get(attr)
            if value:
                self.links.append((attr, value))
        if tag == "a":
            href = attributes.get("href") or ""
            label = (attributes.get("aria-label") or "").strip()
            if href.startswith("#") and not label:
                pass
            if tag not in VOID_TAGS:
                self.stack.append(tag)
            return
        if tag == "img" and not (attributes.get("alt") or "").strip() and attributes.get("alt") != "":
            self.errors.append("img is missing alt")
        if tag == "button":
            label = (attributes.get("aria-label") or "").strip()
            if not label:
                self.stack.append(tag)
                self._button_needs_text = True
                return
        if tag not in VOID_TAGS:
            self.stack.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()

    def handle_data(self, data: str) -> None:
        if data.strip() == "Skip to content":
            self.skip_link = True

    def handle_endtag(self, tag: str) -> None:
        if tag in VOID_TAGS:
            return
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(
                f"mismatched </{tag}>; open tags: {self.stack[-4:]}"
            )
            return
        self.stack.pop()

    def close(self) -> None:
        super().close()
        if self.stack:
            self.errors.append(f"unclosed tags: {self.stack}")
        if not self.has_lang:
            self.errors.append("missing html lang")
        if not self.has_title:
            self.errors.append("missing title")
        if not self.has_viewport:
            self.errors.append("missing viewport")
        if not self.has_description:
            self.errors.append("missing meta description")
        if not self.has_main:
            self.errors.append("missing main")
        if not self.has_h1:
            self.errors.append("missing h1")
        if not self.skip_link:
            self.errors.append("missing skip link")


def is_allowed_absolute(url: str) -> bool:
    trimmed = url.rstrip(").,")
    return any(trimmed.startswith(prefix) for prefix in ALLOWED_URL_PREFIXES)


def check_links(page: Path, parser: PageParser, pages: dict[str, PageParser]) -> None:
    for attr, value in parser.links:
        if value.startswith(("javascript:", "data:")):
            parser.errors.append(f"disallowed {attr} {value}")
            continue
        if value.startswith("//"):
            parser.errors.append(f"protocol-relative URL {value}")
            continue
        if value.startswith(("http://", "https://")):
            if not is_allowed_absolute(value):
                parser.errors.append(f"unexpected absolute URL {value}")
            continue
        if value.startswith("mailto:"):
            parser.errors.append(f"unexpected mailto link {value}")
            continue
        path_part, _, fragment = value.partition("#")
        if path_part in ("",):
            if fragment and fragment not in parser.ids:
                parser.errors.append(f"missing fragment #{fragment}")
            continue
        target = (page.parent / path_part).resolve()
        try:
            target.relative_to(SITE.resolve())
        except ValueError:
            parser.errors.append(f"link escapes site directory: {value}")
            continue
        if not target.is_file():
            parser.errors.append(f"broken {attr} {value}")
            continue
        if fragment and target.suffix == ".html":
            other = pages.get(target.name)
            if other and fragment not in other.ids:
                parser.errors.append(f"missing fragment {value}")


def check_secrets(path: Path, text: str, errors: list[str]) -> None:
    if PRIVATE_REPO in text:
        errors.append(f"{path.relative_to(ROOT)} references a private repository name")
    for pattern in SECRET_RES:
        if pattern.search(text):
            errors.append(f"{path.relative_to(ROOT)} matched a secret-like pattern")
            break
    lowered = text.lower()
    for banned in ("lorem ipsum", "todo", "fixme"):
        if banned in lowered:
            errors.append(f"{path.relative_to(ROOT)} contains {banned}")


def check_workflow(errors: list[str]) -> None:
    if not WORKFLOW.is_file():
        errors.append("missing GitHub Pages workflow")
        return
    text = WORKFLOW.read_text(encoding="utf-8")
    check_secrets(WORKFLOW, text, errors)
    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        errors.append(f"workflow YAML is invalid: {exc}")
        return
    if not isinstance(document, dict):
        errors.append("workflow YAML must be a mapping")
        return
    jobs = document.get("jobs") or {}
    for name in ("check", "build", "deploy"):
        if name not in jobs:
            errors.append(f"workflow is missing the {name} job")
    upload = (
        jobs.get("build", {})
        .get("steps", [{}])[-1]
        .get("with", {})
        .get("path")
    )
    # The upload step is not guaranteed to be last if the file changes.
    found_path = None
    for step in jobs.get("build", {}).get("steps", []):
        if isinstance(step, dict) and "with" in step and "path" in step["with"]:
            found_path = step["with"]["path"]
    if found_path != "site":
        errors.append(f"workflow artifact path is {found_path!r}, expected 'site'")
    deploy_steps = jobs.get("deploy", {}).get("steps", [])
    uses = [step.get("uses", "") for step in deploy_steps if isinstance(step, dict)]
    if not any(item.startswith("actions/deploy-pages@") for item in uses):
        errors.append("workflow does not deploy with actions/deploy-pages")
    if upload is None and found_path is None:
        errors.append("workflow upload path was not found")


def main() -> int:
    errors: list[str] = []
    pages: dict[str, PageParser] = {}
    html_paths = sorted(SITE.glob("*.html"))
    found = {path.name for path in html_paths}
    for name in REQUIRED_PAGES:
        if name not in found:
            errors.append(f"missing {name}")

    for path in html_paths:
        parser = PageParser(path.name)
        text = path.read_text(encoding="utf-8")
        check_secrets(path, text, errors)
        parser.feed(text)
        parser.close()
        pages[path.name] = parser

    for path in html_paths:
        check_links(path, pages[path.name], pages)
        for problem in pages[path.name].errors:
            errors.append(f"{path.name}: {problem}")

    for name in PLACEHOLDER_PAGES:
        text = (SITE / name).read_text(encoding="utf-8")
        if "Placeholder." not in text:
            errors.append(f"{name} is missing a clearly marked placeholder notice")

    for relative in ("css/styles.css", "js/nav.js", "favicon.svg", "robots.txt", "sitemap.xml"):
        asset = SITE / relative
        if not asset.is_file() or asset.stat().st_size == 0:
            errors.append(f"missing asset {relative}")
        elif relative.endswith((".css", ".js", ".svg", ".txt", ".xml")):
            check_secrets(asset, asset.read_text(encoding="utf-8"), errors)

    check_workflow(errors)

    readme = ROOT / "README.md"
    if readme.is_file():
        check_secrets(readme, readme.read_text(encoding="utf-8"), errors)

    if errors:
        print(f"{len(errors)} problem(s):")
        for problem in errors:
            print(f"- {problem}")
        return 1

    print(f"Checked {len(html_paths)} HTML pages, assets, links, and the Pages workflow.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
