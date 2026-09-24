#!/usr/bin/env python3
import json, re, urllib.parse, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET

TOPICS = {
 "mortgage": ["ביטוח משכנתא","משכנתא ביטוח חיים","מחזור משכנתא","אישור עקרוני משכנתא"],
 "pension": ["פנסיה ישראל","קרן פנסיה","דמי ניהול פנסיה","פרישה פנסיה"],
 "insurance": ["ביטוח חיים ישראל","ביטוח בריאות ישראל","סוכן ביטוח","תביעת ביטוח"]
}
UA={"User-Agent":"Mozilla/5.0 GrowthAgent/1.0"}
def fetch(url):
    req=urllib.request.Request(url,headers=UA)
    with urllib.request.urlopen(req,timeout=20) as r:return r.read()
def clean(s): return re.sub(r"\s+"," ",re.sub("<[^>]+>"," ",s or "")).strip()
def score(title, desc, published):
    text=(title+" "+desc).lower(); s=45
    if any(x in text for x in ["משכנת","פנס","ביטוח"]): s+=25
    if any(x in text for x in ["איך","כמה","האם","חדש","שינוי","מחיר","עלות"]): s+=10
    if published: s+=10
    return min(s,95)
def action_for(topic,title):
    if topic=="mortgage": return "בדוק את המקור. אם יש שאלה או דיון פעיל, הוסף הסבר קצר על מה כדאי לבדוק בביטוח המשכנתא בלי למכור."
    if topic=="pension": return "בדוק אם יש כאן שאלה שאפשר לענות עליה מקצועית. תן נקודה אחת שימושית והפנה לעמוד באתר רק אם זה באמת עוזר."
    return "בדוק את המקור וחפש שאלה קונקרטית שאפשר לענות עליה בגובה העיניים."
def discover():
    out=[]; seen=set()
    for topic,queries in TOPICS.items():
      for q in queries:
        url="https://news.google.com/rss/search?q="+urllib.parse.quote(q+" when:7d")+"&hl=he&gl=IL&ceid=IL:he"
        try: root=ET.fromstring(fetch(url))
        except Exception: continue
        for item in root.findall(".//item")[:5]:
          title=clean(item.findtext("title")); link=clean(item.findtext("link")); desc=clean(item.findtext("description")); pub=clean(item.findtext("pubDate"))
          key=title.lower()
          if not title or key in seen: continue
          seen.add(key); sc=score(title,desc,pub)
          out.append({"id":"auto-"+str(len(out)+1),"topic":topic,"title":title,"url":link,"action":action_for(topic,title),"reply":"","score":sc,"minutes":4,"why":"מקור ציבורי מהימים האחרונים + התאמה לנושא של יובל","published":pub,"discoveredAt":datetime.now(timezone.utc).isoformat()})
    out.sort(key=lambda x:x["score"],reverse=True)
    return out[:20]
Path("growth").mkdir(exist_ok=True)
Path("growth/opportunities.json").write_text(json.dumps(discover(),ensure_ascii=False,indent=2),encoding="utf-8")
