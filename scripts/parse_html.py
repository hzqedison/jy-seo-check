"""解析 HTML 的 SEO 标签，返回结构化 dict + 自动标注的 issues 列表。"""
import re

# 出现在 H1 里通常意味着 H1 被误用于面包屑/导航的词
NAV_WORDS = {"home", "blog", "games", "game issues", "support", "category",
             "首页", "博客", "支持", "分类", "游戏"}


def _attr(tag, name):
    m = re.search(name + r'="([^"]*)"', tag, re.I)
    return m.group(1) if m else None


def parse(html):
    r, issues = {}, []

    t = re.search(r'<title[^>]*>(.*?)</title>', html, re.S)
    r["title"] = t.group(1).strip() if t else None
    if not r["title"]:
        issues.append("缺 <title>")

    d = (re.search(r'<meta[^>]*name="description"[^>]*content="([^"]*)"', html, re.I)
         or re.search(r'<meta[^>]*content="([^"]*)"[^>]*name="description"', html, re.I))
    r["description"] = d.group(1).strip() if d else None
    if not r["description"]:
        issues.append("缺 meta description")

    # canonical
    r["canonical"] = None
    for link in re.findall(r'<link[^>]*?>', html):
        if (_attr(link, "rel") or "").lower() == "canonical":
            r["canonical"] = _attr(link, "href")
    if not r["canonical"]:
        issues.append("缺 canonical")

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

    r["issues"] = issues
    return r


if __name__ == "__main__":
    import sys, json
    html = open(sys.argv[1], encoding="utf-8", errors="replace").read()
    print(json.dumps(parse(html), ensure_ascii=False, indent=2))
