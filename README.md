# jy-seo-check

可复用的 **SEO 诊断 skill**：对任意网站走一套严谨流程 —— 澄清需求 → 读材料 → 实时实诊 → 校准 → 出可执行方案 → 滚动迭代，并用**快照机制**追踪每次进展。把"一次性 SEO 分析"沉淀成可跨站复用、可版本迭代的长效资产。

## 能力

- **苏格拉底式需求澄清** → 形成 SPEC（五章：Problem/Solution/Constraints/Non-goals/Success）
- **读诊断材料**：PPT / Word / PDF（配合 pptx/docx/pdf skill，逐图逐字）
- **实时技术实诊**（脚本，零第三方依赖）：跳转链 / robots / sitemap 覆盖率 / SEO 标签（title/desc/canonical/hreflang/H1 面包屑误用/Schema）/ TTFB / Core Web Vitals / 核心场景页与工具页存在性
- **实诊 × 材料校准**：坐实 / 新发现 / 乐观点（避免误伤）
- **字段化改进方案**：Quick Wins（1-4 周）+ Strategic Moves（1-3 月+），每条带 负责方/工作量/漏斗节点/预期信号/验证/成本/来源
- **快照对比再分析**：每次实诊存快照，下次自动 diff（改善/恶化/新问题/已解决）

## 安装到一个项目

本 skill 作为**独立 git 仓库**，通过目标仓库的 `.claude/skills.json` + `install-skills.ps1` 安装。

1. 在目标仓库的 `.claude/skills.json` 的 `skills` 数组里加一条：
   ```json
   {
     "name": "jy-seo-check",
     "url": "https://github.com/hzqedison/jy-seo-check.git",
     "targets": [".claude/skills/jy-seo-check"],
     "postInstall": [
       { "description": "同步 /jy-seo-check 命令", "script": "sync-jy-seo-check-commands.ps1" }
     ]
   }
   ```
2. 把 `scripts/sync-jy-seo-check-commands.ps1`（本仓库 `install/` 下提供）放到目标仓库的 `scripts/`。
3. 在目标仓库根目录运行：`.\scripts\install-skills.ps1`
   → 会把 skill clone 到 `.claude/skills/jy-seo-check/`，并把命令同步到 `.claude/commands/jy-seo-check.md`。

> 已发布到 GitHub（公开）：https://github.com/hzqedison/jy-seo-check —— 团队/其他设备可直接 clone 安装。

## 配置 API key（性能诊断需要）

PageSpeed/CWV 需要免费的 Google PageSpeed Insights API key。
**手把手教程见 [`docs/api-key-guide.md`](docs/api-key-guide.md)**（约 5 分钟，免费 2.5 万次/天，无需绑卡）。
配置：复制 `config.env.example` 为 `config.env` 填 key，或设环境变量 `PAGESPEED_API_KEY`。不配则自动降级（仅测 TTFB）。

## 用法

- 斜杠命令：`/jy-seo-check <域名 | 材料路径 | 需求描述>`
- 或自然语言："帮我分析 example.com 的 SEO"
- **再分析**：在已有 `.seo-audit/snapshots/` 的项目里再跑，自动对比上次

直接用脚本（不经 skill）：
```bash
python scripts/audit.py example.com --core "pricing,features,blog" --compare
```

## 目录结构

```
jy-seo-check/
├── SKILL.md                 # 主入口（6 环节 + 触发描述）
├── README.md                # 本文件
├── config.env.example       # API key 模板（复制为 config.env 使用）
├── commands/jy-seo-check.md # /jy-seo-check 斜杠命令
├── docs/api-key-guide.md    # API key 申请教程
├── install/                 # 安装辅助（命令同步脚本）
├── scripts/                 # 实诊脚本（audit/fetch/parse_html/pagespeed/snapshot/compare）
└── references/              # 方法论与模板（methodology/spec/plan/checklist/topic-cluster）
```

## 设计原则

- **诊断有实证**：不轻信材料，实时实诊交叉验证。
- **方案可落地**：每条建议可分配、可跟踪、可取舍。
- **见效诚实分层**：L1 技术(1-4周) / L2 排名流量(1-3月) / L3 业务转化(3月+)，不夸大。
- **不绑定任何具体客户**：只含通用方法论、脚本与模板。
