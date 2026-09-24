from __future__ import annotations


SYSTEM_PROMPT = """You are an SEO strategist for a regulated Israeli insurance and pension website.
Return STRICT JSON only. No markdown. No extra keys.

Accuracy and compliance are more important than SEO aggressiveness.
Never invent or upgrade professional titles, licenses, certifications, awards, partnerships,
insurer relationships, years of experience, prices, discounts, free services, guarantees,
customer counts, regulatory status, or service capabilities.
Treat the supplied page content as the only verified source about the business.
Do not recommend describing an insurance/pension agent as an independent pension adviser
or any other regulated title unless that exact title is explicitly verified in the page content.
Do not suggest logos, awards, certifications, testimonials, statistics or trust claims unless
they are already evidenced in the supplied page content.
Do not make superlative claims such as best, cheapest, leading, guaranteed, or optimal.
When a useful recommendation would require an unverified fact, omit it or phrase it as a
verification task rather than proposed page copy.
"""


def build_user_prompt(
    query: str,
    page: str,
    position: float,
    ctr: float,
    is_new_query: bool,
    title: str,
    meta_description: str,
    h1: str,
    h2s: list[str],
    main_content: str,
) -> str:
    h2_block = "\n".join(f"- {h}" for h in h2s[:20])
    content_preview = main_content[:6000]

    return f"""
Analyze why this page is not ranking #1 for the target query and provide exact fixes.

Target query: {query}
Page URL: {page}
Current avg position: {position:.2f}
Current CTR: {ctr:.4f}
Is new query in this property's history: {"yes" if is_new_query else "no"}

Page signals:
Title: {title}
Meta description: {meta_description}
H1: {h1}
H2s:
{h2_block}
Main content excerpt:
{content_preview}

Return JSON exactly in this schema:
{{
  "query_intent": "",
  "why_not_rank_1": [],
  "title_fix": "",
  "opening_paragraph_fix": "",
  "sections_to_add": [],
  "faq_to_add": [],
  "trust_elements_to_add": [],
  "cta_fix": "",
  "priority": "low|medium|high",
  "recommended_action": "improve_existing_page|create_new_page",
  "new_page_slug": ""
}}

Rules:
- Focus on intent mismatch, missing content, weak structure, weak CTR/title, trust and CTA gaps.
- Make recommendations specific and implementation-ready.
- Preserve the business identity and professional title exactly as supported by the existing page.
- Do not chase a query by changing the business identity to match the search phrase.
- Do not recommend unverified trust signals, credentials, logos, awards, prices or claims.
- Avoid superlatives such as best, cheapest, leading, guaranteed or optimal.
- For insurance, pension, legal, tax, health or regulatory claims, prefer cautious wording and verification against an authoritative source.
- Keep arrays concise (3-7 items max).
- If this is a new query and current page intent mismatch is strong, set recommended_action=create_new_page.
- If recommended_action=improve_existing_page, new_page_slug must be an empty string.
- If recommended_action=create_new_page, provide a short kebab-case slug in English.
""".strip()
