"""Verify the standalone reader, content boundaries, local resources and reading interactions."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import unquote, urljoin, urlsplit
import hashlib
import json
import mimetypes
import re
import xml.etree.ElementTree as ET
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / 'docs'
OUT = ROOT / 'test-results'
BASE = 'https://reader.test/system-design-reader/'


class Document(HTMLParser):
    def __init__(self, path):
        super().__init__()
        self.links = []
        self.ids = set()
        self.feed(path.read_text(encoding='utf-8'))

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            assert attrs['id'] not in self.ids, f'Duplicate id {attrs["id"]}'
            self.ids.add(attrs['id'])
        if tag in ('a', 'link', 'script', 'img'):
            link = attrs.get('href') or attrs.get('src')
            if link:
                self.links.append(link)


def main():
    OUT.mkdir(exist_ok=True)
    book = json.loads((ROOT / 'book.json').read_text(encoding='utf-8'))
    assert len(book['chapters']) == 8
    assert len(list(DOCS.glob('chapter-*.html'))) == 8
    assert not (DOCS / 'chapter-09.html').exists()
    source = (ROOT / 'source/original.md').read_text(encoding='utf-8')
    starts = list(re.finditer(r'^## 第[一二三四五六七八]章：([^\n]+)', source, re.M))
    for i, start in enumerate(starts):
        current = (ROOT / f'chapters/{i+1:02}.md').read_text(encoding='utf-8')
        original = source[start.end():starts[i+1].start() if i < 7 else len(source)]
        # Every numbered original section survives the editorial pass.
        for heading in re.findall(r'^# ([一二三四五六七八九十百]+、[^\n]+)', original, re.M):
            assert '## ' + heading in current, (i+1, heading)
        assert len(current) >= len(original) * .95, f'Unexpected content loss in chapter {i+1}'
    external_original = ROOT.parent / 'systemdesign.md'
    if external_original.exists():
        assert hashlib.sha256(external_original.read_bytes()).digest() == hashlib.sha256((ROOT/'source/original.md').read_bytes()).digest()
    pages = sorted(DOCS.glob('*.html'))
    parsed = {path: Document(path) for path in pages}
    for path, document in parsed.items():
        for link in document.links:
            target = urlsplit(urljoin(BASE + path.name, link))
            if target.netloc != 'reader.test' or not target.path.startswith('/system-design-reader/'):
                continue
            file = DOCS / unquote(target.path.removeprefix('/system-design-reader/'))
            if file.is_dir():
                file /= 'index.html'
            assert file.is_file(), (path.name, link)
            if target.fragment and file.suffix == '.html':
                assert unquote(target.fragment) in parsed[file].ids, (path.name, link)
    svgns = {'s': 'http://www.w3.org/2000/svg'}
    diagrams = list((DOCS / 'diagrams').glob('*.svg'))
    assert len(diagrams) == 8
    for path in diagrams:
        tree = ET.parse(path).getroot()
        assert tree.find('s:title', svgns).text and tree.find('s:desc', svgns).text
        assert tree.get('role') == 'img'
    errors = []
    missing = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for width in (390, 768, 1440):
            context = browser.new_context(viewport={'width': width, 'height': 1000}, reduced_motion='reduce')

            def serve(route):
                url = urlsplit(route.request.url)
                if url.netloc != 'reader.test' or not url.path.startswith('/system-design-reader/'):
                    route.abort()
                    return
                path = DOCS / unquote(url.path.removeprefix('/system-design-reader/'))
                if path.is_dir():
                    path /= 'index.html'
                if path.is_file():
                    route.fulfill(path=str(path), content_type=mimetypes.guess_type(path)[0] or 'application/octet-stream')
                else:
                    missing.append(str(path))
                    route.fulfill(status=404, body='Missing')

            context.route('**/*', serve)
            page = context.new_page()
            page.on('pageerror', lambda error: errors.append(str(error)))
            for path in pages:
                page.goto(BASE + path.name)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), (width, path.name, 'overflow')
                assert page.locator('h1').count() == 1, path.name
                assert page.locator('.shelf-menu a').count() == 9
                for image in page.locator('img').all():
                    assert image.evaluate('(img) => img.complete && img.naturalWidth > 0'), (width, path.name)
                if path.name.startswith('chapter-'):
                    assert page.locator('article').inner_text().strip()
                    for link in page.locator('.mobile-toc a').all():
                        anchor = unquote(link.get_attribute('href')[1:])
                        assert page.evaluate('(id) => !!document.getElementById(id)', anchor)
                    if width == 390:
                        page.locator('.mobile-toc summary').click()
                        first = page.locator('.mobile-toc a').first
                        first.click()
                        assert urlsplit(page.url).fragment
                if path.name == 'index.html':
                    assert page.locator('.card').count() == 8
                    assert '尚未发布' in page.locator('#coming').inner_text()
            page.goto(BASE + 'chapter-01.html')
            themes = set()
            for _ in range(3):
                page.locator('#theme').click()
                theme = page.locator('html').get_attribute('data-theme')
                themes.add(theme)
                page.reload()
                assert page.locator('html').get_attribute('data-theme') == theme
            assert themes == {'white', 'light', 'dark'}
            for button, expected in (('larger', 26), ('smaller', 16)):
                for _ in range(14):
                    if page.locator('#'+button).is_enabled():
                        page.locator('#'+button).click()
                assert page.locator('article').evaluate('(el) => getComputedStyle(el).fontSize') == f'{expected}px'
                page.reload()
                assert page.locator('article').evaluate('(el) => getComputedStyle(el).fontSize') == f'{expected}px'
            page.evaluate("localStorage.setItem('reader-size','18');localStorage.setItem('reader-theme','white')")
            page.reload()
            page.screenshot(path=str(OUT / f'chapter-01-{width}.png'))
            page.locator('.chapter-nav a[rel=next]').click()
            assert page.url == BASE + 'chapter-02.html'
            page.locator('.chapter-nav a[rel=prev]').click()
            assert page.url == BASE + 'chapter-01.html'
            page.goto(BASE)
            page.screenshot(path=str(OUT / f'home-{width}.png'), full_page=True)
            page.locator('#coming a').click()
            assert 'chapter-08.html#' in page.url
            assert '待续：订单成功了' in page.locator('article h2').last.inner_text()
            page.locator('.chapter-nav a').last.click()
            assert page.url == BASE + 'index.html#coming'
            page.goto(BASE + 'chapter-03.html')
            page.locator('.architecture').first.screenshot(path=str(OUT / f'diagram-{width}.png'))
            if width == 390:
                frame = page.locator('.diagram-frame').first
                assert frame.evaluate('(el) => el.scrollWidth > el.clientWidth')
                frame.evaluate('(el) => el.scrollLeft = el.scrollWidth')
                assert frame.evaluate('(el) => el.scrollLeft > 0')
            assert not errors, errors
            assert not missing, missing
            print(f'PASS: {len(pages)} pages, themes, sizes, navigation, diagrams at {width}px', flush=True)
            context.close()
        # Browser storage can be unavailable; reading controls must still work.
        context = browser.new_context(viewport={'width': 390, 'height': 850})
        context.route('**/*', serve)
        context.add_init_script("Object.defineProperty(window,'localStorage',{get(){throw new Error('Storage disabled')}})")
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(BASE + 'chapter-01.html')
        page.locator('#theme').click()
        page.locator('#larger').click()
        assert page.locator('article').evaluate('(el) => getComputedStyle(el).fontSize') == '19px'
        assert not errors, errors
        context.close()
        browser.close()
    print('PASS: complete 8-chapter serial, source archive, local links/anchors/SVGs, preview boundary and unavailable-storage behavior.')


if __name__ == '__main__':
    main()
