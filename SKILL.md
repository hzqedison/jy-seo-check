---
name: jy-seo-check
description: 对任意网站做系统化 SEO 诊断并产出可落地执行的改进方案。当用户要分析/审计某站点的 SEO、诊断 SEO 问题、把现有 SEO 诊断材料(PPT/文档)校准成可执行方案、或在站点改造后对比上次进展做"再分析"时使用。内置实诊脚本(技术体检+性能)与快照对比机制,支持跨站点复用与历史追踪。
---

# jy-seo-check

把"一次性 SEO 分析"变成**可复用、可追踪的长效资产**。对任意站点走同一套严谨流程:澄清需求 → 读材料 → 实时实诊 → 校准 → 出可执行方案 → 滚动迭代,并把每次实诊**存为带日期的快照**,下次自动对比进展。

> 可通过斜杠命令 **`/jy-seo-check <域名|材料|需求>`** 触发,也可在对话里描述需求自动触发。

## 何时用

- 用户要**分析/审计某站点 SEO**(给一个域名,或一份现有诊断材料)。
- 用户已有 SEO 诊断材料(PPT/Word/文档),要**校准成可落地执行的方案**。
- 站点改造**一段时间后再分析**,要对比上次快照看"改善/恶化/新问题/已解决"。

## 核心理念

- **诊断要有实证**:不只信材料里的论断,用实诊脚本拉实时数据交叉验证(材料可能过时)。
- **方案要可落地**:每条建议字段化(谁做/工作量/漏斗节点/预期信号/验证/成本/来源),可分配、可跟踪、可取舍。
- **见效要诚实分层**:技术健康度 1-4 周可见;排名流量 1-3 月;业务转化(下载/付费)3 月+。不拿末端指标考核底座动作。
- **来源要可追溯**:`[材料]` 原诊断 / `[实诊]` 实测 / `[补充]` 新增 / `[质疑]` 不同看法,全程标注。

## 6 环节工作流

> 不必每次都走全 6 环节——按用户意图裁剪。纯"再分析"可直接跳到环节 3+6。

### 1. 苏格拉底式需求澄清 → SPEC
一次问一个问题、带编号选项,直到形成 `references/spec-template.md` 的五章:Problem / Solution / Constraints / Non-goals / Success Criteria。**关键要问清**:交付目的、执行者(SEO 自助 vs 需开发)、核心指标(流量/排名/转化)、时间窗口、Non-goals、数据可得性。

### 2. 读输入材料(如有)
PPT 用 `pptx` skill(`extract-text` + 提取图片逐张看);Word 用 `docx`;PDF 用 `pdf`。**务必读懂每个细节**,图表里的数据(性能数值、关键词、外链结构)往往是论据核心,不要只读文字跳过图。

### 3. 实时实诊
```bash
python scripts/audit.py <domain> [--compare] [--core /p1/,/p2/]
```
一键技术体检:跳转链、robots、sitemap(数量/覆盖/lastmod)、首页+抽样内页的 SEO 标签(title/desc/canonical/hreflang/H1/Schema)、TTFB、核心场景页/工具页存在性、PageSpeed/CWV(需 API key)。结果存为快照(见下)。详细检查项见 `references/tech-audit-checklist.md`。

### 4. 校准(实诊 × 材料)
把实诊结果与材料论断对照,分三类输出:**坐实**(实证确认)/ **新发现**(材料没提)/ **乐观点**(材料说有问题但实诊已不成立——避免误伤)。

### 5. 出方案
按 `references/plan-template.md`:双档优先级(**Quick Wins** 1-4 周 / **Strategic Moves** 1-3 月+),每条字段化。内容型站点参考 `references/topic-cluster-framework.md` 的 Topic Cluster + E-E-A-T 结构。

### 6. 滚动迭代
用户落地一批后回填效果数据 → 重排优先级。再次实诊时 `--compare` 自动对比上次快照。

## 快照与再分析

- 每次 `audit.py` 在**当前工作目录**下写:`.seo-audit/snapshots/<YYYY-MM-DD-HHMM>/`(快照跟项目走,多站互不干扰)。
- 快照含:`findings.json`(结构化诊断)+ raw 文件(html/sitemap)。`.seo-audit/.gitignore` 自动维护(只入库 findings.json)。
- 对比:`python scripts/compare.py [snapshotA] [snapshotB]`;`audit.py --compare` 会自动对比最近两次,输出改善/恶化/新问题/已解决。

## 脚本索引

| 脚本 | 作用 |
|---|---|
| `scripts/audit.py` | 主编排:跑全套体检 → 写快照。`<domain> [--compare] [--pages url1,url2] [--core /p1/,/p2/] [--no-psi]` |
| `scripts/fetch.py` | curl 封装:跳转链/robots/sitemap/页面HTML/TTFB/状态码 |
| `scripts/parse_html.py` | 解析 SEO 标签:title/desc/canonical/hreflang/H1(含面包屑误用)/Schema |
| `scripts/pagespeed.py` | PageSpeed Insights API(读 config.env 或环境变量的 key),解析 CrUX + Lighthouse |
| `scripts/snapshot.py` | 快照读写工具 |
| `scripts/compare.py` | 对比两次快照 → diff |
| `scripts/cdp.py` | **反爬 fallback**:真实 Chrome 绕过 Cloudflare 抓 SEO 标签（audit 检测到挑战页时自动调用，自动启正式版 Chrome 独立 profile）|

> **反爬处理**：audit.py 检测到首页是 Cloudflare/WAF 挑战页（"Just a moment"）时，自动切 `cdp.py` 用真实浏览器抓真实 DOM；内页/核心页标注"受反爬拦截"而非误报缺失。需正式版 Chrome + `pip install websocket-client`。

## references 索引

| 文件 | 何时读 |
|---|---|
| `references/methodology.md` | 需要 6 环节方法论细节、提问清单 |
| `references/spec-template.md` | 环节 1 产出 SPEC |
| `references/plan-template.md` | 环节 5 产出方案(含字段约定) |
| `references/tech-audit-checklist.md` | 环节 3 实诊,逐项查什么、怎么判断 |
| `references/topic-cluster-framework.md` | 内容/电商型站点的 Topic Cluster + E-E-A-T 设计 |

## 配置

- 性能诊断需要 PageSpeed Insights API key。**申请步骤见 [`docs/api-key-guide.md`](docs/api-key-guide.md)**(图文,5 分钟,免费 2.5 万次/天)。
- 配置方式二选一:① 复制 `config.env.example` 为 `config.env` 填入 key;② 设环境变量 `PAGESPEED_API_KEY`。
- 无 key 时自动降级——只用 curl 测 TTFB,LCP/CLS/INP 提示从 GSC「核心网页指标」手动补。

## 依赖

- Python 3 + 系统 `curl`(脚本零第三方依赖)。PPT 解析另需 `pptx` skill。
