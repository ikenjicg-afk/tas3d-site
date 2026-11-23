"""Render the link-preview cover (1200×630) from cover.html.

Usage, from the repository root:  python3 tools/og-cover/render.py media/og-cover-vN.jpg
Then point og:image / twitter:image / the Event "image" in index.html to the new file name
(a new name makes Telegram, WhatsApp and the CDN fetch the new picture), and run tools/build_lang.py.
"""
import os, sys
from PIL import Image
from playwright.sync_api import sync_playwright

here = os.path.dirname(os.path.abspath(__file__))
out = sys.argv[1] if len(sys.argv) > 1 else 'og-cover.jpg'
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--no-sandbox', '--disable-gpu', '--allow-file-access-from-files'])
    pg = b.new_page(viewport={'width': 1200, 'height': 630}, device_scale_factor=2)
    pg.goto('file://' + os.path.join(here, 'cover.html'))
    pg.evaluate('document.fonts.ready'); pg.wait_for_timeout(800)
    png = os.path.join(here, 'cover@2x.png'); pg.screenshot(path=png)
    b.close()
im = Image.open(png).convert('RGB').resize((1200, 630), Image.LANCZOS)
os.remove(png)
im.save(out, 'JPEG', quality=88, optimize=True, progressive=True)
print(out, im.size, os.path.getsize(out) // 1024, 'KB')
