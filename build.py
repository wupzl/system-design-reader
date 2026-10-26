"""Build a self-contained GitHub Pages reader from maintained Markdown, without network access."""
from pathlib import Path
import html
import json
import re
import shutil
import markdown

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'docs'
BOOK = json.loads((ROOT / 'book.json').read_text(encoding='utf-8'))
CHAPTERS = BOOK['chapters']
COUNT = len(CHAPTERS)
PROJECTS = [('pytorch-apprentice', 'PyTorch：炼金术士的学徒'), ('ai-era-reader', 'AI 纪元'), ('data-empire-reader', '数据帝国'), ('rag-empire-reader', 'RAG 帝国'), ('system-design-reader', '系统设计'), ('online-troubleshooting-reader', '生产环境')]


def page(title, body, reading=False):
    menu = ''.join(f'<a href="/{slug}/"'+(' aria-current="page"' if slug == 'system-design-reader' else '')+f'>{name}</a>' for slug, name in PROJECTS)
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="color-scheme" content="light dark"><meta name="description" content="系统设计：从一台服务器开始。跟随林默与老周，在八章故事中理解缓存、数据库、消息队列与分布式共识。连载中，第九章待续。"><title>{html.escape(title)} · 系统设计</title><script>try{{document.documentElement.dataset.theme=localStorage.getItem('reader-theme')||'white';document.documentElement.style.setProperty('--reading-size',Math.max(16,Math.min(26,Number(localStorage.getItem('reader-size'))||18))+'px')}}catch(e){{}}</script><link rel="stylesheet" href="style.css"><link rel="stylesheet" href="shelf-nav.css"><link rel="stylesheet" href="reader.css"><script src="app.js" defer></script></head>
<body class="{'reading' if reading else ''}"><a class="skip" href="#main">跳到正文</a><header><a class="brand" href="index.html">系统设计<span>SYSTEM DESIGN</span></a><nav class="shelf-nav" aria-label="学习项目导航"><a class="shelf-home" href="/">← 学习书架</a><details class="shelf-switch"><summary>切换项目 ▾</summary><div class="shelf-menu">{menu}</div></details></nav><div class="controls"><button id="smaller" aria-label="缩小字号" type="button">A−</button><button id="larger" aria-label="增大字号" type="button">A＋</button><button id="theme" aria-label="切换阅读背景" type="button">纯白</button></div></header>
{body}<footer>系统设计：从一台服务器开始<br><small>现有 {COUNT} 章 · 连载中 · 第九章待续</small><p><a href="editorial.html">整理说明与技术参考</a> · <a href="https://github.com/wupzl/system-design-reader">项目源码 ↗</a></p></footer></body></html>'''


def render(source):
    md = markdown.Markdown(extensions=['fenced_code', 'tables', 'toc', 'sane_lists', 'md_in_html'], extension_configs={'toc': {'toc_depth': '2-2'}})
    content = md.convert(source)
    content = content.replace('../assets/diagrams/', 'diagrams/')

    def figure(match):
        image = match[1]
        src = re.search(r'src="([^"]+)"', image)[1]
        label = re.search(r'alt="([^"]*)"', image)[1]
        return f'<figure class="architecture"><div class="diagram-frame" tabindex="0" role="region" aria-label="{label}，可横向滚动">{image}</div><figcaption>{label}<a href="{src}" target="_blank" rel="noopener">查看大图 ↗</a></figcaption></figure>'
    content = re.sub(r'<p>(<img [^>]*src="diagrams/[^>]+>)</p>', figure, content)
    return content, md.toc


def main():
    OUT.mkdir(exist_ok=True)
    files = sorted((ROOT / 'chapters').glob('[0-9][0-9].md'))
    assert len(files) == COUNT, 'Update book.json and chapters/ together.'
    assert [c['number'] for c in CHAPTERS] == list(range(1, COUNT+1))
    preview = ''
    for item, file in zip(CHAPTERS, files):
        number, title = item['number'], item['title']
        source = file.read_text(encoding='utf-8')
        assert source.splitlines()[0] == '# ' + title
        body, toc = render(source.split('\n', 1)[1])
        if number == COUNT:
            anchor = re.search(r'<h2 id="([^"]+)">待续：', body)
            assert anchor, 'The last chapter must retain the next chapter preview.'
            preview = f'chapter-{number:02}.html#{anchor[1]}'
        previous = f'<a href="chapter-{number-1:02}.html" rel="prev">← 上一章</a>' if number > 1 else '<a href="index.html">← 全书目录</a>'
        following = f'<a href="chapter-{number+1:02}.html" rel="next">下一章 →</a>' if number < COUNT else '<a href="index.html#coming">第九章待续 · 返回目录 →</a>'
        contents = f'''<div class="reader-layout"><aside><a href="index.html">← 全书目录</a><p class="eyebrow">本章导航</p>{toc}</aside><main id="main"><div class="chapter-heading"><p class="eyebrow">CHAPTER {number:02} / {COUNT:02} · 连载中</p><h1>{html.escape(title)}</h1><p>{item['description']}</p></div><details class="mobile-toc"><summary>展开本章目录</summary>{toc}</details><article>{body}</article><nav class="chapter-nav" aria-label="章节切换">{previous}{following}</nav></main></div>'''
        (OUT / f'chapter-{number:02}.html').write_text(page(title, contents, True), encoding='utf-8')
    cards = ''.join(f'<a class="card" href="chapter-{item["number"]:02}.html"><span class="number">{item["number"]:02}</span><div><h3>{html.escape(item["title"])}</h3><p>{item["description"]}</p></div><span class="arrow" aria-hidden="true">↗</span></a>' for item in CHAPTERS)
    home = f'''<main class="home" id="main"><section class="hero"><p class="eyebrow">一本从真实问题出发的技术小说</p><h1>从一台服务器，<br>到分布式世界<span>。</span></h1><p class="intro">用户越来越多，系统一次次遇到新的难题。跟随林默与架构师老周，从第一条请求开始，理解每项技术为何出现，以及它带来的取舍。</p><a class="start" href="chapter-01.html">从第一章开始阅读 <span>→</span></a><p class="serial">8 章 · 连载中 · 第九章待续</p><div class="book-mark" aria-hidden="true">SD<span>系统设计</span><small>容量 · 架构 · 取舍</small></div></section><section class="catalog"><div class="section-title"><h2>全书导航</h2><span>从缓存、数据库，到分布式共识</span></div><div class="cards">{cards}</div><section class="coming" id="coming"><span class="number">09</span><div><p class="eyebrow">下一章预告 · 尚未发布</p><h3>{BOOK['next']}</h3><p>本地事务、2PC、TCC、Saga、Outbox 与最终一致性。</p><a href="{preview}">阅读第八章末尾预告 →</a></div></section></section></main>'''
    (OUT / 'index.html').write_text(page('全书导航', home), encoding='utf-8')
    editorial, _ = render((ROOT / 'EDITORIAL.md').read_text(encoding='utf-8'))
    (OUT / 'editorial.html').write_text(page('整理说明与技术参考', f'<main class="home standalone" id="main"><a href="index.html">← 全书目录</a><article>{editorial}</article></main>'), encoding='utf-8')
    (OUT / 'chapters.json').write_text(json.dumps(CHAPTERS, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    nav = '# 系统设计：从一台服务器开始\n\n现有 8 章，连载中；第九章仅有预告。\n\n' + '\n'.join(f'- [{c["number"]:02} · {c["title"]}]({c["number"]:02}.md)：{c["description"]}' for c in CHAPTERS) + '\n'
    (ROOT / 'chapters/00-全书导航.md').write_text(nav, encoding='utf-8')
    for path in (ROOT / 'assets').iterdir():
        if path.is_file():
            shutil.copyfile(path, OUT / path.name)
        elif path.name == 'diagrams':
            shutil.copytree(path, OUT / path.name, dirs_exist_ok=True)
    (OUT / '.nojekyll').touch()
    print(f'Built {COUNT} chapters, home, editorial page and {len(list((OUT / "diagrams").glob("*.svg")))} SVG diagrams.')


if __name__ == '__main__':
    main()
