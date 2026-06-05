"""解析 HTML 的 SEO 标签，返回结构化 dict + 自动标注的 issues 列表。"""
import re

# 出现在 H1 里通常意味着 H1 被误用于面包屑/导航的词
NAV_WORDS = {"home", "blog", "games", "game issues", "support", "category",
             "首页", "博客", "支持", "分类", "游戏"}


def _attr(tag, name):
    m = re.search(name + r'=["\']([^"\']*)["\']', tag, re.I)
    return m.group(1) if m else None


def _host(url):
    m = re.search(r'https?://([^/]+)', url or "")
    return m.group(1) if m else None


def parse(html, page_url=None):
    r, issues = {}, []

    # title（含唯一性）
    titles = re.findall(r'<title[^>]*>(.*?)</title>', html, re.S)
    r["title"] = titles[0].strip() if titles else None
    r["title_count"] = len(titles)
    if not r["title"]:
        issues.append("缺 <title>")
    elif len(titles) > 1:
        issues.append(f"多个 <title>（{len(titles)} 个）")

    # description（含唯一性）
    descs = re.findall(r'<meta[^>]*name=["\']description["\'][^>]*>', html, re.I)
    dvals = [(_attr(m, "content") or "").strip() for m in descs]
    dvals = [d for d in dvals if d]
    r["description"] = dvals[0] if dvals else None
    r["description_count"] = len(dvals)
    if not r["description"]:
        issues.append("缺 meta description")
    elif len(dvals) > 1:
        issues.append(f"多个 meta description（{len(dvals)} 个）")

    # canonical（含唯一性 + 自指比对）
    cans = []
    for link in re.findall(r'<link[^>]*?>', html):
        if (_attr(link, "rel") or "").lower() == "canonical":
            cans.append(_attr(link, "href"))
    r["canonical"] = cans[0] if cans else None
    r["canonical_count"] = len(cans)
    if not cans:
        issues.append("缺 canonical")
    elif len(cans) > 1:
        issues.append(f"多个 canonical（{len(cans)} 个 → Google 会全部忽略）")
    if page_url and r["canonical"]:
        def _norm(u):
            return re.sub(r'^https?://', '', (u or "").rstrip("/")).lower()
        if _norm(r["canonical"]) != _norm(page_url):
            issues.append(f"canonical 非自指（指向 {r['canonical']}，当前 {page_url}）")

    # meta robots noindex/nofollow
    r["meta_robots"] = None
    for m in re.findall(r'<meta[^>]*?>', html):
        if (_attr(m, "name") or "").lower() == "robots":
            r["meta_robots"] = (_attr(m, "content") or "").lower()
    if r["meta_robots"] and ("noindex" in r["meta_robots"] or "nofollow" in r["meta_robots"]):
        issues.append(f"meta robots = {r['meta_robots']}（含 noindex/nofollow，会丢索引/不传权重）")

    # hreflang
    hl = []
    for link in re.findall(r'<link[^>]*?>', html):
        if "hreflang" in link.lower():
            hl.append({"lang": _attr(link, "hreflang"), "href": _attr(link, "href")})
    r["hreflang"] = hl
    r["hreflang_count"] = len(hl)
    langs = [(h["lang"] or "") for h in hl]
    xdefault_present = any(l.lower() == "x-default" for l in langs)
    xdefault_exact = any(l == "x-default" for l in langs)
    if xdefault_present and not xdefault_exact:
        issues.append("x-default 大小写错误（应小写 x-default）")
    if hl and not xdefault_present:
        issues.append("hreflang 缺 x-default")

    # H1
    h1 = [re.sub(r'<[^>]+>', ' ', x).strip() for x in re.findall(r'<h1[^>]*>(.*?)</h1>', html, re.S)]
    h1 = [re.sub(r'\s+', ' ', h) for h in h1 if h]
    r["h1_list"] = h1[:20]
    r["h1_count"] = len(h1)
    if len(h1) > 1:
        issues.append(f"多个 H1（{len(h1)} 个）")
    if len(h1) > 1 and sum(1 for h in h1 if h.lower() in NAV_WORDS) >= 1:
        issues.append("H1 疑似用于面包屑/导航")
        r["h1_breadcrumb_suspect"] = True
    else:
        r["h1_breadcrumb_suspect"] = False
    if r["h1_count"] == 0:
        issues.append("缺 H1")

    # schema
    r["schema_types"] = re.findall(r'"@type"\s*:\s*"([^"]*)"', html)
    r["schema_count"] = len(re.findall(r'application/ld\+json', html))
    if r["schema_count"] == 0:
        issues.append("无结构化数据（JSON-LD）")

    # H2/H3 层级计数
    r["h2_count"] = len(re.findall(r'<h2[\s>]', html, re.I))
    r["h3_count"] = len(re.findall(r'<h3[\s>]', html, re.I))
    if r["h1_count"] >= 1 and r["h2_count"] == 0:
        issues.append("无 H2（标题层级缺失，模块结构弱）")

    # img alt / 显式宽高
    imgs = re.findall(r'<img[^>]*?>', html, re.I)
    r["img_count"] = len(imgs)
    no_dim = sum(1 for im in imgs if not (re.search(r'\bwidth=', im, re.I) and re.search(r'\bheight=', im, re.I)))
    no_alt = sum(1 for im in imgs if not re.search(r'\balt=', im, re.I))
    r["img_without_dimensions"] = no_dim
    r["img_without_alt"] = no_alt
    if imgs and no_dim / len(imgs) > 0.5:
        issues.append(f"{no_dim}/{len(imgs)} 图片缺显式 width/height（CLS 风险）")
    if imgs and no_alt / len(imgs) > 0.5:
        issues.append(f"{no_alt}/{len(imgs)} 图片缺 alt（可访问性/图片 SEO）")

    # 内链统计（站内 <a href>）
    hrefs = re.findall(r'<a[^>]*\shref=["\']([^"\'#]+)["\']', html, re.I)
    internal = [h for h in hrefs if h.startswith("/") or (page_url and _host(page_url) and _host(page_url) in h)]
    r["link_total"] = len(hrefs)
    r["internal_link_count"] = len(internal)
    if r["link_total"] == 0:
        issues.append("页面无可抓取 <a href> 链接（疑似 JS 渲染/onclick 跳转）")

    # onclick 跳转的伪链接（爬虫抓不到，权重不传递）
    onclick_nav = re.findall(r'<(?:div|span|button|li)[^>]*\bonclick=["\'][^"\']*(?:location|href|navigate|router|goto|window\.open|\.push)[^"\']*["\']', html, re.I)
    r["onclick_nav_count"] = len(onclick_nav)
    if onclick_nav and len(onclick_nav) >= 3 and len(onclick_nav) > r["link_total"] * 0.2:
        issues.append(f"{len(onclick_nav)} 处用 onclick 跳转（非 <a href>，爬虫无法抓取/不传权重）")

    # 文本密度（空壳/CSR 检测）：纯文本字符 / HTML 总长
    text = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', html, flags=re.S | re.I)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    r["text_len"] = len(text)
    r["text_ratio"] = round(len(text) / max(len(html), 1), 4)
    if len(html) > 2000 and r["text_ratio"] < 0.05 and r["text_len"] < 500:
        issues.append(f"正文密度极低（text {r['text_len']} 字符/比例 {r['text_ratio']}）→ 疑似 CSR 空壳，核心内容未在首个 HTML")

    r["issues"] = issues
    return r


if __name__ == "__main__":
    import sys, json
    html = open(sys.argv[1], encoding="utf-8", errors="replace").read()
    print(json.dumps(parse(html), ensure_ascii=False, indent=2))
