"""Publish this reader and, explicitly, the already reviewed sibling navigation changes.

Uses the normal Git credential helper. Credentials stay in memory and are never logged.
Run after build.py, verify.py, and the parent bookshelf/verify.py pass.
"""
from pathlib import Path
import argparse
import json
import os
import subprocess
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT.parent
OWNER = 'wupzl'
REPO = 'system-design-reader'
ENV = dict(os.environ, GIT_TERMINAL_PROMPT='0', GCM_INTERACTIVE='Never')


def git(path, *args):
    result = subprocess.run(['git', '-C', str(path), *args], capture_output=True, text=True, encoding='utf-8', env=ENV, check=True)
    return result.stdout.strip()


def credentials():
    result = subprocess.run(['git', 'credential', 'fill'], input='protocol=https\nhost=github.com\n\n', capture_output=True, text=True, env=ENV, check=True)
    fields = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
    if not fields.get('password'):
        raise SystemExit('A GitHub login with repository and Pages administration access is required.')
    return fields['password']


def api(token, method, path, data=None, missing_ok=False):
    request = urllib.request.Request('https://api.github.com'+path, method=method, data=json.dumps(data).encode('utf-8') if data is not None else None, headers={'Authorization': 'Bearer '+token, 'Accept': 'application/vnd.github+json', 'Content-Type': 'application/json', 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'system-design-reader-publisher'})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            raw = response.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as error:
        if error.code == 404 and missing_ok:
            return None
        # Error bodies from GitHub contain public API messages, not request headers.
        detail = json.loads(error.read().decode('utf-8')).get('message', 'GitHub API error')
        raise SystemExit(f'{method} {path}: HTTP {error.code}: {detail}') from None


def commit(path, paths, message):
    git(path, 'diff', '--check')
    git(path, 'add', '--', *paths)
    if git(path, 'diff', '--cached', '--name-only'):
        git(path, 'commit', '-m', message)
    print(f'{path.name}: {git(path, "rev-parse", "--short", "HEAD")}', flush=True)


def publish_reader(token):
    remote_url = f'https://github.com/{OWNER}/{REPO}.git'
    existing = api(token, 'GET', f'/repos/{OWNER}/{REPO}', missing_ok=True)
    if existing is None:
        created = api(token, 'POST', '/user/repos', {'name': REPO, 'description': '系统设计：从一台服务器开始 · 八章连载技术小说与静态阅读网站', 'private': False, 'homepage': f'https://{OWNER}.github.io/{REPO}/', 'auto_init': False})
        print('Created '+created['html_url'], flush=True)
    else:
        assert existing['full_name'] == f'{OWNER}/{REPO}'
        assert not existing['private'], 'Refusing to change repository visibility.'
    if not (ROOT / '.git').exists():
        subprocess.run(['git', 'init', '-b', 'main', str(ROOT)], check=True, capture_output=True)
        git(ROOT, 'config', 'core.autocrlf', 'false')
        git(ROOT, 'remote', 'add', 'origin', remote_url)
    assert git(ROOT, 'remote', 'get-url', 'origin') == remote_url
    commit(ROOT, ['.'], 'Create eight-chapter system design reader with SVG architecture diagrams')
    git(ROOT, 'push', '-u', 'origin', 'main')
    pages = api(token, 'GET', f'/repos/{OWNER}/{REPO}/pages', missing_ok=True)
    settings = {'build_type': 'legacy', 'source': {'branch': 'main', 'path': '/docs'}}
    if pages is None:
        pages = api(token, 'POST', f'/repos/{OWNER}/{REPO}/pages', settings)
    elif pages.get('source') != settings['source'] or pages.get('build_type') == 'workflow':
        pages = api(token, 'PUT', f'/repos/{OWNER}/{REPO}/pages', settings)
    print('Pages configured: '+pages['html_url'], flush=True)


def publish_integration():
    repos = [('ai-era-reader', 'main'), ('pytorch-apprentice', 'main'), ('data-empire-reader', 'main'), ('rag-empire-reader', 'main'), ('bookshelf', 'master')]
    # Validate all destinations before the first push. Never force-push.
    for name, branch in repos:
        path = WORKSPACE / name
        remote = 'wupzl.github.io' if name == 'bookshelf' else name
        assert git(path, 'remote', 'get-url', 'origin') == f'https://github.com/{OWNER}/{remote}.git'
        assert git(path, 'branch', '--show-current') == branch
        git(path, 'fetch', 'origin')
        assert git(path, 'rev-parse', 'HEAD') == git(path, 'rev-parse', f'origin/{branch}'), f'{name}: local and remote heads have diverged'
    for name, branch in repos:
        path = WORKSPACE / name
        paths = ['index.html', 'bookshelf.css', 'README.md', 'verify.py', '.github/workflows/verify-readers.yml'] if name == 'bookshelf' else [str(p.relative_to(path)).replace('\\', '/') for p in (path / 'docs').glob('*.html')]
        if (path / 'build.py').exists():
            paths.append('build.py')
        commit(path, paths, 'Add system design reader to learning bookshelf navigation')
        git(path, 'push', 'origin', branch)
        print(f'Published {name}', flush=True)


def status(token):
    for name in ('system-design-reader', 'ai-era-reader', 'pytorch-apprentice', 'data-empire-reader', 'rag-empire-reader', 'wupzl.github.io'):
        pages = api(token, 'GET', f'/repos/{OWNER}/{name}/pages', missing_ok=True)
        runs = api(token, 'GET', f'/repos/{OWNER}/{name}/actions/runs?per_page=4')
        print(json.dumps({'repository': name, 'pages': {k: pages.get(k) for k in ('status', 'html_url', 'source')} if pages else None, 'runs': [{'name': r['name'], 'status': r['status'], 'conclusion': r['conclusion'], 'url': r['html_url'], 'head_sha': r['head_sha'][:8]} for r in runs['workflow_runs']]}, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['reader', 'integration', 'status'])
    args = parser.parse_args()
    token = credentials()
    assert api(token, 'GET', '/user')['login'] == OWNER, 'Unexpected GitHub account'
    if args.action == 'reader':
        publish_reader(token)
    elif args.action == 'integration':
        publish_integration()
    else:
        status(token)


if __name__ == '__main__':
    main()
