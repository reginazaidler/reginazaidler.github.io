#!/usr/bin/env python3
"""
generate_article.py
───────────────────
Reads the latest insurance-trends JSON report, asks Claude to pick the
best opportunity and write a full SEO article, then outputs a styled
HTML file that matches vainzof.co.il.

Usage:
    python3 scripts/generate_article.py \
        --json-path reports/insurance-trends-report.json \
        --output-dir .
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import textwrap
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-6"

GA_ID = "G-EM8SYH542C"
FORMSPREE_ID = "mdawkwwn"
WHATSAPP_NUMBER = "972524520222"

SITE_CONTEXT = """
האתר הוא vainzof.co.il של יובל ויינזוף - יועץ ביטוח ופנסיה עם 18 שנות ניסיון.
שירות מרכזי: בדיקת תיק ביטוח ופנסיה - זיהוי כפל ביטוחים, עלויות מיותרות, חוסרים.
קהל יעד: משפחות ישראליות בגיל 30-55 שמשלמות על ביטוחים ופנסיה אבל לא בדקו לאחרונה.
טון: מקצועי אבל נגיש, ישיר, מעשי. לא מכירתי.
קול כתיבה: הקורא צריך להרגיש שיובל מסביר לו את הנושא בשיחה אישית, מתוך ניסיון בעבודה עם לקוחות.
כתבות קיימות: דמי ניהול פנסיה, כפל ביטוחים, ביטוח חיים למשכנתא, ביטוח סיעודי,
               בדיקת תיק ביטוח, ביטוח בריאות פרטי, קרן השתלמות.
""".strip()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate SEO article from trends report")
    p.add_argument("--json-path", default="reports/insurance-trends-report.json")
    p.add_argument("--output-dir", default=".")
    p.add_argument("--max-trends", type=int, default=15,
                   help="How many trends to send Claude for evaluation")
    p.add_argument("--dry-run", action="store_true",
                   help="Print generated content without writing files")
    return p.parse_args()


def api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        sys.exit("ERROR: ANTHROPIC_API_KEY environment variable is not set.")
    return key


def call_claude(prompt: str, system: str, max_tokens: int = 4096, retries: int = 5) -> str:
    payload = json.dumps({
        "model": MODEL,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()

    for attempt in range(retries):
        req = urllib.request.Request(
            ANTHROPIC_API_URL,
            data=payload,
            headers={
                "x-api-key": api_key(),
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
            return "".join(block.get("text", "") for block in data.get("content", []))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            print(f"[call_claude] HTTP {e.code} error (attempt {attempt + 1}/{retries}): {body}", flush=True)
            if e.code in (529, 503, 500) and attempt < retries - 1:
                wait = 30 * (2 ** attempt)
                print(f"[call_claude] Retrying in {wait}s...", flush=True)
                time.sleep(wait)
            else:
                raise


def load_report(json_path: str) -> dict:
    path = Path(json_path)
    if not path.exists():
        sys.exit(f"ERROR: report not found at {json_path}")
    return json.loads(path.read_text(encoding="utf-8"))


def pick_best_trend(report: dict, max_trends: int) -> dict:
    """Ask Claude to evaluate all trends and pick + plan the best article."""

    # Collect candidates: new direct + fallback ideas
    candidates = []
    for t in report.get("changes", {}).get("new", [])[:max_trends]:
        candidates.append({"title": t["title"], "traffic": t.get("traffic", ""), "type": "direct"})
    for idea in report.get("article_ideas", [])[:max_trends]:
        candidates.append({"title": idea["topic"], "headline": idea.get("headline", ""), "type": "idea"})
    for idea in report.get("fallback_article_ideas", [])[:max_trends]:
        candidates.append({"title": idea["topic"], "headline": idea.get("headline", ""), "type": "fallback"})

    if not candidates:
        sys.exit("No trend candidates found in report.")

    print(f"[pick_best_trend] {len(candidates)} candidates:", flush=True)
    for c in candidates:
        print(f"  • [{c['type']}] {c['title']}", flush=True)

    prompt = f"""להלן רשימת טרנדים חמים בגוגל ישראל כרגע:

{json.dumps(candidates, ensure_ascii=False, indent=2)}

הקשר האתר:
{SITE_CONTEXT}

## כללי בחירה - חשוב מאוד

בחר **רק** טרנד שעומד בכל התנאים הבאים:
1. **אירוע ספציפי ואמיתי** - שם מקום, אירוע, חברה, אדם, תאריך - לא נושא גנרי.
2. **קשר ישיר לביטוח או פנסיה** - הקורא צריך להבין מיד למה זה רלוונטי אליו.
3. **כותרת שמחברת בין האירוע לביטוח** - לפי הדוגמה: "האש ביוון 2026 - למה ביטוח דירה חשוב יותר מאי פעם".

## כותרות לדחות
- "מה זה ביטוח - כל מה שצריך לדעת"
- "מדריך לביטוח בריאות"
- כל כותרת גנרית שיכולה להתאים לכל שנה

## אם אין טרנד מתאים
החזר `"chosen_trend": null` - עדיף לא לכתוב כלום מאשר לכתוב כתבה חלשה.

המשימה שלך:
1. בחר את הטרנד הכי ספציפי ורלוונטי לביטוח/פנסיה. אם אין כזה - החזר null.
2. הסבר בקצרה למה בחרת אותו (2-3 משפטים).
3. תכנן את הכתבה: כותרת H1, מילת מפתח ראשית, slug ב-URL (אנגלית), meta description.

ענה ב-JSON בלבד (ללא backticks), בפורמט:
{{
  "chosen_trend": "..." או null,
  "reason": "...",
  "h1": "...",
  "keyword": "...",
  "slug": "kebab-case-english-slug",
  "meta_description": "עד 155 תווים",
  "page_class": "kebab-case-page-class"
}}"""

    raw = call_claude(prompt, system="אתה מומחה SEO לאתרים בעברית. ענה אך ורק ב-JSON תקין.")
    raw = raw.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    result = json.loads(raw)
    if not result.get("chosen_trend"):
        sys.exit("[pick_best_trend] No suitable trend found - skipping article generation.")
    return result


# Internal links map for articles
INTERNAL_LINKS = {
    "pension-fees-guide": ("pension-fees-guide.html", "כמה דמי ניהול פנסיה זה גבוה"),
    "insurance-double-coverage": ("insurance-double-coverage.html", "כפל ביטוחים - זיהוי ובדיקה"),
    "financial-checklist-family": ("financial-checklist-family.html", "צ׳קליסט פיננסי שנתי למשפחה"),
    "insurance-types": ("insurance-types.html", "סוגי ביטוחים בישראל"),
    "check-insurance-policies": ("check-insurance-policies.html", "איך בודקים תיק ביטוח"),
    "calculator": ("calculator.html", "מחשבון חיסכון"),
    "articles": ("articles.html", "כל המאמרים על ביטוח ופנסיה"),
    "pension-guide": ("pension-guide.html", "מדריך פנסיה"),
    "life-insurance": ("life-insurance.html", "ביטוח חיים"),
    "health-insurance": ("health-insurance.html", "ביטוח בריאות"),
    "travel-insurance": ("travel-insurance.html", "ביטוח נסיעות לחו׳׳ל"),
    "mortgage-insurance": ("mortgage-insurance.html", "ביטוח משכנתא"),
    "loss-of-income": ("loss-of-income.html", "ביטוח אובדן כושר עבודה"),
}


def write_article(meta: dict) -> dict:
    """Ask Claude to write the full article body (sections as JSON)."""

    links_list = "\n".join(
        f'  - "{slug}": href="{href}" טקסט="{label}"'
        for slug, (href, label) in INTERNAL_LINKS.items()
    )

    prompt = f"""אתה כותב כתבת SEO מלאה לאתר vainzof.co.il של יובל ויינזוף, יועץ ביטוח ופנסיה.

נושא: {meta['chosen_trend']}
כותרת H1: {meta['h1']}
מילת מפתח: {meta['keyword']}

כתוב כתבה מקצועית ומועילה בעברית.
הכתבה צריכה:
- להיות ~500 מילים (קצר וממוקד)
- לפתוח עם פסקת intro קצרה (2-3 משפטים)
- לכלול 3-4 סעיפי H2, כל סעיף עד 3 פסקאות קצרות
- לסיים עם FAQ (2-3 שאלות ותשובות)
- כל פסקה עד 2 משפטים, כל bullet עד 10 מילים

חוקים חשובים:
1. אל תזכיר שהנושא הוא "טרנד" או "חיפוש נפוץ היום" - כתוב כמאמר מידע רגיל.
2. לינקים פנימיים: השתמש רק בלינקים מהרשימה הבאה, כתוב את ה-href המדויק:
{links_list}
3. הוסף לכל היותר 2 לינקים פנימיים רלוונטיים בגוף הכתבה - לא יותר.
4. בסוף הכתבה (סעיף "קריאה נוספת") הוסף עד 3 לינקים רלוונטיים מהרשימה.
5. אל תוסיף יותר מ-1 קריאה לפעולה (CTA) בכל הכתבה - בסוף בלבד, בסגנון עדין.
6. כתוב בעברית ישראלית טבעית, עם קצב מגוון. מותר להשתמש מדי פעם בגוף ראשון כשניסיון מקצועי מוסיף הקשר.
7. אל תמציא מקרה לקוח, מספר, ציטוט או חוויה. אם חסר פרט מהשטח, כתוב ניסוח כללי שאפשר לאמת בעריכה.
8. הימנע מניסוחים תבניתיים כמו "בעידן של היום", "חשוב לציין", "לסיכום", "כל מה שצריך לדעת" ו"המדריך המקיף".
9. אל תחזור על אותה מסקנה בפתיחה, בגוף ובסיכום. העדף דוגמאות קונקרטיות ושאלות שקורא אמיתי היה שואל.
10. לפני החזרת ה-JSON, קרא את הטקסט כעורך: הסר סופרלטיבים, רצפים סימטריים מדי ומילות מילוי.

חשוב: ב-JSON אסור HTML ואסור מרכאות כפולות בתוך ערכים.
כתוב טקסט רגיל בלבד.

ענה ב-JSON בלבד (ללא backticks):
{{
  "intro": "פסקת פתיחה - טקסט רגיל",
  "sections": [
    {{
      "id": "section-slug-english",
      "h2": "כותרת סעיף",
      "paragraphs": ["פסקה ראשונה", "פסקה שנייה"],
      "bullets": ["נקודה א", "נקודה ב"]
    }}
  ],
  "faq": [
    {{"q": "שאלה", "a": "תשובה"}}
  ],
  "summary": "משפט סיכום אחד"
}}"""

    raw = call_claude(
        prompt,
        system="אתה עורך תוכן SEO מקצועי לאתרים בעברית. כתוב תוכן מעמיק ומועיל. ענה אך ורק ב-JSON תקין ללא HTML.",
        max_tokens=8000,
    )
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0]
    raw = raw.strip()
    try:
        return json.loads(raw)
    except Exception:
        import re as _re
        m = _re.search(r'\{.*\}', raw, _re.DOTALL)
        if m:
            return json.loads(m.group())
        raise


# ── HTML helpers ──────────────────────────────────────────────────────────────

def toc_items(sections: list[dict]) -> str:
    return "\n".join(
        f'          <li><a href="#{s["id"]}">{s["h2"]}</a></li>'
        for s in sections
    ) + "\n          <li><a href=\"#faq\">שאלות נפוצות</a></li>"


def linkify(text: str) -> str:
    """Replace bare hrefs like pension-fees-guide.html with proper <a> tags."""
    import re
    for slug, (href, label) in INTERNAL_LINKS.items():
        # Replace bare filename references
        text = text.replace(href, f'<a href="{href}">{label}</a>')
    return text


def sections_html(sections: list[dict]) -> str:
    parts = []
    for s in sections:
        paras = "".join(f"<p>{linkify(p)}</p>\n        " for p in s.get("paragraphs", []))
        bullets = ""
        if s.get("bullets"):
            items = "".join(f"<li>{linkify(b)}</li>" for b in s["bullets"])
            bullets = f"<ul>{items}</ul>"
        # Handle "links" field if Claude returns it
        links_html = ""
        if s.get("links"):
            link_items = ""
            for lnk in s["links"]:
                href = lnk.get("href", "#")
                label = lnk.get("label", href)
                link_items += f'<li><a href="{href}">{label}</a></li>'
            links_html = f'<ul>{link_items}</ul>'
        parts.append(f"""
      <section id="{s['id']}" class="pension-section">
        <h2>{s['h2']}</h2>
        {paras}{bullets}{links_html}
      </section>""")
    return "\n".join(parts)


def faq_html(faq: list[dict]) -> str:
    items = []
    for item in faq:
        items.append(f"        <h3>{item['q']}</h3>\n        <p>{item['a']}</p>")
    return "\n".join(items)


def faq_schema(faq_items: list[dict]) -> str:
    entities = []
    for item in faq_items:
        q = item.get('name') or item.get('q', '')
        a = item.get('text') or item.get('a', '')
        entities.append(
            f"""    {{
      "@type": "Question",
      "name": {json.dumps(q, ensure_ascii=False)},
      "acceptedAnswer": {{
        "@type": "Answer",
        "text": {json.dumps(a, ensure_ascii=False)}
      }}
    }}"""
        )
    return ",\n".join(entities)


def build_html(meta: dict, article: dict, now_str: str) -> str:
    slug = meta["slug"]
    h1 = meta["h1"]
    keyword = meta["keyword"]
    meta_desc = meta["meta_description"]
    page_class = meta.get("page_class", slug.replace("-", "_") + "_page")
    canonical_url = f"https://vainzof.co.il/{slug}.html"
    og_title = h1

    sections = article["sections"]
    intro = article["intro"]
    summary = article.get("summary", "")

    return f"""<!doctype html>
<html lang="he" dir="rtl">
<head>
<script async src="https://www.googletagmanager.com/gtag/js?id={GA_ID}"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){{dataLayer.push(arguments);}}
gtag('js', new Date());
gtag('config', '{GA_ID}');
</script>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{h1}</title>
<meta name="description" content="{meta_desc}">
<link rel="canonical" href="{canonical_url}">
<meta property="og:type" content="article">
<meta property="og:title" content="{og_title}">
<meta property="og:description" content="{meta_desc}">
<meta property="og:url" content="{canonical_url}">
<meta property="og:image" content="https://vainzof.co.il/assets/yuval.webp">
<meta property="og:image:alt" content="יובל ויינזוף - סוכן ביטוח ופנסיה">
<meta name="twitter:image" content="https://vainzof.co.il/assets/yuval.webp">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{og_title}">
<meta name="twitter:description" content="{meta_desc}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Assistant:wght@400;700;800&display=swap">
<link rel="icon" type="image/png" href="favicon.png">
<link rel="apple-touch-icon" href="favicon.png">
<link rel="preload" as="image" href="assets/yuval.webp">
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": {json.dumps(h1, ensure_ascii=False)},
  "description": {json.dumps(meta_desc, ensure_ascii=False)},
  "author": {{
    "@type": "Person",
    "name": "יובל ויינזוף"
  }},
  "publisher": {{
    "@type": "Organization",
    "name": "יובל ויינזוף",
    "logo": {{
      "@type": "ImageObject",
      "url": "https://vainzof.co.il/assets/logo.png"
    }}
  }},
  "mainEntityOfPage": "{canonical_url}",
  "datePublished": "{now_str}",
  "inLanguage": "he-IL"
}}
</script>
<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
{faq_schema(article.get('faq_schema', []))}
  ]
}}
</script>
<link rel="stylesheet" href="style.css">
<style>
body.{page_class} {{
  background: linear-gradient(180deg, #f8fafc 0%, #edf4ff 100%);
  font-family: "Assistant", sans-serif;
}}
body.{page_class} main {{ padding-top: 2.5rem; padding-bottom: 2.5rem; }}
.pension-guide-wrap {{ max-width: 76rem; margin: 0 auto; padding: 0 1rem; }}
.pension-grid {{ display: grid; gap: 1.25rem; }}
.pension-hero, .pension-section, .pension-cta-inline,
.pension-lead-box, .pension-form-section, .pension-links-box, .pension-toc {{
  background: #fff; border: 1px solid #dbe5f2;
  border-radius: 1.5rem; box-shadow: 0 16px 40px rgba(15,23,42,0.06);
}}
.pension-hero {{
  padding: 1.5rem;
  background: linear-gradient(135deg, var(--navy-deep) 0%, var(--navy-main) 100%);
  border-color: rgba(255,255,255,0.18);
}}
.pension-hero {{ color: rgba(255,255,255,0.92); }}
.pension-hero h1 {{ color: #fff !important; }}
.pension-hero .bg-blue-50 {{ background: rgba(255,255,255,0.1); color: var(--gold-brand); }}
.pension-rich-text p, .pension-rich-text ul, .pension-rich-text ol {{ margin-bottom: 1.15rem; }}
.pension-rich-text p, .pension-rich-text li {{ color: #334155; line-height: 1.95; }}
.pension-rich-text h2 {{ font-size: clamp(1.65rem,2vw,2.2rem); color: #061a40; font-weight: 800; margin-bottom: 1rem; }}
.pension-rich-text h3 {{ font-size: clamp(1.2rem,1.4vw,1.45rem); color: #0f172a; font-weight: 800; margin: 1.4rem 0 0.7rem; }}
/* Override dark text from pension-rich-text inside dark hero/cta sections */
.pension-hero p, .pension-hero li {{ color: rgba(255,255,255,0.92) !important; }}
.pension-hero a:not([class*="btn"]) {{ color: rgba(255,255,255,0.8) !important; }}
.pension-section, .pension-form-section {{ padding: clamp(1.3rem,3vw,2.2rem); scroll-margin-top: 7rem; }}
.pension-toc, .pension-lead-box, .pension-links-box {{ padding: 1.35rem; }}
.pension-toc ul, .pension-rich-text ul {{ list-style: disc; padding-right: 1.25rem; }}
.pension-cta-inline {{ padding: 1.35rem; background: linear-gradient(135deg,#0f172a 0%,#17356a 100%); color: #fff; }}
.pension-cta-inline p, .pension-cta-inline h2 {{ color: #fff; }}
.pension-btn-row {{ display: flex; flex-wrap: wrap; gap: 0.75rem; }}
.pension-btn, .pension-btn-secondary {{
  display: inline-flex; justify-content: center; align-items: center;
  min-height: 50px; padding: 12px 24px; border-radius: 12px;
  font-weight: 800; text-decoration: none; border: 1px solid transparent;
  transition: transform .2s ease, box-shadow .2s ease;
}}
.pension-btn {{ background: var(--gold-brand); color: #ffffff; }}
.pension-btn--whatsapp {{
  background: linear-gradient(135deg,#19a866 0%,#128c7e 100%); color: #fff;
  border-color: #16a34a; box-shadow: 0 10px 22px rgba(22,163,74,0.28);
}}
.pension-btn:hover, .pension-btn--whatsapp:hover {{ transform: translateY(-2px); }}
.pension-links-box a, .pension-rich-text a:not(.pension-btn),
.pension-toc a {{ color: #1d4ed8; font-weight: 700; text-decoration: underline; text-underline-offset:.2rem; }}
.pension-form-grid {{ display: grid; gap: 0.9rem; }}
.pension-form-grid .full-span {{ grid-column: 1/-1; }}
.pension-form-section input, .pension-form-section textarea {{
  width: 100%; padding: 0.95rem 1rem; background: #f8fafc;
  border: 1px solid #cbd5e1; border-radius: 1rem; color: #0f172a;
  font-weight: 700; text-align: right;
}}
.pension-form-section textarea {{ min-height: 130px; resize: vertical; }}
.pension-success {{ display:none; color:#166534; font-weight:700; }}
.pension-error {{ display:none; color:#b91c1c; font-weight:700; }}
@media (min-width: 768px) {{
  body.{page_class} main {{ padding-top: 3.5rem; padding-bottom: 3.5rem; }}
  .pension-form-grid {{ grid-template-columns: repeat(2,minmax(0,1fr)); }}
}}
@media (max-width: 1023px) {{
  #mobileMenu.lg\\:hidden {{ display: none; }}
  #mobileMenu:not(.hidden) {{ display: block; }}
}}
@media (min-width: 1024px) {{
  .pension-grid {{ grid-template-columns: minmax(0,2.1fr) minmax(280px,0.9fr); align-items: start; }}
  .pension-sidebar {{ position: sticky; top: 7rem; }}
}}
@media (max-width: 767px) {{
  .pension-btn, .pension-btn-secondary {{ width: 100%; }}
}}
</style>
</head>
<body class="{page_class}">
<a href="#main" class="sr-focusable">דלג לתוכן המרכזי</a>
<div id="top-anchor" class="site-topbar">
  <div class="container-clean site-topbar__inner">{h1}</div>
</div>
<header class="site-header">
  <div class="container-clean site-header__inner">
    <a href="index.html" class="site-brand" aria-label="חזרה לדף הבית">
      <img src="assets/logo.png" alt="יובל ויינזוף - לוגו" class="site-logo">
    </a>
    <nav class="site-nav" aria-label="ניווט ראשי">
      <a href="index.html" class="nav-link">דף הבית</a>
      <a href="about.html" class="nav-link">קצת עלי</a>
      <a href="insurance-types.html" class="nav-link">סוגי ביטוחים</a>
      <a href="faq.html" class="nav-link">שאלות ותשובות</a>
      <a href="articles.html" class="nav-link nav-link-active">מאמרים</a>
    </nav>
    <button id="menuBtn" class="lg:hidden p-2 text-blue-900" aria-label="פתח תפריט" aria-expanded="false" aria-controls="mobileMenu">
      <svg class="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16m-7 6h7"/>
      </svg>
    </button>
  </div>
</header>
<div id="mobileMenu" class="hidden lg:hidden bg-white border-b border-slate-100 py-4 px-6 space-y-4 shadow-xl absolute w-full top-full right-0 z-50">
  <a href="index.html" class="block font-bold text-slate-600 border-b pb-2">דף הבית</a>
  <a href="about.html" class="block font-bold text-slate-600 border-b pb-2">קצת עלי</a>
  <a href="insurance-types.html" class="block font-bold text-slate-600 border-b pb-2">סוגי ביטוחים</a>
  <a href="faq.html" class="block font-bold text-slate-600 border-b pb-2">שאלות ותשובות</a>
  <a href="articles.html" class="block font-bold text-blue-900 border-b pb-2">מאמרים</a>
</div>

<main id="main" class="py-10 md:py-14">
  <div class="pension-guide-wrap pension-grid">
    <article class="space-y-6 pension-rich-text">

      <section class="pension-hero">
        <a href="articles.html" class="font-bold" style="color:rgba(255,255,255,0.8)">← חזרה לכל המאמרים</a>
        <p class="mt-6 inline-flex items-center gap-2 rounded-full bg-blue-50 px-4 py-2 text-sm font-extrabold text-blue-900">מדריך עדכני - {now_str[:7]}</p>
        <h1 class="text-4xl font-black mt-5 mb-5" style="color:#fff">{h1}</h1>
        {intro}
      </section>

{sections_html(sections)}

      <section class="pension-section">
        <h2>סיכום</h2>
        <p>{summary}</p>
      </section>

      <section id="faq" class="pension-section">
        <h2>שאלות נפוצות</h2>
{faq_html(article.get('faq', []))}
      </section>

      <section class="pension-links-box">
        <h2 class="text-2xl font-black text-blue-950 mb-4">קריאה נוספת</h2>
        <ul>
          <li><a href="insurance-types.html">סוגי ביטוחים בישראל</a></li>
          <li><a href="pension-fees-guide.html">כמה דמי ניהול פנסיה זה גבוה</a></li>
          <li><a href="insurance-double-coverage.html">כפל ביטוחים: זיהוי ובדיקה</a></li>
          <li><a href="financial-checklist-family.html">צ׳קליסט פיננסי שנתי למשפחה</a></li>
          <li><a href="articles.html">כל המאמרים</a></li>
        </ul>
      </section>

      <section id="lead-form" class="pension-form-section">
        <h2 class="text-3xl font-black text-blue-950 mb-3">השאירו פרטים לבדיקה</h2>
        <p class="text-slate-700 mb-6">בדיקה ראשונית ללא עלות - נבדוק מה קיים בתיק ומה אפשר לשפר.</p>
        <form id="leadForm" class="space-y-4">
          <div class="pension-form-grid">
            <div>
              <label for="full_name" class="block mb-2 font-bold text-slate-700">שם מלא</label>
              <input id="full_name" name="user_name" type="text" required placeholder="איך קוראים לך?">
            </div>
            <div>
              <label for="phone" class="block mb-2 font-bold text-slate-700">טלפון</label>
              <input id="phone" name="user_phone" type="tel" inputmode="tel" required placeholder="מספר טלפון">
            </div>
            <div>
              <label for="email" class="block mb-2 font-bold text-slate-700">אימייל</label>
              <input id="email" name="user_email" type="email" placeholder="אימייל (לא חובה)">
            </div>
            <div>
              <label for="topic" class="block mb-2 font-bold text-slate-700">נושא</label>
              <input id="topic" name="topic" type="text" value="{keyword}" readonly>
            </div>
            <div class="full-span">
              <label for="message" class="block mb-2 font-bold text-slate-700">מה תרצו לבדוק?</label>
              <textarea id="message" name="message" placeholder="תאר בקצרה מה אתה מחפש לבדוק..."></textarea>
            </div>
          </div>
          <div class="pension-btn-row">
            <div id="formSuccess" class="pension-success">הפרטים נשלחו. נחזור אליכם בקרוב.</div>
            <div id="formError" class="pension-error">שגיאה בשליחה. אפשר לנסות שוב או לפנות ב-WhatsApp.</div>
          </div>
          <div class="pension-btn-row">
            <button type="submit" class="pension-btn">שליחת טופס</button>
            <a href="https://wa.me/{WHATSAPP_NUMBER}" target="_blank" rel="noopener noreferrer" class="pension-btn pension-btn--whatsapp">שליחת הודעה ב-WhatsApp</a>
          </div>
        </form>
      </section>

    </article>

    <aside class="pension-sidebar space-y-6">
      <section class="pension-toc">
        <h2 class="text-2xl font-black text-blue-950 mb-4">תוכן עניינים</h2>
        <ul>
{toc_items(sections)}
        </ul>
      </section>
      <section class="pension-lead-box">
        <h2 class="text-2xl font-black text-blue-950 mb-3">יש שאלה?</h2>
        <p class="text-slate-700">יובל ויינזוף - יועץ ביטוח ופנסיה. אפשר לפנות ישירות.</p>
        <div class="pension-btn-row" style="margin-top:1rem">
          <a href="https://wa.me/{WHATSAPP_NUMBER}" target="_blank" rel="noopener noreferrer" class="pension-btn pension-btn--whatsapp">WhatsApp</a>
        </div>
      </section>
    </aside>
  </div>
</main>

<script src="js/site-header.js"></script>
<script src="js/site-footer.js"></script>
<script>
const leadForm = document.getElementById('leadForm');
const formSuccess = document.getElementById('formSuccess');
const formError = document.getElementById('formError');
leadForm?.addEventListener('submit', async (e) => {{
  e.preventDefault();
  formSuccess.style.display = 'none';
  formError.style.display = 'none';
  try {{
    const res = await fetch('https://formspree.io/f/{FORMSPREE_ID}', {{
      method: 'POST',
      body: new FormData(leadForm),
      headers: {{ Accept: 'application/json' }}
    }});
    if (!res.ok) throw new Error();
    leadForm.reset();
    formSuccess.style.display = 'block';
  }} catch {{
    formError.style.display = 'block';
  }}
}});
</script>
<script src="js/whatsapp-float.js"></script>
</body>
</html>"""



# ── Category mapping ─────────────────────────────────────────────────────────

# Map keywords in slug/title → articles.html category anchor
CATEGORY_MAP = [
    (["pension", "פנסיה", "dami", "fees", "retirement", "severance", "salary-rise",
      "beneficiaries", "freelancer", "pension-report"], "cat-pension"),
    (["insurance", "bituach", "health", "life", "travel", "mortgage", "loss-of-income",
      "critical", "sickness", "measles", "birth", "double-coverage", "annual-review",
      "choose-insurance", "update-insurance", "switch-insurance", "essential-family",
      "long-term-care", "private-vs-hmo", "overpaying"], "cat-insurance"),
    (["severance", "pitzuyim", "withdraw", "calculate-severance"], "cat-severance"),
    (["investment-fund", "gml", "provident", "gemol"], "cat-investment-fund"),
    (["checklist", "finance", "savings", "bank", "emergency-fund", "bituach-leumi",
      "sp500", "ta35", "gas", "dollar", "neft", "market"], "cat-finance"),
]


def guess_category(slug: str, h1: str) -> str:
    text = (slug + " " + h1).lower()
    for keywords, cat in CATEGORY_MAP:
        if any(kw in text for kw in keywords):
            return cat
    return "cat-insurance"  # default


def update_sitemap(sitemap_path: Path, slug: str, today: str) -> None:
    content = sitemap_path.read_text(encoding="utf-8")
    url = f"https://vainzof.co.il/{slug}.html"
    if url in content:
        print(f"[sitemap] Already present: {url}")
        return
    new_entry = f"""
  <url>
    <loc>{url}</loc>
    <lastmod>{today}</lastmod>
  </url>"""
    # Insert before closing </urlset>
    content = content.replace("</urlset>", new_entry + "\n\n</urlset>")

    sitemap_path.write_text(content, encoding="utf-8")
    print(f"[sitemap] Added: {url}")


def update_articles_html(articles_path: Path, slug: str, h1: str,
                          meta_desc: str, category: str) -> None:
    content = articles_path.read_text(encoding="utf-8")
    href = f"{slug}.html"
    if href in content:
        print(f"[articles] Already present: {href}")
        return

    card = f"""          <article class="bg-white border border-slate-200 rounded-2xl p-5 article-card">
            <h3 class="text-2xl font-extrabold text-blue-950 mb-3">{h1}</h3>
            <p class="text-slate-700 mb-4">{meta_desc}</p>
            <a href="{href}" class="font-extrabold text-[var(--navy-main)] article-card__link">לקריאה מלאה ←</a>
          </article>"""

    # Find the category accordion and insert the card inside its grid
    anchor = f'id="{category}"'
    cat_idx = content.find(anchor)
    if cat_idx == -1:
        # fallback: insert before </urlset> replacement won't work, use cat-insurance
        anchor = 'id="cat-insurance"'
        cat_idx = content.find(anchor)

    if cat_idx == -1:
        print(f"[articles] Category anchor not found, skipping")
        return

    # Find the first <div class="grid inside this category block
    grid_start = content.find('<div class="grid grid-cols-1 md:grid-cols-3 gap-4', cat_idx)
    if grid_start == -1:
        print(f"[articles] Grid not found in category")
        return

    # Insert the new card right after the opening grid div tag
    grid_tag_end = content.find('>', grid_start) + 1
    content = content[:grid_tag_end] + "\n" + card + "\n" + content[grid_tag_end:]

    # Also update the count in the summary hint
    # Find hint span for this category
    hint_search_start = cat_idx
    hint_idx = content.find('articles-accordion__hint', hint_search_start)
    if hint_idx != -1:
        hint_end = content.find('</span>', hint_idx)
        hint_content = content[hint_idx:hint_end]
        import re
        m = re.search(r'(\d+)', hint_content)
        if m:
            old_count = int(m.group(1))
            content = content[:hint_idx] + hint_content.replace(
                str(old_count), str(old_count + 1), 1) + content[hint_end:]

    articles_path.write_text(content, encoding="utf-8")
    print(f"[articles] Added card to {category}: {h1}")


def update_llms_txt(llms_path: Path, slug: str, h1: str) -> None:
    if not llms_path.exists():
        return
    content = llms_path.read_text(encoding="utf-8")
    url = f"https://vainzof.co.il/{slug}.html"
    if url in content:
        print(f"[llms] Already present: {url}")
        return
    # Append the new article as a named link before the first blank line
    # after the last "- " list item in the guides section
    new_line = f"- {h1}: {url}\n"
    # Find the last "- " line in the file and insert after it
    lines = content.splitlines(keepends=True)
    last_list_idx = -1
    for i, line in enumerate(lines):
        if line.startswith("- "):
            last_list_idx = i
    if last_list_idx != -1:
        lines.insert(last_list_idx + 1, new_line)
        llms_path.write_text("".join(lines), encoding="utf-8")
        print(f"[llms] Added: {url}")
    else:
        # Fallback: append at end
        with llms_path.open("a", encoding="utf-8") as f:
            f.write(new_line)
        print(f"[llms] Appended: {url}")


CSV_HEADERS = ["date", "slug", "title", "keyword", "url", "status", "notes"]


def log_article(csv_path: Path, slug: str, title: str, keyword: str, generated_at: str) -> None:
    """Append a row to the generated-articles CSV tracking log."""
    import csv as _csv
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not csv_path.exists()
    url = f"https://vainzof.co.il/{slug}.html"
    date_str = generated_at[:10]
    with csv_path.open("a", encoding="utf-8", newline="") as f:
        writer = _csv.DictWriter(f, fieldnames=CSV_HEADERS)
        if write_header:
            writer.writeheader()
        writer.writerow({"date": date_str, "slug": slug, "title": title,
                         "keyword": keyword, "url": url, "status": "", "notes": ""})
    print(f"[tracking] Logged to {csv_path}")


def update_all_indexes(slug: str, h1: str, meta_desc: str, today: str) -> None:
    """Update sitemap, articles.html and llms.txt for the new article."""
    category = guess_category(slug, h1)
    print(f"[indexes] Category detected: {category}")

    sitemap = Path("sitemap.xml")
    articles = Path("articles.html")
    llms = Path("llms.txt")

    if sitemap.exists():
        update_sitemap(sitemap, slug, today)
    else:
        print("[sitemap] sitemap.xml not found, skipping")

    # articles.html intentionally skipped - agent articles are indexed via
    # sitemap + llms.txt only, not linked from the site navigation.
    print("[articles] Skipping articles.html (orphan-by-design)")

    if llms.exists():
        update_llms_txt(llms, slug, h1)
    else:
        print("[llms] llms.txt not found, skipping")


def main() -> int:
    args = parse_args()
    report = load_report(args.json_path)
    now = datetime.now(timezone.utc)
    now_str = now.strftime("%Y-%m-%d")

    print("[generate_article] Asking Claude to pick best trend & plan article...")
    meta = pick_best_trend(report, args.max_trends)
    print(f"[generate_article] Chosen: {meta['chosen_trend']}")
    print(f"[generate_article] Reason: {meta['reason']}")
    print(f"[generate_article] Slug: {meta['slug']}")

    print("[generate_article] Writing full article...")
    article = write_article(meta)

    html = build_html(meta, article, now_str)
    filename = f"{meta['slug']}.html"

    if args.dry_run:
        print(f"\n{'='*60}\nDRY RUN - would write: {filename}\n{'='*60}")
        print(html[:2000], "... [truncated]")
        return 0

    output_path = Path(args.output_dir) / filename
    output_path.write_text(html, encoding="utf-8")
    print(f"[generate_article] Written: {output_path}")

    # Save metadata for the workflow to use
    meta_out = Path(args.output_dir) / "reports" / "last-generated-article.json"
    meta_out.parent.mkdir(parents=True, exist_ok=True)
    meta_out.write_text(
        json.dumps({"filename": filename, "slug": meta["slug"], "h1": meta["h1"],
                    "keyword": meta["keyword"], "generated_at": now.isoformat()},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[generate_article] Metadata saved: {meta_out}")

    # Append to generated-articles tracking log
    log_article(
        csv_path=Path(args.output_dir) / "reports" / "generated-articles.csv",
        slug=meta["slug"],
        title=meta["h1"],
        keyword=meta["keyword"],
        generated_at=now.isoformat(),
    )

    # Update sitemap, articles.html, llms.txt
    update_all_indexes(
        slug=meta["slug"],
        h1=meta["h1"],
        meta_desc=meta["meta_description"],
        today=now_str,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
