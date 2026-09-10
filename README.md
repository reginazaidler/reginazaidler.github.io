# vainzof.co.il

Static website source for `vainzof.co.il`.

## Repository contents

- HTML pages at the repository root.
- Shared assets under `assets/`.
- Shared JavaScript under `js/`.
- Technical SEO audit utility: `scripts/seo_audit.py`.
- Optional SEO audit docs: `SEO-AUTOMATION.md`.
- Insurance trends automation docs: `TRENDS-AUTOMATION.md`.

## Removed automation

The previous daily rank report automation (Search Console collection, report email sender, and scheduled workflow) was removed from this repository.

## Deploy

The site is deployed via GitHub Pages using `.github/workflows/deploy-pages.yml`.

## Local checks

Run the local SEO audit script (optional):

```bash
python scripts/seo_audit.py
```

Validate that every page has an HTTPS canonical, the sitemap and robots sitemap
reference contain only the HTTPS origin, and no page uses an insecure absolute
internal link:

```bash
python3 scripts/check_https_seo.py
```

The deployment workflow both enables GitHub Pages' `https_enforced` setting via
the GitHub API and runs this validation before publishing. This setting makes
GitHub Pages perform the HTTP-to-HTTPS redirect at the hosting layer; an HTML
canonical tag is not used as a substitute for that redirect. The live response
can be verified from a network-enabled environment with:

```bash
python3 scripts/check_https_seo.py --check-live-redirect
```


## Insurance Trends agent (free)

Run:

```bash
python3 scripts/insurance_trends_agent.py --geo IL --lookback-hours 6
```

Outputs are written to `reports/insurance-trends-report.md`, `reports/insurance-trends-report.json`, and `data/trends-agent/snapshot_*.json`.


GitHub-only run: use **Actions → Run Insurance Trends Agent** (workflow file: `.github/workflows/insurance-trends-agent.yml`).
In manual GitHub runs you can override `geo` and `lookback_hours`; if no direct insurance trends are found, the report includes fallback insurance-angle ideas based on general hot trends.

## Bitbucket daily dash-normalizer agent

This repo includes a Bitbucket Pipeline agent that replaces **em dashes (`U+2014`)** with a normal hyphen (`-`).

### Files
- Pipeline config: `bitbucket-pipelines.yml` (custom pipeline: `daily-normalize-dashes`)
- Replacement script: `scripts/normalize_dashes.py`

### How to run daily
1. In Bitbucket, open **Pipelines → Schedules → New schedule**.
2. Select pipeline: **`daily-normalize-dashes`**.
3. Select branch: your main branch.
4. Set frequency: **Daily** and pick the preferred time.

When there are replacements, the pipeline commits and pushes automatically.
