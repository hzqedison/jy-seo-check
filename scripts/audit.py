#!/usr/bin/env python3
"""seo-check 主编排：对一个 domain 跑全套技术体检 → 写快照。

用法:
  python audit.py <domain> [--compare] [--pages url1,url2] [--core /p1/,/p2/] [--no-psi]

  --compare  跑完自动对比上一份快照
  --pages    指定要抽检的内页完整 URL（逗号分隔）；不传则从 sitemap 自动取样
  --core     要探测存在性的核心场景页/工具页路径（逗号分隔），按行业定制，
             如加速器站: --core /reduce-ping/,/game-booster/,/lag-fix/,/ping-test/
  --no-psi   跳过 PageSpeed（无 key 或想省时）
"""
import sys, os, re, json, argparse
from collections import Counter
sys.path.insert(0, os.path.dirname(__file__))
import fetch, parse_html, pagespeed, snapshot

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

DEFAULT_CORE = ["/blog/", "/about/", "/contact/"]


def norm(domain):
    if not domain.startswith("http"):
        domain = "https://" + domain
    return domain.rstrip("/")


def analyze_sitemap(xml, fetch_fn=None):
    # sitemap-index：递归抓子 sitemap，统计真实 URL 总数（避免把"子 sitemap 数"误当 URL 数）
    if "<sitemapindex" in xml.lower() and fetch_fn:
        subs = re.findall(r'<loc[^>]*>([^<]+)</loc>', xml, re.I)
        total, years, sample = 0, Counter(), []
        for sub in subs[:25]:  # 限 25 个子 sitemap，避免过多请求
            sx = fetch_fn(sub.strip())
            total += len(re.findall(r'<loc[\s>]', sx, re.I))
            years.update(re.findall(r'<lastmod>(\d{4})', sx))
            if len(sample) < 10:
                sample += re.findall(r'<loc[^>]*>([^<]+)</loc>', sx, re.I)[:5]
        return {"url_count": total, "is_index": True, "sub_sitemaps": len(subs),
                "by_path": {}, "lastmod_years": dict(sorted(years.items())),
                "sample_locs": sample[:10]}
    locs = re.findall(r'<loc[^>]*>([^<]+)</loc>', xml, re.I)
    count = len(re.findall(r'<loc[\s>]', xml, re.I))  # 最稳计数（等价 grep -c）

    def seg(u):
        m = re.search(r'https?://[^/]+/(?:[a-z-]{2,5}/)?([^/]*)', u, re.I)
        return m.group(1) if m and m.group(1) else "(root)"
    by_path = dict(Counter(seg(u) for u in locs).most_common(15))
    years = dict(sorted(Counter(re.findall(r'<lastmod>(\d{4})', xml)).items()))
    gen = re.findall(r'<!--\s*(.*?)\s*-->', xml)
    return {"url_count": count, "is_index": False, "by_path": by_path, "lastmod_years": years,
            "generator_comments": gen[:3], "sample_locs": locs[:10]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("domain")
    ap.add_argument("--compare", action="store_true")
    ap.add_argument("--pages", default="")
    ap.add_argument("--core", default="")
    ap.add_argument("--no-psi", action="store_true")
    a = ap.parse_args()

    base = norm(a.domain)
    F = {"domain": base, "issues": []}

    # 1 跳转链
    rc = fetch.redirect_chain(base)
    F["redirect"] = rc
    if rc["hops"] >= 2:
        F["issues"].append(f"跳转链 {rc['hops']} 跳（建议≤1）")
    if any(c[0] == "302" for c in rc["chain"]):
        F["issues"].append("跳转链含 302 临时跳转（权重传递不确定）")
    final = rc["final"] or base
    core_base = final.rstrip("/")

    # 2 robots
    robots = fetch.get(base + "/robots.txt")
    sm_decl = re.findall(r'(?im)^\s*Sitemap:\s*(.+)$', robots)
    F["robots"] = {"disallow": re.findall(r'(?im)^\s*Disallow:\s*(.+)$', robots)[:20],
                   "sitemaps": [s.strip() for s in sm_decl]}

    # 3 sitemap
    sm_url = sm_decl[0].strip() if sm_decl else base + "/sitemap.xml"
    sm = fetch.get(sm_url)
    if "<loc" in sm.lower() or "<sitemap" in sm.lower():
        F["sitemap"] = analyze_sitemap(sm, fetch.get); F["sitemap"]["url"] = sm_url
        yrs = F["sitemap"]["lastmod_years"]
        if yrs and max(yrs) < "2025":
            F["issues"].append(f"sitemap lastmod 最新仅 {max(yrs)}（疑过期）")
    else:
        F["sitemap"] = {"error": "无法获取/解析", "url": sm_url}

    # 4 首页（curl；遇反爬挑战页自动切 CDP 真实浏览器）
    home = fetch.get(final)
    low = home.lower()
    antibot = ("just a moment" in low or "challenges.cloudflare.com" in low
               or "cf-browser-verification" in low or "enable javascript and cookies" in low)
    F["antibot"] = antibot
    if antibot:
        F["issues"].append("[反爬] 检测到 Cloudflare/WAF 挑战页，curl 被拦 → 切 CDP 真实浏览器")
        import cdp
        cres = cdp.fetch(final)
        if cres.get("title"):
            home_seo = cres
            F["via"] = "CDP"
            if cres.get("sitemap") and F.get("sitemap", {}).get("error"):
                F["sitemap"] = cres["sitemap"]; F["sitemap"]["via"] = "CDP"
        else:
            F["issues"].append(f"[反爬] CDP 抓取失败: {cres.get('error', '?')}（需手动启动 Chrome 调试）")
            home_seo = parse_html.parse(home)
    else:
        home_seo = parse_html.parse(home)
    tt = fetch.ttfb(final, 2)
    F["homepage"] = {"url": final, "ttfb_samples": tt, "seo": home_seo}
    for i in home_seo.get("issues", []):
        F["issues"].append(f"[首页] {i}")
    if tt:
        avg = round(sum(x["ttfb"] for x in tt) / len(tt), 3)
        F["homepage"]["ttfb_avg"] = avg
        if avg > 0.8:
            F["issues"].append(f"[首页] TTFB {avg}s 偏慢（good<0.8s）")

    # 5 抽样内页
    inner = [p.strip() for p in a.pages.split(",") if p.strip()]
    if not inner and F["sitemap"].get("sample_locs"):
        cand = [u for u in F["sitemap"]["sample_locs"] if "/blog/" in u or "/article" in u]
        inner = (cand or F["sitemap"]["sample_locs"])[:1]
    F["inner_pages"] = []
    if antibot:
        F["issues"].append("[反爬] 内页 curl 被拦，未抽检内页标签（如需用 CDP 逐页抓）")
    else:
        for u in inner[:3]:
            seo = parse_html.parse(fetch.get(u))
            F["inner_pages"].append({"url": u, "seo": seo})
            tag = u.rstrip("/").rsplit("/", 1)[-1][:30]
            for i in seo["issues"]:
                F["issues"].append(f"[内页:{tag}] {i}")

    # 6 核心页/工具页存在性（含软 404 检测：站点对不存在路径是否也返回 200）
    soft404 = (not antibot) and fetch.status(core_base + "/__seocheck404probe__/") == "200"
    F["soft404"] = soft404
    if soft404:
        F["issues"].append("[软404] 站点对不存在路径也返回 200（SPA/软404）→ 核心页 200 不代表真实存在，需看页面内容")
    def _clean_core(p):
        p = p.strip().strip("/")
        # 修复 Git-Bash(MSYS)对前导斜杠路径的自动转换，如 C:/Program Files/Git/reduce-ping
        if "Program Files" in p or re.match(r'^[A-Za-z]:', p):
            p = p.rsplit("/", 1)[-1]
        return p
    core = [_clean_core(p) for p in a.core.split(",") if p.strip()] or [c.strip("/") for c in DEFAULT_CORE]
    F["core_pages"] = []
    for p in core:
        url = core_base + "/" + p + "/"
        code = fetch.status(url)
        note = "(软404存疑)" if (code == "200" and soft404) else ""
        F["core_pages"].append({"path": "/" + p + "/", "url": url, "status": code, "note": note})
        if code in ("404", "410", "000"):
            F["issues"].append(f"核心页缺失: /{p}/ ({code})")
        elif code == "403" and antibot:
            F["issues"].append(f"核心页 /{p}/ 受反爬拦截(403)，存在性需 CDP 验证")

    # 7 PageSpeed
    if not a.no_psi:
        F["pagespeed"] = {"mobile": pagespeed.run(final, "mobile"),
                          "desktop": pagespeed.run(final, "desktop")}
        for s in ("mobile", "desktop"):
            ps = F["pagespeed"][s]
            if "error" in ps:
                continue
            lcp_cat = ps.get("field", {}).get("LCP_ms", {}).get("cat")
            if ps.get("crux_overall") == "SLOW" or lcp_cat == "SLOW":
                F["issues"].append(f"[性能:{s}] CWV/LCP 不佳（{ps.get('crux_overall')}）")

    # 存快照
    sd = snapshot.new_dir()
    snapshot.save_raw(sd, "homepage.html", home)
    snapshot.save_raw(sd, "sitemap.xml", sm)
    snapshot.save_raw(sd, "robots.txt", robots)
    snapshot.save_findings(sd, F)

    # 摘要
    print(f"\n===== seo-check: {base} =====")
    print(f"快照: {sd}")
    print(f"跳转: {rc['hops']} 跳 → {final}")
    print(f"sitemap: {F['sitemap'].get('url_count', '?')} URLs  lastmod_years={F['sitemap'].get('lastmod_years', {})}")
    print(f"首页 TTFB: {F['homepage'].get('ttfb_avg', '?')}s")
    print(f"核心页: " + ", ".join(f"{c['path']}={c['status']}" for c in F["core_pages"]))
    print(f"\n问题清单 ({len(F['issues'])}):")
    for i in F["issues"]:
        print("  -", i)

    if a.compare:
        prev, cur = snapshot.latest_two()
        if prev:
            import compare
            compare.diff(prev, cur, print_out=True)
        else:
            print("\n(无上一份快照可对比)")


if __name__ == "__main__":
    main()
