# SEO Automation - איך זה עובד

הקובץ `scripts/seo_audit.py` הוא **כלי בקרה** (Audit), לא כלי תיקון אוטומטי.

## מה הכלי עושה?

בכל הרצה הוא סורק את כל קבצי `*.html` בתיקיית השורש ובודק:
- `<title>`
- `meta description`
- `link rel="canonical"`
- `meta property="og:image"`
- `script type="application/ld+json"`
- קיום `h1` יחיד
- ספירת `<loc>` ב-`sitemap.xml`

בנוסף הוא מייצר:
- דו"ח Markdown (ברירת מחדל: `seo-scan-report.md`)
- אופציונלית: דו"ח JSON

## התזמון שביקשת: כל יום ב־05:00 + מייל לשתי כתובות

הוגדר קובץ cron מוכן בנתיב `ops/seo-audit.cron` עם:
- תזמון יומי ב־`05:00` **לפי שעון ישראל** (`Asia/Jerusalem`)
- שליחת מייל ל:
  - `reginazaidler@gmail.com`
  - `vainzofyuval@yahoo.com`

שורת ה-cron:

```bash
CRON_TZ=Asia/Jerusalem
0 5 * * * cd /workspace/vainzof && /usr/bin/python3 scripts/seo_audit.py --output-md seo-scan-report.md --output-json seo-scan-report.json --send-email --email-to reginazaidler@gmail.com vainzofyuval@yahoo.com --smtp-host SMTP_HOST --smtp-port 587 --smtp-user SMTP_USER --smtp-password SMTP_PASSWORD --smtp-from SMTP_FROM >> /workspace/vainzof/seo-audit.log 2>&1
```

## איך המייל נשלח?

הסקריפט תומך SMTP מובנה דרך הפרמטרים:
- `--send-email`
- `--email-to`
- `--smtp-host`
- `--smtp-port`
- `--smtp-user`
- `--smtp-password`
- `--smtp-from`

בלי ערכי SMTP אמיתיים, שליחת המייל לא תוכל לפעול.

## האם הוא יתקן לבד?

לא. בכוונה.

הכלי מוגדר כ־**audit-only** כדי לא לשנות תוכן/מטא-דאטה בלי בקרה אנושית.

## פקודות שימוש

הרצה בסיסית:

```bash
python scripts/seo_audit.py
```

הרצה עם JSON:

```bash
python scripts/seo_audit.py --output-json seo-scan-report.json
```

הרצה עם מייל (עם פרטי SMTP אמיתיים):

```bash
python scripts/seo_audit.py --send-email --email-to reginazaidler@gmail.com vainzofyuval@yahoo.com --smtp-host smtp.example.com --smtp-user user@example.com --smtp-password 'secret' --smtp-from user@example.com
```

כישלון אוטומטי אם נמצאו בעיות (ל-CI):

```bash
python scripts/seo_audit.py --fail-on-issues
```
