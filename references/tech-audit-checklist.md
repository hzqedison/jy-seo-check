# 技术实诊清单

> `audit.py` 自动跑下列项并写入 `findings.json`。本文件供人/AI 对照判断标准。

## 1. 跳转链（redirect）
- 查：`curl -IL`，HTTP 码链 + 跳数。
- 判断：跳数应 ≤1；**302 临时跳转**不应出现在永久路由（权重传递不确定，应 301/308）。
- 常见坑：`站点 → www → /lang → /lang/` 多跳、且中间夹 302。

## 2. robots.txt
- 查：Disallow 规则 + Sitemap 声明。
- 判断：是否误封核心目录；是否屏蔽了应屏蔽的（/api /checkout /user）；**是否漏屏蔽大量低质页**。
- **自动报警**：`Disallow: /` 或 `Disallow: /$` → 屏蔽了首页/全站。

## 3. sitemap
- 查：URL 总数、按路径分类、lastmod 年份、生成器注释。**遇 `<sitemapindex>` 自动递归子 sitemap（最多 25 个）统计真实 URL 总数**，避免把"子 sitemap 数"误当 URL 数。
- 判断：
  - 覆盖率 = sitemap URL 数 / 全站页数（常见低至个位数~两成，说明大量页面未提交）。
  - **lastmod 过期**（停在 N 年前）→ 非自动化生成。
  - 第三方工具注释（xml-sitemaps.com 等）→ 手动生成，建议改自动化。

## 4. 页面 SEO 标签（首页 + 抽样内页）
| 标签 | 判断标准 |
|---|---|
| title | 存在、含核心词、**唯一（多个 → 报警）** |
| meta description | 存在、含关键词、**唯一** |
| canonical | 存在、**唯一（多个 → Google 全忽略）**、**自指比对**（canonical 应等于当前页 URL） |
| meta robots | **不应含 noindex/nofollow**（含 → 丢索引/不传权重） |
| hreflang | x-default **小写**；内页也要有；多站需双向自指一致 |
| **H1** | **每页仅 1 个**；不可用于面包屑/导航（典型坑：内页出现多个 H1，其中数个其实是面包屑层级） |
| H2/H3 | 有合理层级；有 H1 却无 H2 → 模块结构弱 |
| Schema | 按页型齐全：首页 Organization/WebSite/Product/SoftwareApplication（**+AggregateRating 出星级**）；文章页 Article/FAQ/HowTo；**内页常为 0** |
| img | 有意义图配 alt；**显式 width/height**（缺 → CLS 风险）；关键文案不放图里 |
| 内链 | 用真实 `<a href>`；**`onclick` 跳转的伪链接爬虫抓不到/不传权重** |
| 文本密度 | text/HTML 比例过低 + 正文极短 → **CSR 空壳**（核心内容未在首个 HTML，依赖 JS 渲染） |

> 注意校准：首页标签齐全 ≠ 内页齐全。务必抽检内页（材料说"Schema 不足"可能只在内页成立）。

## 4b. HTTP 头 / 索引控制
- **X-Robots-Tag**：HTTP 响应头里的索引限制（HTML meta 之外的来源）。含 noindex/nofollow → 与 meta 同等严重。
- 查：`curl -IL` 看响应头。

## 4c. 反爬 fallback（CDP）
- 首页若是 Cloudflare/WAF 挑战页（"Just a moment" / `challenges.cloudflare.com` / "enable javascript and cookies"）→ curl 被 403/拦截。
- `audit.py` 自动切 `cdp.py`：启正式版 Chrome 独立 profile，等挑战 JS 通过，抓真实 DOM。
- 此时内页/核心页标注「受反爬拦截，存在性需 CDP 验证」而非误报缺失。

## 4d. 渲染对比（`--render`，CDP 双跑，慢）
- **hydration 前后 diff**：SSR 首个 HTML vs 渲染后 DOM，比 H1 数 / canonical / 链接数 —— 抓「客户端脚本改写 canonical」「hydration 后链接锐减」等问题。
- **移动/桌面 DOM diff**：移动 UA vs 桌面，比 H1/链接/正文 —— 抓「移动端删减核心内容」（移动优先索引下会丢内容）。

## 5. 性能 / Core Web Vitals
- 查：`pagespeed.py`（CrUX 真实 + Lighthouse 实验室）；无 key 时退回 `curl` 测 TTFB。
- 阈值（Google）：
  - **TTFB** good <0.8s / poor >1.8s
  - **LCP** good <2.5s / poor >4.0s
  - **INP** good <200ms / poor >500ms
  - **CLS** good <0.1 / poor >0.25
- CrUX overall = SLOW（即 CWV Failed）是直接排名拖累。
- 注意 TTFB 冷热差异大（首访慢、预热快），多测几次。

## 6. 核心场景页 / 工具页存在性
- 查：`--core` 列出的行业相关路径的 HTTP 码。
- 判断：404/000 = 该场景词无着陆页（核心场景未占位的直接证据）。
- 行业相关路径示例（按被测站行业替换）：电商 `category/ product/ deals/`；SaaS `pricing/ features/ integrations/`；工具类 `<核心功能>/ <在线工具>/`。
- 工具页（在线检测/计算类）若全 404 = 可能的重大机会缺口。

## 7. 多站 / 副站
- 副站独立域名时：查其 hreflang 是否回指主站集群 + 自指；性能；Schema。
- 常见坑：副站 hreflang 指向主站集群、却漏掉自身自指 → 双向确认断裂。

## 待补（脚本测不了，需 GSC/GA/付费工具）
- 完整 CWV 历史趋势、全站低质页清单、关键词排名、外链体检（DR/dofollow比/anchor/来源国）。
