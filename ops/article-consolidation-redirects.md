# Permanent redirects for consolidated articles

These redirects are not activated by this repository. The HTML fallback pages
use immediate meta refresh and canonical tags, and return HTTP 200 on GitHub Pages.

| Exact source path | Static target URL | Status |
| --- | --- | --- |
| `/check-insurance-policies.html` | `https://vainzof.co.il/insurance-double-coverage.html` | 301 |
| `/travel-insurance-check-before-flight.html` | `https://vainzof.co.il/travel-insurance-abroad.html` | 301 |
| `/tsunami-in-japan-insurance-guide.html` | `https://vainzof.co.il/travel-insurance-abroad.html` | 301 |

If the domain's traffic is proxied through Cloudflare, create three Single
Redirect rules using exact host `vainzof.co.il` and exact path matches above.
Use the static target URL, status 301, and preserve the query string. Do not
replace an existing ruleset or change DNS merely to activate these rules.
The repository's Cloudflare Web Analytics integration does not establish that
the domain is proxied or that its token can edit redirect rules.

Reference: https://developers.cloudflare.com/rules/url-forwarding/single-redirects/create-dashboard/
Settings: https://developers.cloudflare.com/rules/url-forwarding/single-redirects/settings/

Before activation, publish and verify the target guides. After activation,
request each old HTTPS URL without following redirects and verify status 301
and the exact Location header. Then follow redirects and verify the target
returns 200 in one hop. Also test a query string and confirm it is preserved.
Keep the fallback files for bookmarks and environments where edge rules are not active.
