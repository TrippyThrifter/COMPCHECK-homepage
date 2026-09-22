# CompCheck

Public marketing website for CompCheck, a pricing and comps research tool for online resellers.

This repository contains only the public site: static HTML, CSS, JavaScript, and assets. It does not include an application backend, credentials, or customer data.

## Preview locally

From the repository root:

```bash
python3 -m http.server 8080 -d site
```

Then open `http://127.0.0.1:8080/`.

## Pages

- `site/index.html` — homepage
- `site/contact.html` — contact and access-request placeholder
- `site/privacy.html` — privacy placeholder
- `site/terms.html` — terms placeholder
- `site/404.html` — missing-page message

Privacy, Terms, and Contact are drafts. Replace them when final text and a public contact method are ready. Do not invent customer counts, reviews, or performance claims on these pages.

## GitHub Pages

`.github/workflows/pages.yml` checks the site on pull requests, then on `main` uploads the `site/` directory and deploys it with GitHub Actions.

In the repository settings, set **Pages → Build and deployment → Source** to **GitHub Actions**. Publishing starts after that setting is saved and the workflow runs on `main`.

Expected site URL:

`https://trippythrifter.github.io/COMPCHECK-homepage/`

`site/404.html` uses root-absolute links under `/COMPCHECK-homepage/` so assets still load when GitHub Pages serves the file for a missing path.

## Check

```bash
python3 scripts/check_site.py
```

The same check runs in `.github/workflows/check.yml` and in the Pages workflow.

## Fonts

Newsreader and Source Sans 3 are included under the SIL Open Font License. License texts are in `site/assets/fonts/`.
