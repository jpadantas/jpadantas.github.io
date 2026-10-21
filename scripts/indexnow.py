"""Tell Bing (and other IndexNow search engines) that pages were added or changed.

Usage (from the repository root, after the change is pushed and live):
    python scripts/indexnow.py <publication-id-or-url> ...   # e.g. dantas2026poker
    python scripts/indexnow.py --all                         # every URL in sitemap.xml

The key file <KEY>.txt at the site root proves ownership of www.joaopadantas.com.
Google does not use IndexNow; it reads sitemap.xml instead.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST = 'www.joaopadantas.com'
SITE = f'https://{HOST}'
KEY = '95a2003be1ae756579bb14819874c5d3'
ENDPOINT = 'https://api.indexnow.org/indexnow'

STATUS = {
    200: 'OK - URLs submitted',
    202: 'Accepted - key validation pending, URLs will be processed',
    400: 'Bad request',
    403: 'Forbidden - key file not found or does not match',
    422: 'Unprocessable - URLs do not belong to the host or key mismatch',
    429: 'Too many requests - try again later',
}


def sitemap_urls():
    with open(os.path.join(ROOT, 'sitemap.xml'), encoding='utf-8') as f:
        return re.findall(r'<loc>(.*?)</loc>', f.read())


def to_url(arg):
    if arg.startswith('http'):
        return arg
    if os.path.exists(os.path.join(ROOT, 'bib', f'{arg}.bib')):
        return f'{SITE}/publications/{arg}/'
    return f'{SITE}/{arg.lstrip("/")}'


def submit(urls):
    body = json.dumps({'host': HOST, 'key': KEY, 'keyLocation': f'{SITE}/{KEY}.txt', 'urlList': urls}).encode()
    request = urllib.request.Request(ENDPOINT, data=body, method='POST',
                                     headers={'Content-Type': 'application/json; charset=utf-8'})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            code = response.status
    except urllib.error.HTTPError as error:
        code = error.code
    print(f'{len(urls)} URL(s) -> HTTP {code}: {STATUS.get(code, "unexpected response")}')
    return code in (200, 202)


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    urls = sitemap_urls() if args == ['--all'] else [to_url(a) for a in args]
    sys.exit(0 if submit(urls) else 1)


if __name__ == '__main__':
    main()
