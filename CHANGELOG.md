# Changelog

记录 AI Signal 面向用户的变更。每日的 feed 数据更新（`Feed update` commit）不在此列。

## 2026-07-05

### 新增

- 播客人物追踪：27 位 AI 关键人物（海外高管/分析师 20 人 + 中国 AI 一线 7 人）作为**嘉宾**上任何播客/访谈都会被抓到，不再限于 13 个订阅频道。每天用 yt-dlp 在 YouTube 全网按"人名 + interview/访谈 + 年份"搜索，命中并入 `feed-podcasts.json`（带 `person` 字段，中国人物带 `region: "cn"`），字幕、摘要、日报管道零改动复用。
  之所以这样改：RSS 频道只覆盖主持人自己发布的节目；高管上别人节目（往往是信息量最大的场合）此前完全漏掉。
  过滤规则（保证与频道内容同等质量）：标题必须含人名（最干净的同名假阳性过滤）、时长 ≥ 15 分钟（去切片/shorts；实测 20 分钟会漏掉 19 分钟的正式大会演讲）、剔除例行盘面播报与影视合集标题、与频道 RSS 命中的同一期自动去重；已入 feed 的命中在 7 天窗口内保留，不受搜索排名波动影响。
  名单在 `config/sources.json` 的 `podcasts.people`，新增 `--people-only` 参数可单独刷新人物搜索。

### 修复

- `skill.md` 更名为 `SKILL.md`，符合 Agent Skills 规范的大写文件名。
  之所以这样改：Linux 环境（多数云端 Agent）文件名大小写敏感，小写文件名可能导致 Agent 找不到 skill 定义、只能照 README 即兴引导——实测 WorkBuddy 安装时漏问了推送时间。
- Onboarding 加硬规则：Step 2-6 逐条问、不许跳过；即使 Agent 自己不能定时，也必须问推送时间并存入配置。
- 平台检测从"只认 OpenClaw"改为按定时能力判断：WorkBuddy 等自带定时任务的持久 Agent 走与 OpenClaw 同级的自动推送路径（Step 6 / Step 8 新增对应分支）。
- 补 Windows 适配说明：bash 片段需换成 PowerShell 等价写法；Python 脚本本身跨平台（UTF-8 强制、无硬编码路径）。

### 新增

- feed 拉取加多源镜像：GitHub raw 不可达时自动切换 jsDelivr CDN，全部失败才落本地缓存。大陆无代理用户从此每天能正常收到更新；也可用 `AI_SIGNAL_BASE_URLS` 环境变量自定义镜像列表。
  之所以这样改：raw.githubusercontent.com 在大陆基本不可达，此前无代理用户装上后每天拉取都会失败、只能吃旧缓存。
- README 与 skill.md 补国内安装路径：clone 失败时用 gh-proxy 类镜像加速前缀。
- X/Twitter 抓取加入主题过滤：节日祝福、生活动态、纯社交回复等非 AI 信号不再进入 feed。
  之所以这样改：7 月 4 日美国国庆的刷屏推挤占了 feed 位额。
- 过滤关键词用当日真实 feed 校准：覆盖主流模型名（Claude / Fable / GPT / Gemini 等）、AIE、CLI 等一线语汇，宁可多留不错杀，互动排序兜底。

### 改进

- 日报每条内容带稳定编号（推文 X1/X2、播客 P1/P2、论文 Paper1），追问时直接说"展开 P2"、"详细讲讲 Paper1"即可。

### 文档

- 新增本 CHANGELOG 与 README「最近更新」段。

## 2026-07-04

### 修复

- 用户安装依赖瘦身：`requirements.txt` 只剩 `httpx[socks]`；中央抓取依赖（twscrape 等）移到 `requirements-central.txt`。
  之所以这样改：新用户在 macOS 系统 Python 3.9 上装 twscrape 直接失败；SOCKS 代理环境缺 socksio 时，远端 feed 拉取会静默回退到本地缓存。
- 定时任务恢复每日刷新中央摘要缓存（feed-summaries.json 此前停更了三天）。

### 改进

- manifest 新增 `feed_sources`：标注每个 feed 来自远端还是本地缓存、是否过期，Agent 可如实提示用户。
- 日报支持播客深读展开（"展开第 2 个播客"），有全文字幕时优先读 transcript。

## 2026-07-03

### 修复

- 已读标记改为「日报确认展示 / 送达后」才写入 seen.json，生成或推送失败不再吞掉用户没看过的内容。

## 2026-07-02

### 新增

- 播客无公开字幕时的 ASR 转录兜底（火山引擎），并拒绝把 show notes 误当成 transcript。
