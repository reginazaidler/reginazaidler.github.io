# Yuval Audience Finder Chrome extension - prototype

Prototype for testing the audience-discovery hypothesis on Instagram without performing follows, likes, comments, DMs, login automation, or background scraping.

## What it does
When the user is already viewing Instagram in Chrome, the extension collects public profile links currently rendered around the visible page and shows them in a popup. It stores the latest scan locally in Chrome.

It does NOT claim that every collected account is a commenter. Instagram's DOM changes frequently, so V0.1 deliberately reports only what it can verify: profile links rendered on the page.

## Install locally
1. Download this folder.
2. Chrome -> Extensions -> Manage Extensions.
3. Enable Developer mode.
4. Load unpacked -> select this folder.
5. Open an Instagram Reel/post, expose comments/accounts on screen, then click the extension.

## Next experiment
Test on 5-10 real Reels. If the visible-profile extraction is reliable, add:
- context classification (commenter vs author/navigation)
- Hebrew/Israel relevance scoring
- business/bot filtering
- export into /growth/ dashboard
