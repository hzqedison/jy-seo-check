---
name: "JY SEO Check"
description: 对任意站点做系统化 SEO 诊断并产出可落地执行的改进方案，支持快照对比再分析。
category: SEO
tags: [seo, audit, analysis, web]
---

加载并执行 **jy-seo-check** skill，对用户的目标站点/材料走 6 环节方法论。

**Input**：`/jy-seo-check` 后的参数 = 域名（如 `example.com`）、或现有诊断材料路径（PPT/Word/PDF）、或需求描述。

**Steps**

1. **加载 skill**：用 Skill 工具加载 `jy-seo-check`，遵循其 `SKILL.md` 与 `references/methodology.md` 的 6 环节。skill 加载后会给出其 base 目录，后续脚本用 `python <skill目录>/scripts/audit.py ...` 运行（不要写死盘符，多设备 D:/K: 通用）。

2. **判断意图**：
   - 给了域名/材料、当前项目无 `.seo-audit/snapshots/` → 首次分析，走环节 1-5。
   - 当前项目已有 `.seo-audit/snapshots/` → 可能是"再分析"：先跑 `audit.py <domain> --compare` 对比上次快照，再聚焦变化（改善/恶化/新问题/已解决）。
   - 没给输入 → 用 **AskUserQuestion** 问：分析哪个站点？有无现成诊断材料？核心目标（流量/排名/收录/转化）？

3. **按 6 环节推进**（按意图裁剪，纯再分析可只走 3+6）：
   1. 苏格拉底澄清 → SPEC（`references/spec-template.md`，一次一问带编号选项）
   2. 读材料（PPT 用 `pptx` skill，**逐图看别跳过**）
   3. 实诊：`python <skill>/scripts/audit.py <domain> --core <行业相关路径>`
   4. 校准（坐实 / 新发现 / 乐观点，标注 `[材料]/[实诊]/[补充]/[质疑]`）
   5. 出方案（`references/plan-template.md`，Quick Wins + Strategic Moves，字段化）
   6. 迭代（落地后回填数据，再分析 `--compare`）

**Guardrails**
- 不基于假设动手，先澄清需求。
- 实诊数据与材料论断交叉验证（材料可能过时）。
- 见效诚实分层 L1(1-4周)/L2(1-3月)/L3(3月+)，不夸大业务转化速度。
- 性能数据需要 `config.env` 或环境变量里的 PageSpeed API key；无 key 时降级（仅 TTFB）。申请见 `docs/api-key-guide.md`。

**参数**：$ARGUMENTS
