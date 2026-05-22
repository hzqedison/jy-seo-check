# PageSpeed Insights API Key 申请教程

> jy-seo-check 的性能诊断（Core Web Vitals：LCP/CLS/INP + Lighthouse 分数）调用 Google PageSpeed Insights API。本教程手把手带你拿到免费 key。约 5 分钟。

## 为什么需要

- **不填 key**：也能跑，但用的是 Google 匿名共享配额，**很容易报 `Quota exceeded`**（实测当天就会被限），且性能只能退回 `curl` 测 TTFB。
- **填了 key**：**每天 25,000 次**，个人/小团队完全够用，**免费、无需绑卡**。

## 前提

- 一个 Google 账号（Gmail 即可）。
- **不需要**信用卡 / 计费账户。

## 步骤

### 1. 打开 Google Cloud Console
访问 → https://console.cloud.google.com/
首次进入会让你同意服务条款，勾选同意、选所在国家。

### 2. 新建一个项目
- 顶部蓝色导航栏左侧有个**项目下拉**（可能显示 "My First Project"）→ 点它 → **新建项目 / New Project**
- 项目名随便填，比如 `seo-tools` → **创建 / Create**
- 等几秒，再用顶部下拉**切到这个新项目**（重要，别建在别的项目下）

### 3. 启用 PageSpeed Insights API
- 左上角 **☰ 菜单** → **API 和服务 / APIs & Services** → **库 / Library**
- 搜索框输入：`PageSpeed Insights API`
- 点开同名结果 → 点蓝色 **启用 / Enable**
- 等它启用完成（几秒）

### 4. 创建 API Key
- 左侧菜单 **API 和服务 / APIs & Services** → **凭据 / Credentials**
- 顶部 **+ 创建凭据 / Create Credentials** → 选 **API 密钥 / API key**
- 弹窗会显示一串密钥，形如 `AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX` → 点**复制**
- （建议）点弹窗里的 **编辑 API 密钥 / Edit API key** → "API 限制 / API restrictions" → 选 **限制密钥 / Restrict key** → 只勾 **PageSpeed Insights API** → 保存。这样即使泄露也只能用于这一个 API，更安全。

### 5. 填进 jy-seo-check（二选一）

**方式 A — 配置文件（推荐）**
在 skill 目录里把 `config.env.example` 复制成 `config.env`，把 key 填到等号后面：
```
PAGESPEED_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

**方式 B — 环境变量**
```bash
# macOS / Linux / Git-Bash
export PAGESPEED_API_KEY=AIzaSy...
# Windows PowerShell（永久）
setx PAGESPEED_API_KEY "AIzaSy..."
```
（脚本优先读环境变量，其次读 config.env。）

### 6. 验证是否生效
在 skill 目录跑：
```bash
python scripts/pagespeed.py https://example.com mobile
```
- 看到 `LCP_ms / INP_ms / CLS / lighthouse_score` 有数值 → ✅ 成功。
- 返回 `error` 含 **"API key not valid"** → key 没复制全，或第 3 步 API 没启用。
- 返回 `error` 含 **"Quota exceeded"** → key 没被读到（检查文件名是否正好叫 `config.env`、或环境变量是否生效）。

## 常见问题

| 问题 | 答案 |
|---|---|
| 要钱吗？ | 不要。PageSpeed Insights API 免费，25,000 次/天。 |
| 要绑信用卡吗？ | 不需要。 |
| key 泄露了？ | 到 Credentials 删除或重建，旧 key 立即失效。 |
| 不想申请？ | 可不填，skill 自动降级：只测 TTFB；LCP/CLS/INP 从 Google Search Console「核心网页指标」报告手动看。 |
| 团队怎么用？ | 每人各自申请自己的 key（别共用，免得一个被限影响所有人）。 |
| key 放进 git 了怎么办？ | `config.env` 已被 `.gitignore` 忽略；若不慎提交，先在云端删除该 key 再重建。 |
