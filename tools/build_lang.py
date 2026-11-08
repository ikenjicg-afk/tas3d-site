#!/usr/bin/env python3
"""Build the English and Uzbek pages of tas3d.uz from index.html.

index.html is the only page to edit (Russian text in the markup, EN/UZ in
window.TAS3D_I18N). This script writes en/index.html and uz/index.html with the
translated text already in the markup, their own <head> (title, description,
canonical, Open Graph, schema.org Event), and sitemap.xml with all three
addresses. Run it from the repository root after every change to index.html:

    python3 tools/build_lang.py

Needs Python 3 and Node.js (Node only reads the translations script).
"""
import datetime
import html
import json
import os
import re
import subprocess
import sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://tas3d.uz'
LANGS = {'en': 0, 'uz': 1}          # index in TAS3D_I18N values
LOCALE = {'ru': 'ru_RU', 'en': 'en_US', 'uz': 'uz_UZ'}
OG_DESC = {
    'en': 'Tashkent, 03.12.2026, 15:00–19:00. Central Asian University.',
    'uz': 'Toshkent, 03.12.2026, 15:00–19:00. Central Asian University.',
}
EVENT_DESC = {
    'en': 'A forum on 3D visualisation in architecture: talks, workshops and networking for architects, visualisers, designers and developers.',
    'uz': 'Arxitekturada 3D-vizualizatsiya bo‘yicha forum: arxitektorlar, vizualizatorlar, dizaynerlar va developerlar uchun ma’ruzalar, master-klasslar va netvorking.',
}
TA = re.compile(r'aria-label="([^"]*)" data-ta="([^"]+)"')  # screen-reader labels with a translation key
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}


def fail(msg):
    sys.exit('build_lang: ' + msg)


def read_translations(src):
    m = re.search(r'<script>\n/\* TAS3D 2026 — translations\..*?</script>', src, re.S)
    if not m:
        fail('translations script not found in index.html')
    js = m.group(0)[len('<script>'):-len('</script>')]
    code = 'var window = {};\n' + js + '\nprocess.stdout.write(JSON.stringify({i18n: window.TAS3D_I18N, head: window.TAS3D_HEAD}));'
    out = subprocess.run(['node', '-e', code], capture_output=True, text=True)
    if out.returncode != 0:
        fail('node could not read the translations:\n' + out.stderr)
    data = json.loads(out.stdout)
    if not data.get('i18n') or not data.get('head'):
        fail('TAS3D_I18N or TAS3D_HEAD is empty')
    return data['i18n'], data['head']


class Finder(HTMLParser):
    """Finds every element with data-t and the source range of its inner HTML."""

    def __init__(self, src):
        super().__init__(convert_charrefs=True)
        self.src = src
        self.line_start = [0]
        for i, ch in enumerate(src):
            if ch == '\n':
                self.line_start.append(i + 1)
        self.stack = []      # [tag, key, inner_start, in_template]
        self.found = []      # (key, inner_start, inner_end, in_template)
        self.tpl = 0

    def at(self):
        line, col = self.getpos()
        return self.line_start[line - 1] + col

    def handle_starttag(self, tag, attrs):
        start = self.at()
        text = self.get_starttag_text()
        if self.src[start:start + len(text)] != text:
            fail('lost track of the markup at %r' % text[:60])
        if tag in VOID:
            return
        key = dict(attrs).get('data-t')
        self.stack.append([tag, key, start + len(text), self.tpl > 0])
        if tag == 'template':
            self.tpl += 1

    def handle_startendtag(self, tag, attrs):
        # self-closing tags such as <circle .../> inside inline SVG icons: nothing to track
        start = self.at()
        text = self.get_starttag_text()
        if self.src[start:start + len(text)] != text:
            fail('lost track of the markup at %r' % text[:60])

    def handle_endtag(self, tag):
        end = self.at()
        if self.src[end:end + 2] != '</':
            fail('lost track of the markup at offset %d' % end)
        while self.stack:
            t, key, inner, in_tpl = self.stack.pop()
            if t == 'template':
                self.tpl -= 1
            if t == tag:
                if key:
                    self.found.append((key, inner, end, in_tpl))
                return
            if key:
                fail('element <%s data-t="%s"> has no closing tag' % (t, key))
        fail('closing tag </%s> without an opening one' % tag)


def set_attr(src, pattern, value, what):
    new, n = re.subn(pattern, lambda m: m.group(1) + html.escape(value, quote=True) + m.group(2), src, count=1)
    if n != 1:
        fail('could not set ' + what)
    return new


def build(src, lang, idx, i18n, head, ru_map, ranges):
    out = src
    # 1. translated text into the markup (back to front, so offsets stay valid)
    for key, a, b in sorted(ranges, key=lambda r: -r[1]):
        if key.startswith('_') or key not in i18n:
            continue
        out = out[:a] + i18n[key][idx] + out[b:]
    # screen-reader labels (aria-label + data-ta)
    def ta(mm):
        k = mm.group(2)
        if k not in i18n:
            return mm.group(0)
        return 'aria-label="%s" data-ta="%s"' % (html.escape(re.sub(r'<[^>]+>', '', i18n[k][idx]), quote=True), k)
    out = TA.sub(ta, out)
    url = '%s/%s/' % (SITE, lang)
    title, desc = head[lang]
    # 2. head
    out = out.replace('<!doctype html>\n', '<!doctype html>\n<!-- Generated from /index.html by tools/build_lang.py. Do not edit: change index.html and run the script. -->\n', 1)
    out, n = re.subn(r'<html lang="ru">', '<html lang="%s">' % lang, out, count=1)
    if n != 1:
        fail('<html lang="ru"> not found')
    out = set_attr(out, r'(<title>)[^<]*(</title>)', title, 'title')
    out = set_attr(out, r'(<meta name="description" content=")[^"]*(">)', desc, 'description')
    out = set_attr(out, r'(<link rel="canonical" href=")[^"]*(">)', url, 'canonical')
    out = set_attr(out, r'(<meta property="og:url" content=")[^"]*(">)', url, 'og:url')
    out = set_attr(out, r'(<meta property="og:title" content=")[^"]*(">)', title, 'og:title')
    out = set_attr(out, r'(<meta property="og:description" content=")[^"]*(">)', OG_DESC[lang], 'og:description')
    out = set_attr(out, r'(<meta name="twitter:title" content=")[^"]*(">)', title, 'twitter:title')
    out = set_attr(out, r'(<meta name="twitter:description" content=")[^"]*(">)', OG_DESC[lang], 'twitter:description')
    out = set_attr(out, r'(<meta property="og:locale" content=")[^"]*(">)', LOCALE[lang], 'og:locale')
    others = [l for l in ('ru', 'en', 'uz') if l != lang]
    alts = ''.join('<meta property="og:locale:alternate" content="%s">\n' % LOCALE[l] for l in others)
    out, n = re.subn(r'(?:<meta property="og:locale:alternate" content="[^"]*">\n)+', alts, out, count=1)
    if n != 1:
        fail('og:locale:alternate not found')
    m = re.search(r'(<script type="application/ld\+json">)(.*?)(</script>)', out, re.S)
    if not m:
        fail('schema.org script not found')
    ev = json.loads(m.group(2))
    ev['description'] = EVENT_DESC[lang]
    ev['url'] = url
    out = out[:m.start(2)] + json.dumps(ev, ensure_ascii=False, separators=(',', ':')) + out[m.end(2):]
    # 3. language switch shows this language as current
    out = re.sub(r'(<button type="button" data-lang="(ru|en|uz)" aria-pressed=")(true|false)(")',
                 lambda mm: mm.group(1) + ('true' if mm.group(2) == lang else 'false') + mm.group(4), out)
    # 4. the page language and the Russian text for switching back, before the behaviour script
    marker = '<script>\n/* TAS3D 2026 — behaviour'
    if out.count(marker) != 1:
        fail('behaviour script not found')
    data = '<script>window.TAS3D_PAGE_LANG = %s;\nwindow.TAS3D_RU = %s;</script>\n' % (
        json.dumps(lang), json.dumps(ru_map, ensure_ascii=False).replace('</', '<\\/'))
    out = out.replace(marker, data + marker, 1)
    return out


def sitemap():
    today = datetime.date.today().isoformat()
    urls = {'ru': SITE + '/', 'en': SITE + '/en/', 'uz': SITE + '/uz/'}
    links = ''.join('    <xhtml:link rel="alternate" hreflang="%s" href="%s"/>\n' % (l, u) for l, u in urls.items())
    links += '    <xhtml:link rel="alternate" hreflang="x-default" href="%s"/>\n' % urls['ru']
    body = ''.join('  <url>\n    <loc>%s</loc>\n    <lastmod>%s</lastmod>\n%s  </url>\n' % (u, today, links) for u in urls.values())
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">\n'
            + body + '</urlset>\n')


def main():
    src = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    i18n, head = read_translations(src)
    finder = Finder(src)
    finder.feed(src)
    finder.close()
    found = sorted(finder.found, key=lambda r: r[1])
    # only the outermost data-t elements are replaced (like setting innerHTML in the page script)
    ranges, last_end = [], -1
    for key, a, b, in_tpl in found:
        if a >= last_end:
            ranges.append((key, a, b))
            last_end = b
    # Russian text by key: the first occurrence outside <template>, as the page script sees it
    ru_map = {}
    for key, a, b, in_tpl in found:
        if not in_tpl and key not in ru_map:
            ru_map[key] = src[a:b]
    for key, a, b, in_tpl in found:
        if key not in ru_map:
            ru_map[key] = src[a:b]
    for mm in TA.finditer(src):
        ru_map.setdefault(mm.group(2), html.unescape(mm.group(1)))
    for lang, idx in LANGS.items():
        page = build(src, lang, idx, i18n, head, ru_map, ranges)
        os.makedirs(os.path.join(ROOT, lang), exist_ok=True)
        with open(os.path.join(ROOT, lang, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(page)
    with open(os.path.join(ROOT, 'sitemap.xml'), 'w', encoding='utf-8') as f:
        f.write(sitemap())
    missing = sorted({k for k, a, b in ranges if not k.startswith('_') and k not in i18n})
    print('build_lang: %d texts translated; en/index.html, uz/index.html, sitemap.xml written' % len(ranges))
    if missing:
        print('build_lang: no EN/UZ translation (Russian kept): ' + ', '.join(missing))


if __name__ == '__main__':
    main()
