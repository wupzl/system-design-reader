# 系统设计：从一台服务器开始

八章连载技术小说。跟随林默与架构师老周，从一台服务器出发，理解缓存、数据库、消息队列与分布式共识。第九章“分布式事务”仅保留预告。

- [在线阅读](https://wupzl.github.io/system-design-reader/)
- [全书 Markdown 导航](chapters/00-全书导航.md)
- [学习书架](https://wupzl.github.io/)
- [整理说明与技术参考](EDITORIAL.md)

手机和桌面阅读、章内目录、上下章切换、字号调整、纯白/米白/深色背景。八张本地 SVG 架构图，其余字符图支持横向滚动。无需登录，没有运行时 CDN、框架或后端依赖。

## 本地构建与预览

```bash
python -m pip install -r requirements.txt
python build.py
python -m http.server 4175 --directory docs --bind 127.0.0.1
```

打开 http://127.0.0.1:4175/。返回学习书架与切换项目使用线上站点的根路径；跨项目本地验证请在父目录运行 `python bookshelf/verify.py`。

## 更新连载

维护 `chapters/01.md` 等正文和 `book.json`，然后运行 `python build.py`。生成的网站文件位于 `docs/`。原稿位于 `source/original.md`，构建不会改写原稿或正文。`scripts/import_source.py` 与 `scripts/create_diagrams.py` 记录首次整理过程，不属于日常构建。

新增章节时，同时更新 `book.json`、首页连载说明、下一章预告及学习书架的章节数。所有页面保留返回书架与六项目切换入口。

## 验证

```bash
python -m pip install -r requirements-test.txt
python -m playwright install chromium
python verify.py
```

检查全文与原稿存档、章节数、资源及锚点、SVG 可访问名称、手机和桌面布局、字号与三种主题持久化、上下章跳转和第九章预告。截图位于 `test-results/`。GitHub Actions 还检查重建不会产生未提交差异。

## 发布

GitHub Pages 从 `main` 分支的 `/docs` 发布，线上地址为 https://wupzl.github.io/system-design-reader/ 。


项目切换菜单已接入 [Agent 帝国：代码审判者](https://wupzl.github.io/coding-agent-reader/)，九章小说式 Coding Agent 工程阅读。


项目切换菜单已接入 [面试官的审判](https://wupzl.github.io/interview-proof-reader/)，七章技术面试小说与七组本地训练，第八章待续。


项目切换菜单已接入 [LangChain 帝国](https://wupzl.github.io/langchain-empire-reader/)，五章正文，第六章待续。
