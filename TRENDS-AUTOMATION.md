# Insurance Trends Automation (Free)

המסמך מסביר איך להריץ סוכן חינמי שבודק כל כמה שעות טרנדים מגוגל טרנדס, מזהה שינויים בתחום הביטוח ומייצר רעיונות לכתבות.

## מה נוסף בריפו

- סקריפט: `scripts/insurance_trends_agent.py`
- קובץ cron לדוגמה: `ops/insurance-trends.cron`
- פלטים:
  - `reports/insurance-trends-report.md`
  - `reports/insurance-trends-report.json`
  - `data/trends-agent/snapshot_*.json`

## איך זה עובד

בכל ריצה הסקריפט:
1. מושך Google Trends RSS לפי מדינה (`--geo`, ברירת מחדל IL).
2. מסנן טרנדים לפי מילות מפתח ביטוחיות (עברית + אנגלית).
3. משווה לריצה קודמת (חלון `--lookback-hours`).
4. מזהה מה חדש/מה נעלם/מה נשאר.
5. מייצר רעיונות לכתבות + CTA.
6. שומר דוח Markdown + JSON + snapshot היסטורי.

## הרצה מקומית

```bash
python3 scripts/insurance_trends_agent.py --geo IL --lookback-hours 6
```

## תזמון (כל 4 שעות)

יש דוגמה מוכנה ב-`ops/insurance-trends.cron`.

```bash
CRON_TZ=Asia/Jerusalem
0 */4 * * * cd /workspace/reginazaidler.github.io && /usr/bin/python3 scripts/insurance_trends_agent.py --geo IL --lookback-hours 6 >> /workspace/reginazaidler.github.io/insurance-trends.log 2>&1
```

## עלות

הפתרון כולו חינמי:
- מקור נתונים: Google Trends RSS.
- ללא OpenAI / ללא API בתשלום.
- רץ על Cron מקומי/שרת.

## הערות חשובות

- ל-Google Trends אין API רשמי חינמי מלא, ולכן RSS הוא מקור "best effort".
- מומלץ לעדכן את רשימת מילות המפתח בסקריפט בהתאם לתוכן האתר.
- בריצה ראשונה אין השוואה מלאה כי אין snapshot קודם.


## בלי מחשב מקומי (GitHub בלבד)

אם הקוד יושב רק ב-GitHub, אפשר להריץ הכל דרך GitHub Actions:

- Workflow: `.github/workflows/insurance-trends-agent.yml`
- הרצה ידנית: לשונית **Actions** → **Run Insurance Trends Agent** → **Run workflow**
- אפשר לבחור שם `geo` ו-`lookback_hours` לפני ההרצה הידנית
- הרצה אוטומטית: כל 4 שעות (לפי UTC)
- תוצאות: קובץ Artifact בשם `insurance-trends-agent-reports` שמכיל:
  - `reports/insurance-trends-report.md`
  - `reports/insurance-trends-report.json`
  - `data/trends-agent/snapshot_*.json`

> שים לב: ב-GitHub Actions כל ריצה היא סביבה חדשה, לכן השוואה היסטורית מלאה תלויה בקבצי snapshot שמורידים מה-Artifacts של ריצות קודמות.
> אם אין טרנדים ביטוחיים ישירים בריצה מסוימת, הדוח יכלול גם **רעיונות גיבוי** על בסיס הטרנדים הכלליים החמים בזווית ביטוחית.
