"""Read aggregate Web Analytics only; credentials stay in the runner environment."""
import datetime as dt
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request

ENDPOINT = 'https://api.cloudflare.com/client/v4/graphql'
ACCOUNT = 'c3c805dee37630770e8771b1ae2f419b'
HOST = 'vainzof.co.il'
TYPE_REF = 'kind name ofType { kind name ofType { kind name ofType { kind name } } }'


def named(ref):
    while ref.get('ofType'):
        ref = ref['ofType']
    return ref['name']


def request(query):
    token = os.environ.get('CLOUDFLARE_API_TOKEN', '')
    if not token:
        raise RuntimeError('Missing CLOUDFLARE_API_TOKEN repository secret')
    req = urllib.request.Request(ENDPOINT, data=json.dumps({'query': query}).encode(),
        headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f'Cloudflare HTTP {exc.code}; check token permissions') from None
    if result.get('errors'):
        messages = '; '.join(str(e.get('message', 'GraphQL error')) for e in result['errors'])
        raise RuntimeError(messages.replace(token, '[REDACTED]'))
    return result['data']


def main():
    # Discover the current schema instead of guessing metric or filter names.
    schema = request('{ __schema { types { name fields { name type { ' + TYPE_REF +
        ' } args { name type { ' + TYPE_REF + ' } } } inputFields { name } } } }')
    types = {t['name']: t for t in schema['__schema']['types']}
    dataset = 'rumPageloadEventsAdaptiveGroups'
    candidates = [f for t in types.values() for f in (t.get('fields') or []) if f['name'] == dataset and any(a['name'] == 'filter' for a in f['args'])]
    if not candidates:
        raise RuntimeError('Web Analytics dataset is unavailable to this token')
    field = candidates[0]
    filters = next(a for a in field['args'] if a['name'] == 'filter')
    available = {f['name'] for f in types[named(filters['type'])]['inputFields']}
    required = {'requestHost', 'datetime_geq', 'datetime_lt'}
    if not required <= available:
        raise RuntimeError('Required hostname/time filters unavailable: ' + ', '.join(sorted(required - available)))
    output = {f['name']: f for f in types[named(field['type'])]['fields']}
    if 'count' not in output:
        raise RuntimeError('Page-load count metric unavailable')
    sums = {f['name'] for f in types[named(output['sum']['type'])]['fields']} if 'sum' in output else set()
    has_visits = 'visits' in sums
    selection = 'count' + (' sum { visits }' if has_visits else '')
    end = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    rows = []
    for offset in range(7, 0, -1):
        start = end - dt.timedelta(days=offset)
        stop = start + dt.timedelta(days=1)
        iso = lambda value: value.isoformat().replace('+00:00', 'Z')
        query = ('{ viewer { accounts(filter: {accountTag: ' + json.dumps(ACCOUNT) + '}) { '
            + dataset + '(limit: 1, filter: {requestHost: ' + json.dumps(HOST)
            + ', datetime_geq: ' + json.dumps(iso(start)) + ', datetime_lt: '
            + json.dumps(iso(stop)) + '}) { ' + selection + ' } } } }')
        accounts = request(query)['viewer']['accounts']
        if len(accounts) != 1:
            raise RuntimeError('Token cannot access the configured account')
        groups = accounts[0][dataset]
        rows.append({'start_utc': iso(start), 'end_utc': iso(stop),
            'page_views': sum(g['count'] for g in groups),
            'visits': sum(g['sum']['visits'] for g in groups) if has_visits else None})
    dimensions = {f['name'] for f in types[named(output['dimensions']['type'])]['fields']}
    if 'requestPath' not in dimensions:
        raise RuntimeError('Page path dimension unavailable in API schema')
    last = rows[-1]
    query = ('{ viewer { accounts(filter: {accountTag: ' + json.dumps(ACCOUNT) + '}) { '
        + dataset + '(limit: 1000, orderBy: [count_DESC], filter: {requestHost: '
        + json.dumps(HOST) + ', datetime_geq: ' + json.dumps(last['start_utc'])
        + ', datetime_lt: ' + json.dumps(last['end_utc'])
        + '}) { count dimensions { requestPath } } } } }')
    accounts = request(query)['viewer']['accounts']
    if len(accounts) != 1:
        raise RuntimeError('Token cannot access the configured account')
    pages = [{'path': g['dimensions']['requestPath'], 'page_views': g['count']}
        for g in accounts[0][dataset]]
    report = {'hostname': HOST, 'generated_utc': end.isoformat(), 'days': rows,
        'pages_last_24h': pages, 'pages_truncated': len(pages) == 1000,
        'page_views': sum(r['page_views'] for r in rows),
        'visits': sum(r['visits'] for r in rows) if has_visits else None}
    directory = Path('analytics-report')
    directory.mkdir(exist_ok=True)
    (directory / 'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    lines = [f'# Web Analytics: {HOST}', '', 'Last 7 days, rolling UTC windows.', '',
        f'Page views: {report["page_views"]}',
        f'Visits: {report["visits"]}' if has_visits else 'Visits: unavailable in the API schema.', '',
        'Visits are not unique people. Data can be sampled; blocked beacons are not counted.', '',
        '| Start (UTC) | End (UTC) | Page views | Visits |', '| --- | --- | ---: | ---: |']
    lines.extend(f'| {r["start_utc"]} | {r["end_utc"]} | {r["page_views"]} | {r["visits"] if has_visits else "N/A"} |' for r in rows)
    lines.extend(['', '## Pages in the last 24 hours', '',
        f"Window: {last['start_utc']} to {last['end_utc']}", '',
        '| Page path | Page views |', '| --- | ---: |'])
    for page in pages:
        safe_path = str(page['path']).replace('|', '&#124;').replace('\n', '').replace('\r', '')
        lines.append(f"| {safe_path} | {page['page_views']} |")
    if not pages:
        lines.extend(['', 'No page views returned for this window.'])
    if report['pages_truncated']:
        lines.extend(['', 'Showing at most 1000 paths; the page list may be incomplete.'])
    markdown = '\n'.join(lines) + '\n'
    (directory / 'report.md').write_text(markdown, encoding='utf-8')
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as summary:
            summary.write(markdown)
    print(markdown)


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, KeyError, ValueError, urllib.error.URLError) as exc:
        token = os.environ.get('CLOUDFLARE_API_TOKEN', '')
        message = str(exc)
        print('Report failed: ' + (message.replace(token, '[REDACTED]') if token else message), file=sys.stderr)
        sys.exit(1)
