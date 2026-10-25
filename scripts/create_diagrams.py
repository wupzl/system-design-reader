"""Draw portable SVGs and replace selected character diagrams once, preserving text alternatives."""
from pathlib import Path
import html
import re

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'assets/diagrams'
OUT.mkdir(exist_ok=True)


def box(x, y, label, sub='', width=160):
    return f'<g><rect x="{x}" y="{y}" width="{width}" height="72" rx="9" fill="#f4f8f5" stroke="#b0c9b9"/><text x="{x+width/2}" y="{y+29}" text-anchor="middle" fill="#244f3d" font-size="16" font-weight="600">{html.escape(label)}</text><text x="{x+width/2}" y="{y+53}" text-anchor="middle" fill="#52685b" font-size="12">{html.escape(sub)}</text></g>'


def line(x1, y1, x2, y2, label='', dashed=False):
    dash = ' stroke-dasharray="6 5"' if dashed else ''
    result = f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="#507f63" stroke-width="2" marker-end="url(#arrow)"{dash}/>'
    if label:
        result += f'<text x="{(x1+x2)/2}" y="{(y1+y2)/2-10}" text-anchor="middle" fill="#52685b" font-size="12" paint-order="stroke" stroke="#fff" stroke-width="5">{html.escape(label)}</text>'
    return result


def drawing(slug, title, desc, shapes, height=370):
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 720 {height}" role="img" aria-labelledby="title desc">
<title id="title">{html.escape(title)}</title><desc id="desc">{html.escape(desc)}</desc>
<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10Z" fill="#507f63"/></marker></defs>
<rect width="720" height="{height}" rx="12" fill="#fff"/>
<g font-family="system-ui,Microsoft YaHei,sans-serif"><text x="30" y="38" fill="#244f3d" font-size="20" font-weight="700">{html.escape(title)}</text>
<text x="30" y="65" fill="#52685b" font-size="12">{html.escape(desc)}</text>{shapes}</g></svg>'''
    (OUT / f'{slug}.svg').write_text(svg + '\n', encoding='utf-8')


figures = [
    (1, 'load-balancing', '把请求分给多台应用服务器', '负载均衡分配请求；增加应用实例仍需关注共享依赖的容量。',
     box(30, 185, '用户', '同一个访问入口', 130)+box(250, 185, '负载均衡器', '轮询 / 其他策略')+''.join(box(530,y,f'App {i+1}','可替换的应用实例') for i,y in enumerate((95,185,275)))+line(160,221,250,221)+''.join(line(410,221,530,y+36) for y in (95,185,275)),
     lambda t: '用户 → LB' in t and 'Server A' in t, 370),
    (2, 'shared-session', '把会话状态移出应用内存', '两台应用读取同一份会话；应用实例不再独占登录状态。',
     box(30,180,'负载均衡器','请求可以进入任意实例')+box(280,110,'App A','不在本机保存会话')+box(280,250,'App B','不在本机保存会话')+box(530,180,'Redis','共享会话 / 设置 TTL')+line(190,216,280,146)+line(190,216,280,286)+line(440,146,530,216)+line(440,286,530,216),
     lambda t: '用户 → LB' in t and 'Redis' in t, 370),
    (3, 'read-write-routing', '读写分离：路由与复制是两条路径', '写入和强一致要求的读取走主库；允许延迟的读取可走副本。',
     box(30,180,'App','按读写需求路由')+box(280,110,'Primary','写入 / 必要的读取')+box(280,250,'Replica','允许复制延迟的读取')+box(530,110,'binlog','源库变更日志')+box(530,250,'relay log','接收后按顺序应用')+line(190,216,280,146,'写 / 读')+line(190,216,280,286,'读')+line(440,146,530,146)+line(610,182,610,250,'复制')+line(530,286,440,286,'应用'),
     lambda t: 'DB Router' in t and 'Master' in t, 370),
    (4, 'database-sharding', '数据分片：先找到数据，再访问分片', '分片键决定路由；同一分片可以再配置自己的主库与副本。',
     box(30,185,'App','携带 user_id 等分片键')+box(280,185,'分片路由','按路由规则定位')+''.join(box(530,y,f'DB {i}','保存部分业务数据') for i,y in enumerate((95,185,275)))+line(190,221,280,221)+''.join(line(440,221,530,y+36) for y in (95,185,275)),
     lambda t: ('DB0' in t or 'DB 0' in t or 'DB_0' in t) and len(t)>80, 370),
    (5, 'queue-buffering', '用消息队列缓冲瞬时流量', '受理、可靠投递与最终业务成功，是需要分别确认的阶段。',
     box(30,110,'请求入口','限流 / 校验')+box(280,110,'库存预占','原子操作 / 过期回收')+box(530,110,'MQ','确认 / 持久化 / 重试')+box(530,260,'Consumer','控制并发 / 幂等处理')+box(280,260,'数据库','业务事务 / 最终状态')+box(30,260,'查询结果','已受理 ≠ 已成单')+line(190,146,280,146)+line(440,146,530,146)+line(610,182,610,260)+line(530,296,440,296)+line(280,296,190,296),
     lambda t: 'Redis 原子扣减库存' in t and 'MQ' in t, 380),
    (6, 'circuit-breaker', '熔断器的三个状态', '熔断减少持续故障的放大；恢复由受控探测决定。',
     box(30,170,'Closed · 关闭','正常放行并统计失败')+box(280,170,'Open · 打开','快速失败 / 使用降级')+box(530,170,'Half-open · 半开','放行少量探测请求')+line(190,206,280,206,'达到阈值')+line(440,206,530,206,'等待窗口到期')+line(610,242,610,300)+line(610,300,110,300,'探测成功：恢复关闭')+line(110,300,110,242)+line(610,170,610,110)+line(610,110,360,110,'探测失败：重新打开')+line(360,110,360,170),
     lambda t: all(x in t.lower() for x in ('closed','open','half')), 360),
    (7, 'cdn-cache', '让静态资源靠近读者', '命中边缘缓存时直接响应；未命中时按配置回源并缓存。',
     box(30,185,'浏览器','先检查本地缓存')+box(280,185,'CDN 边缘节点','接近访问者的缓存')+box(530,185,'源站','静态资源 / 应用服务')+line(190,221,280,221,'请求')+line(440,221,530,221,'未命中时回源')+line(610,257,610,310)+line(610,310,360,310,'回源内容按缓存策略存储')+line(360,310,360,257),
     lambda t: 'CDN' in t and ('源站' in t or 'Origin' in t) and len(t)>70, 370),
    (8, 'raft-majority', '多数派确认，让提交的历史保持一致', '三节点示意：当前任期日志经多数派确认并满足规则后提交。',
     box(30,180,'Client','发送命令 / 等待应用')+box(280,180,'Leader A','当前任期日志')+box(530,110,'Follower B','持久化日志并确认')+box(530,250,'Follower C','允许暂时落后')+line(190,216,280,216)+line(440,216,530,146,'复制')+line(440,216,530,286,'复制',True)+line(530,182,440,242,'B 确认')+'<text x="280" y="335" fill="#244f3d" font-size="13">A + B = 2 / 3；选举、日志新旧与任期规则同样必要。</text>',
     lambda t: 'Client' in t and '多数节点确认' in t, 370),
]

for chapter, slug, title, desc, shapes, matches, height in figures:
    drawing(slug, title, desc, shapes, height)
    path = ROOT / f'chapters/{chapter:02}.md'
    content = path.read_text(encoding='utf-8')
    image = f'![{title}](../assets/diagrams/{slug}.svg)'
    if image in content:
        continue
    fences = list(re.finditer(r'```text\n(.*?)```', content, flags=re.S))
    candidates = [m for m in fences if matches(m[1])]
    if candidates:
        match = candidates[0]
        replacement = image + '\n\n<details class="original-diagram" markdown="1">\n<summary>查看文字版示意</summary>\n\n' + match[0] + '\n\n</details>'
        # Correct the read router's original drawing as well as the visual version.
        if slug == 'read-write-routing':
            replacement = image + '\n\n<details class="original-diagram" markdown="1">\n<summary>查看文字版示意</summary>\n\n```text\nApp → DB Router ── 写 / 必要的读 ─→ Primary\n                └─ 允许延迟的读 ─→ Replica\nPrimary ── binlog 复制 / relay log 应用 ─→ Replica\n```\n\n</details>'
        content = content[:match.start()] + replacement + content[match.end():]
    else:
        # Put a figure at the first related section, keeping all existing examples.
        anchors = {4: '## 七、', 6: '### 熔断', 7: '### CDN'}
        target = anchors.get(chapter)
        position = content.find('\n\n', content.find(target)) if target and target in content else content.find('\n\n')
        content = content[:position] + '\n\n' + image + content[position:]
    path.write_text(content, encoding='utf-8')
    print(f'{chapter:02}: {slug} (replaced {len(candidates)>0})')
