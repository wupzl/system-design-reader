"""One-time, explicit import. build.py only reads maintained chapters/, never this script."""
from pathlib import Path
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / 'systemdesign.md'
for folder in ('source', 'chapters', 'assets', 'assets/diagrams'):
    (ROOT / folder).mkdir(exist_ok=True)
if list((ROOT / 'chapters').glob('[0-9][0-9].md')):
    raise SystemExit('Maintained chapters already exist; refusing to overwrite them.')
shutil.copyfile(SOURCE, ROOT / 'source/original.md')
source = SOURCE.read_text(encoding='utf-8')
starts = list(re.finditer(r'^## 第[一二三四五六七八]章：([^\n]+)', source, re.M))
assert len(starts) == 8
topics = [
    '容量估算 · 负载均衡 · 水平扩展',
    '共享会话 · 旁路缓存 · 缓存故障',
    '日志复制 · 读写分离 · 故障转移',
    '数据分片 · 一致性哈希 · 全局 ID',
    '削峰填谷 · 可靠投递 · 消费幂等',
    '限流算法 · 熔断降级 · 故障隔离',
    'DNS · CDN · 多地域与容灾',
    'CAP · 多数派 · Raft · 栅栏令牌',
]


def replace_once(text, old, new):
    assert old in text, f'Missing editorial target: {old[:70]}'
    return text.replace(old, new, 1)


def note(text):
    return '\n\n> **工程补充**：' + text + '\n\n'


chapters = []
for index, match in enumerate(starts):
    number = index + 1
    title = match[1].strip()
    body = source[match.end():starts[index+1].start() if index < 7 else len(source)]
    # Work outside fences so command examples and graph content remain untouched.
    chunks = re.split(r'(```[^\n]*\n.*?```)', body, flags=re.S)
    for k in range(0, len(chunks), 2):
        value = chunks[k]
        value = re.sub(r'^# 《系统设计：从一台服务器开始》\s*$', '', value, flags=re.M)
        value = re.sub(r'^下一章[。．]?\s*$', '', value, flags=re.M)
        value = re.sub(r'^# (第[一二三四五六七八]章结束[^\n]*)', r'## \1', value, flags=re.M)
        value = re.sub(r'^# ([一二三四五六七八九十百]+、[^\n]+)', r'## \1', value, flags=re.M)
        value = re.sub(r'^# 《([^\n]+)》', r'### 下一章：\1', value, flags=re.M)
        value = re.sub(r'^# ', '### ', value, flags=re.M)
        chunks[k] = value
    body = ''.join(chunks).strip()
    if number == 1:
        body = replace_once(body, '每秒请求数。', '在本书的 Web 场景中，用它表示每秒请求数；数据库语境中的 QPS 则通常指每秒查询数。')
        body = replace_once(body, '“现在性能翻倍。”', '“现在有机会分担更多请求。”')
        body = replace_once(body, '压力被分散。', '压力被分散。实际吞吐提升还取决于数据库、网络、负载均衡器和请求分布，并不保证随机器数量线性增长。')
    if number == 2:
        body = replace_once(body, '结果完全一样。', '在 Redis 可用且会话未过期的前提下，两台应用能够查询同一份会话状态。')
        body = replace_once(body, '越往前：\n\n```text\n更快\n更贵\n容量更小\n```\n\n越往后：\n\n```text\n更慢\n更便宜\n容量更大\n```', '这和内存层级的思路相似：尽量把热门数据放在离使用者更近的位置。不过，浏览器、CDN、Redis 与数据库的延迟、容量和成本取决于实际部署，不能直接套用 CPU 缓存的价格与容量关系。')
        body = replace_once(body, '但用很小的空间，可以表示海量数据。', '但用很小的空间，可以表示海量数据。' + note('“一定不存在”针对的是已经加入且未被错误删除的集合。若新增记录还没同步到过滤器，就可能误挡真实数据；需要设计更新顺序、故障回退和重建机制。缓存空值也应使用可区分的占位值，并设置短 TTL。'))
        old = '''if (redis.get(key) == null) {

    if (tryLock(key)) {

        data = db.query();

        redis.set(key, data);

        unlock(key);

    } else {

        sleep(50);

        retry();
    }
}'''
        new = '''// 示意代码：具体 API 由 Redis 客户端与业务实现提供
for (int attempt = 0; attempt < MAX_RETRIES; attempt++) {
    data = cache.get(key);
    if (data != null) return data;

    token = randomUniqueToken();
    if (tryLock(lockKey, token, LOCK_TTL)) {
        try {
            data = cache.get(key); // 获锁后再次检查
            if (data == null) {
                data = db.query();
                cache.set(key, encodeNullIfNeeded(data), CACHE_TTL);
            }
            return data;
        } finally {
            compareAndDelete(lockKey, token); // 原子校验归属再释放
        }
    }
    boundedBackoff(attempt);
}
return fallbackOrReject();'''
        body = replace_once(body, old, new)
        body = replace_once(body, '互斥锁 / 分布式锁。', '互斥锁 / 分布式锁。' + note('锁的创建和 TTL 设置必须原子完成，释放时需原子比较唯一 token，避免删掉别人的锁。租约过期仍可能产生并发执行；缓存重建允许怎样的重复、是否需要版本控制，要按业务确定。涉及严格资源写入时，还要考虑第八章的栅栏令牌。'))
    if number == 3:
        body = replace_once(body, '然后从库获取这些日志，再重放。', '然后从库获取这些日志，再重放。这里的 SQL 用来说明变化；binlog 可以采用语句、行或混合格式，行格式记录的是行变化，并不总是保存这条 SQL。')
        body = replace_once(body, '现实中还有各种半同步方案，本质都是在：', 'MySQL 半同步复制等待至少指定数量的副本确认事件已写入并刷盘到 relay log，不要求副本已经执行事务。因此，半同步并不等于读副本没有延迟；等待超时后还可能退回异步复制。故障切换也需要独立的检测、选主、旧主隔离和流量切换机制。\n\n这些方案，本质都是在：')
    if number == 4:
        body = replace_once(body, '### UUID', '### UUID') if '### UUID' in body else body
        body = replace_once(body, '如果把随机 UUID 当 MySQL 主键', '这里主要讨论随机 UUID（例如 v4）；有序 UUID 的索引局部性有所不同。如果把随机 UUID 当 MySQL 主键')
    if number == 5:
        body = replace_once(body, '“消息确实到 Broker 了。”', '“Broker 已按当前确认配置接收了消息；这还不代表消费者已处理成功。”')
        body = replace_once(body, 'Broker：\n\n```text\n“已经 ACK 了，我删掉。”\n```', '对于 RabbitMQ 这类任务队列，Broker 可以把已确认的投递标记为可删除。Kafka 的 offset 提交含义不同：它推进消费位置，消息仍由保留策略管理。')
        body = replace_once(body, '消息保证送到\n但可能重复', '在持久化、确认与重试等条件满足时争取至少处理一次\n可能重复，仍需处理失败、过期与重试耗尽')
        body = replace_once(body, 'Deduplication。', 'Deduplication。' + note('“先查再做再记录”只表达思路，不能单独保证并发幂等。需要唯一约束，并将去重记录和业务更新放在同一个本地事务中；若涉及外部副作用，还需使用对方的幂等键或设计补偿、对账。'))
        body = body.replace('立即返回“抢购成功，处理中”', '返回“请求已受理，订单确认中”')
        body = replace_once(body, '流量在前面就被截断。', '流量在前面就被截断。' + note('Redis 预扣与 MQ 发送不构成跨系统原子事务。发送失败、订单创建失败或支付超时都可能留下预占库存，需要可靠事件记录、幂等补偿、预占超时与对账；受理成功不能直接等同于最终下单成功。'))
    if number == 7:
        body += note('DNS 缓存、健康检查周期和客户端连接会影响实际切换时间。CDN 故障转移与多地域容灾都需要预留容量，并验证数据恢复点（RPO）和恢复时间（RTO）。')
    if number == 8:
        body = replace_once(body, '性能\n可用性\n复杂度\n```\n\n都会非常高。', '协调成本与复杂度上升\n延迟可能增加\n分区期间的可用性可能下降\n```\n\n都需要重新权衡。')
        body = replace_once(body, '确认，\n\n就认为它成立。', '按照同一协议和版本规则确认，\n\n才可能把它认定为已提交。不能只数相同值的副本数量，就推断已经获得一致性。')
        body = replace_once(body, '这给一致性提供了基础。', '这给一致性提供了基础。交集本身还不够，必须结合版本、投票限制、日志新旧比较和提交规则，才能排除冲突历史。')
        body = replace_once(body, '于是这条日志可以进入提交状态。', '对于当前任期的日志条目，在满足 Raft 提交规则后，就可以推进提交位置。旧任期日志不能仅靠副本计数直接提交，通常要通过提交当前任期条目来间接提交之前的日志；客户端成功响应还应等状态机应用该命令。')
        body = replace_once(body, '于是只有一个合法写入方。', '于是只有能够取得多数派确认的一侧可以继续提交新写入。隔离的旧 Leader 可能暂时仍自认为是 Leader，但无法提交；线性一致读也需要 ReadIndex 等确认机制或满足假设的租约机制，不能直接读任意旧副本。')
        body = replace_once(body, '栅栏令牌。', '栅栏令牌。' + note('令牌应由具有相应一致性保证的机制单调生成，受保护资源必须原子地校验令牌并完成写入。只携带一个数字、只做续租，或者只在应用侧检查，都不足以实现隔离；去重和重试规则也要单独设计。'))
        body = replace_once(body, '### 下一章：订单成功了，库存却没扣——分布式事务', '## 待续：订单成功了，库存却没扣——分布式事务')
        # Keep the preview at the very end; corrections belong with the corresponding passage.
    body = re.sub(r'\n{3,}', '\n\n', body)
    (ROOT / f'chapters/{number:02}.md').write_text(f'# {title}\n\n{body}\n', encoding='utf-8')
    chapters.append({'number': number, 'title': title, 'description': topics[index]})
(ROOT / 'book.json').write_text(json.dumps({'title': '系统设计：从一台服务器开始', 'status': '连载中', 'next': '订单成功了，库存却没扣——分布式事务', 'chapters': chapters}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
for name in ('style.css', 'shelf-nav.css'):
    shutil.copyfile(ROOT.parent / 'ai-era-reader/docs' / name, ROOT / 'assets' / name)
print('Imported 8 complete chapters; source/original.md preserves the original byte for byte.')
