# CompCheck homepage

Public marketing website for CompCheck, a reseller pricing and comps research tool.

This repository contains only that public site: static HTML, CSS, and JavaScript. It does not include the CompCheck application, accounts, payments, or private systems.

## Preview locally

From the repository root:

```bash
python3 -m http.server 8080 --directory site
```

Open `http://127.0.0.1:8080/`.

## Pages

| File | Purpose |
| --- | --- |
| `site/index.html` | Homepage |
| `site/privacy.html` | Privacy placeholder |
| `site/terms.html` | Terms placeholder |
| `site/contact.html` | Contact and access placeholder |
| `site/404.html` | Not found |

Privacy, terms, and contact are clearly marked placeholders. Replace them with reviewed text and a real public contact method before relying on them. Do not add credentials or private application links.

## GitHub Pages

`.github/workflows/pages.yml` checks the site, then on `main` uploads the `site` directory and deploys it with GitHub Actions.

After this workflow is on `main`, set the repository Pages source to **GitHub Actions** under Settings, Pages. That setting does not change repository visibility.

Expected site URL:

`https://trippythrifter.github.io/COMPCHECK-homepage/`

No secrets or environment variables are required.

## Check

```bash
python3 tools/check_site.py
```

The script checks HTML structure, local links, required pages, and the workflow file.
