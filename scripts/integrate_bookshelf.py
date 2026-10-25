"""Add this reader to the sibling bookshelf and persist links in reader generators."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
LINK = '<a href="/system-design-reader/">系统设计</a>'
for repo in ('ai-era-reader', 'pytorch-apprentice', 'data-empire-reader', 'rag-empire-reader'):
    base = ROOT / repo
    changed = 0
    for folder in ('docs', 'assets'):
        if not (base / folder).is_dir():
            continue
        for path in (base / folder).glob('*.html'):
            value = path.read_text(encoding='utf-8')
            if 'class="shelf-menu"' in value and '/system-design-reader/' not in value:
                value = re.sub(r'(<div class="shelf-menu">)(.*?)(</div>)', lambda m: m[1]+m[2]+LINK+m[3], value, flags=re.S)
                path.write_text(value, encoding='utf-8')
                changed += 1
    build = base / 'build.py'
    if build.is_file():
        value = build.read_text(encoding='utf-8')
        if repo == 'pytorch-apprentice':
            # Its literal menu was missing RAG in the generator; use all five links.
            menu = ''.join(f'<a href="/{slug}/"'+(' aria-current="true"' if slug == repo else '')+f'>{label}</a>' for slug, label in [('pytorch-apprentice', 'PyTorch：炼金术士的学徒'), ('ai-era-reader', 'AI 纪元'), ('data-empire-reader', '数据帝国'), ('rag-empire-reader', 'RAG 帝国'), ('system-design-reader', '系统设计')])
            value = re.sub(r'(<div class="shelf-menu">).*?(</div>)', lambda m: m[1]+menu+m[2], value, count=1, flags=re.S)
        elif "('system-design-reader','系统设计')" not in value:
            value = value.replace("('rag-empire-reader','RAG 帝国')", "('rag-empire-reader','RAG 帝国'),('system-design-reader','系统设计')")
        build.write_text(value, encoding='utf-8')
    print(f'{repo}: updated {changed} page menus and its generator where available')

shelf = ROOT / 'bookshelf'
path = shelf / 'index.html'
value = path.read_text(encoding='utf-8')
if '/system-design-reader/' not in value:
    value = value.replace('04 / 持续更新', '05 / 持续更新')
    card = '<a class="project rust" href="/system-design-reader/"><div class="cover" aria-hidden="true"><span class="volume">05 / SYSTEM DESIGN</span><strong>系统设计<span class="cover-subtitle">从一台服务器开始</span></strong><span class="symbol">SD</span><span class="cover-foot">容量 · 架构 · 取舍</span></div><div class="project-copy"><p class="category">系统设计 · 技术小说</p><h3>系统设计：从一台服务器开始</h3><p>跟随林默与老周，从第一次宕机开始，理解缓存、数据库、消息队列与分布式共识为何出现。</p><div class="tags"><span>8 章 · 第九章待续</span><span class="project-status">连载</span><span>8 张架构图</span></div><span class="enter">进入阅读 <span aria-hidden="true">↗</span></span></div></a>'
    assert '</div><div class="shelf-note">' in value
    value = value.replace('</div><div class="shelf-note">', card+'</div><div class="shelf-note">', 1)
    path.write_text(value, encoding='utf-8')

path = shelf / 'verify.py'
value = path.read_text(encoding='utf-8')
if "'system-design-reader':" not in value:
    value = value.replace("'rag-empire-reader': '全书完结',", "'rag-empire-reader': '全书完结',\n    'system-design-reader': '连载',")
value = value.replace('four sibling', 'five sibling').replace('all four projects', 'all five projects').replace('four project counts', 'five project counts')
path.write_text(value, encoding='utf-8')

path = shelf / '.github/workflows/verify-readers.yml'
value = path.read_text(encoding='utf-8')
if 'repository: wupzl/system-design-reader' not in value:
    value = value.replace('      - uses: actions/setup-python@v5', '      - uses: actions/checkout@v4\n        with:\n          repository: wupzl/system-design-reader\n          ref: main\n          path: system-design-reader\n      - uses: actions/setup-python@v5')
    value = value.replace('python -m pip install -r bookshelf/requirements-test.txt', 'python -m pip install -r bookshelf/requirements-test.txt -r system-design-reader/requirements-test.txt')
    value = value.replace('all four readers', 'all five readers')
    value = value.replace('      - name: Verify PyTorch reading features', '      - name: Verify system design reader\n        run: python system-design-reader/verify.py\n      - name: Verify PyTorch reading features')
    value = value.replace('            pytorch-apprentice/test-results/', '            pytorch-apprentice/test-results/\n            system-design-reader/test-results/')
path.write_text(value, encoding='utf-8')

path = shelf / 'README.md'
value = path.read_text(encoding='utf-8').replace('数据帝国和 RAG 帝国四个阅读项目', '数据帝国、RAG 帝国和系统设计五个阅读项目')
value = value.replace('RAG 帝国 9 章（全书完结）。', 'RAG 帝国 9 章（全书完结）、系统设计 8 章（连载，第九章待续）。')
value = value.replace('其余四个仓库', '其余五个仓库').replace('`rag-empire-reader/` 目录', '`rag-empire-reader/`、`system-design-reader/` 目录')
value = value.replace('四项目切换菜单', '五项目切换菜单').replace('检出四个阅读仓库', '检出五个阅读仓库').replace('执行总验收与 PyTorch 完整验收', '执行总验收、系统设计阅读验收与 PyTorch 完整验收')
value = value.replace('python -m pip install -r bookshelf/requirements-test.txt', 'python -m pip install -r bookshelf/requirements-test.txt -r system-design-reader/requirements-test.txt')
path.write_text(value, encoding='utf-8')
print('bookshelf: added fifth project, verification coverage and CI checkout')
