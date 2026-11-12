#!/usr/bin/env python3
"""Daily check of the live site tas3d.uz.

Run by .github/workflows/site-check.yml every morning and after changes to this checker.
Uses only the Python standard library. Exits with code 1 (the GitHub run fails and GitHub
e-mails the account owner) when any of these is true:

- a page on the live site differs from the file in this repository
  (index.html, en/index.html, uz/index.html): the site was replaced, or the last push was not published;
- tas3d.uz or www.tas3d.uz no longer point to GitHub Pages (domain or DNS taken over, or broken);
- http://tas3d.uz/ does not redirect to https://;
- the HTTPS certificate is invalid or expires in less than MIN_CERT_DAYS days.

Run locally from the repository root: python3 tools/site_check.py
"""
import datetime
import hashlib
import http.client
import os
import socket
import ssl
import sys
import time
import urllib.request

HOST = 'tas3d.uz'
GITHUB_PAGES_IPS = {'185.199.108.153', '185.199.109.153', '185.199.110.153', '185.199.111.153'}
PAGES = {'/': 'index.html', '/en/': 'en/index.html', '/uz/': 'uz/index.html'}
MIN_CERT_DAYS = 14
UA = 'tas3d-site-check (+https://github.com/ikenjicg-afk/tas3d-site)'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

problems = []   # (english for the log, russian for the summary)


def ok(msg):
    print('OK   ' + msg)


def fail(msg, ru):
    print('FAIL ' + msg)
    problems.append((msg, ru))


def check_dns():
    for name in (HOST, 'www.' + HOST):
        try:
            ips = {ai[4][0] for ai in socket.getaddrinfo(name, 443, socket.AF_INET, socket.SOCK_STREAM)}
        except OSError as e:
            fail('%s: DNS lookup failed: %s' % (name, e), 'Домен %s не находится в DNS.' % name)
            continue
        if ips and ips <= GITHUB_PAGES_IPS:
            ok('%s -> GitHub Pages %s' % (name, sorted(ips)))
        else:
            fail('%s points to %s, expected GitHub Pages %s' % (name, sorted(ips), sorted(GITHUB_PAGES_IPS)),
                 'Домен %s ведёт не на GitHub (%s). Проверьте записи в Cloudflare и NS-серверы в sayt.uz.' % (name, ', '.join(sorted(ips))))


def check_redirect():
    try:
        c = http.client.HTTPConnection(HOST, 80, timeout=20)
        c.request('GET', '/', headers={'User-Agent': UA})
        r = c.getresponse()
        loc = r.getheader('Location', '')
        c.close()
    except OSError as e:
        fail('http://%s/: %s' % (HOST, e), 'Сайт не открывается по http://%s/.' % HOST)
        return
    if r.status in (301, 308) and loc.startswith('https://' + HOST):
        ok('http://%s/ -> %d %s' % (HOST, r.status, loc))
    else:
        fail('http://%s/ answered %d %s, expected a redirect to https' % (HOST, r.status, loc),
             'Адрес http:// не переводит на https://. Проверьте Enforce HTTPS в настройках Pages.')


def check_cert():
    ctx = ssl.create_default_context()
    try:
        with socket.create_connection((HOST, 443), timeout=20) as s:
            with ctx.wrap_socket(s, server_hostname=HOST) as t:
                cert = t.getpeercert()
    except (OSError, ssl.SSLError) as e:
        fail('HTTPS certificate: %s' % e, 'Сертификат HTTPS недействителен: браузеры покажут предупреждение.')
        return
    exp = datetime.datetime.fromtimestamp(ssl.cert_time_to_seconds(cert['notAfter']), datetime.timezone.utc)
    days = (exp - datetime.datetime.now(datetime.timezone.utc)).days
    if days >= MIN_CERT_DAYS:
        ok('certificate valid until %s (%d days left)' % (exp.strftime('%Y-%m-%d'), days))
    else:
        fail('certificate expires %s (%d days left)' % (exp.strftime('%Y-%m-%d'), days),
             'Сертификат HTTPS истекает через %d дн. (%s). GitHub обычно продлевает его сам; если не продлил — проверьте настройки Pages.' % (days, exp.strftime('%d.%m.%Y')))


def fetch(path):
    # a unique query string skips the CDN cache, so we see what GitHub Pages serves right now
    url = 'https://%s%s?check=%d' % (HOST, path, time.time())
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Cache-Control': 'no-cache'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def check_pages(tries=4, wait=90):
    diff = []
    for attempt in range(tries):
        diff = []
        for path, name in PAGES.items():
            with open(os.path.join(ROOT, name), 'rb') as f:
                want = f.read()
            try:
                got = fetch(path)
            except OSError as e:
                diff.append(('%s: %s' % (path, e), 'Страница https://%s%s не открывается (%s).' % (HOST, path, e)))
                continue
            if hashlib.sha256(got).digest() != hashlib.sha256(want).digest():
                diff.append(('%s differs from %s (%d bytes live, %d in the repository)' % (path, name, len(got), len(want)),
                             'Страница https://%s%s отличается от файла %s в репозитории: сайт подменили или последнее изменение не опубликовалось.' % (HOST, path, name)))
        if not diff:
            ok('live pages match the repository: ' + ', '.join(PAGES))
            return
        if attempt < tries - 1:
            print('...  ' + '; '.join(d[0] for d in diff) + ' - retrying in %ds (a fresh push may still be deploying)' % wait)
            time.sleep(wait)
    for msg, ru in diff:
        fail(msg, ru)


def main():
    check_dns()
    check_redirect()
    check_cert()
    check_pages()
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        with open(summary, 'a', encoding='utf-8') as f:
            if problems:
                f.write('## ❌ Проверка tas3d.uz: есть проблемы\n\n' + ''.join('- %s\n' % ru for _, ru in problems))
            else:
                f.write('## ✅ Сайт tas3d.uz в порядке\n\nДомен ведёт на GitHub, http переводит на https, сертификат действителен, '
                        'страницы /, /en/ и /uz/ совпадают с файлами в репозитории.\n')
    print('PROBLEMS: %d' % len(problems))
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
