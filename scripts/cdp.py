"""CDP fallback —— 用真实 Chrome 绕过反爬（Cloudflare 等）抓 SEO 标签。

自动启动正式版 Chrome 独立 profile 调试实例（不影响用户日常 Chrome），导航目标 URL，
等待反爬挑战 JS 通过，再用 CDP Runtime.evaluate 抓 DOM。返回与 parse_html.parse() 兼容的 dict。

依赖：正式版 Chrome + websocket-client（pip install websocket-client）。
用法：python cdp.py <url>
"""
import sys, os, json, time, subprocess, urllib.request, urllib.parse
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PORT = 9222
PROFILE = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "seo-cdp-chrome")


def _chrome_path():
    for p in [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
              os.path.join(os.environ.get("LOCALAPPDATA", ""), r"Google\Chrome\Application\chrome.exe")]:
        if os.path.exists(p):
            return p
    return None


def _alive():
    try:
        urllib.request.urlopen(f"http://localhost:{PORT}/json/version", timeout=3)
        return True
    except Exception:
        return False


def ensure_chrome():
    """9222 没有调试实例则启动正式版 Chrome 独立 profile（与用户日常 Chrome 隔离）。"""
    if _alive():
        return True
    cp = _chrome_path()
    if not cp:
        return False
    subprocess.Popen([cp, f"--remote-debugging-port={PORT}", "--remote-allow-origins=*",
                      f"--user-data-dir={PROFILE}", "about:blank"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(12):
        time.sleep(1.5)
        if _alive():
            return True
    return False


def fetch(url, wait=12):
    """用 CDP 抓 url，返回与 parse_html.parse() 兼容的 dict（含 issues / via=CDP）。"""
    if not url.startswith("http"):
        url = "https://" + url
    if not ensure_chrome():
        return {"error": "无法启动/连接 Chrome 调试实例（CDP）", "issues": ["CDP 不可用"]}
    try:
        from websocket import create_connection
    except ImportError:
        return {"error": "缺 websocket-client：pip install websocket-client", "issues": []}

    req = urllib.request.Request(f"http://localhost:{PORT}/json/new?{urllib.parse.quote(url, safe='')}", method="PUT")
    try:
        tab = json.load(urllib.request.urlopen(req, timeout=10))
    except Exception as e:
        return {"error": f"创建 tab 失败: {e}", "issues": []}

    time.sleep(wait)  # 等反爬挑战 JS（Cloudflare "Just a moment"）自动通过

    try:
        ws = create_connection(tab["webSocketDebuggerUrl"], suppress_origin=True, timeout=20)
    except Exception as e:
        return {"error": f"WebSocket 连接失败: {e}", "issues": []}

    _id = [0]
    def send(method, params=None):
        _id[0] += 1
        ws.send(json.dumps({"id": _id[0], "method": method, "params": params or {}}))
        while True:
            m = json.loads(ws.recv())
            if m.get("id") == _id[0]:
                return m
    def ev(expr, await_promise=False):
        r = send("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": await_promise})
        return r.get("result", {}).get("result", {}).get("value")

    r = {}
    r["url"] = ev("location.href")
    r["title"] = ev("document.title")
    r["description"] = ev("(document.querySelector('meta[name=description]')||{}).content||null")
    r["canonical"] = ev("(document.querySelector('link[rel=canonical]')||{}).href||null")
    h1 = ev("Array.from(document.querySelectorAll('h1')).map(function(h){return h.innerText.trim()}).filter(Boolean)") or []
    r["h1_list"] = h1[:20] if isinstance(h1, list) else []
    r["h1_count"] = len(h1) if isinstance(h1, list) else 0
    hl = ev("Array.from(document.querySelectorAll('link[hreflang]')).map(function(l){return l.getAttribute('hreflang')})") or []
    r["hreflang"] = [{"lang": x, "href": None} for x in hl] if isinstance(hl, list) else []
    r["hreflang_count"] = len(r["hreflang"])
    st = ev("Array.from(document.querySelectorAll('script[type=\"application/ld+json\"]')).reduce(function(a,s){try{var j=JSON.parse(s.textContent);(Array.isArray(j)?j:[j]).forEach(function(x){if(x&&x['@type'])a.push(x['@type'])})}catch(e){}return a},[])") or []
    r["schema_types"] = st if isinstance(st, list) else []
    r["schema_count"] = len(r["schema_types"])
    # sitemap（同源 fetch，带反爬通过后的 cookie）
    sm = ev("fetch('/sitemap.xml').then(function(x){return x.text()}).then(function(t){return JSON.stringify({loc:(t.match(/<loc/g)||[]).length, sitemaps:(t.match(/<sitemap>/g)||[]).length, years:Array.from(new Set((t.match(/<lastmod>\\d{4}/g)||[]).map(function(y){return y.slice(9)}))).sort()})}).catch(function(){return null})", True)
    r["sitemap"] = json.loads(sm) if sm else None
    ws.close()

    issues = []
    if not r["title"]: issues.append("缺 <title>")
    if not r["description"]: issues.append("缺 meta description")
    if not r["canonical"]: issues.append("缺 canonical")
    if r["h1_count"] > 1: issues.append(f"多个 H1（{r['h1_count']} 个）")
    if r["h1_count"] == 0: issues.append("缺 H1")
    if r["schema_count"] == 0: issues.append("无结构化数据（JSON-LD）")
    langs = [h.get("lang", "") or "" for h in r["hreflang"]]
    if any(l.lower() == "x-default" for l in langs) and not any(l == "x-default" for l in langs):
        issues.append("x-default 大小写错误（应小写）")
    r["issues"] = issues
    r["via"] = "CDP"
    return r


# 提取关键 SEO 节点的指纹（用于 hydration / 移动桌面 diff）
_FINGERPRINT_JS = r"""(function(){
  function txt(s){return Array.from(document.querySelectorAll(s)).map(function(e){return (e.innerText||'').trim()}).filter(Boolean)}
  return {
    h1: txt('h1'),
    h2_count: document.querySelectorAll('h2').length,
    title: document.title,
    canonical: (document.querySelector('link[rel=canonical]')||{}).href||null,
    robots: (document.querySelector('meta[name=robots]')||{}).content||null,
    links: Array.from(document.querySelectorAll('a[href]')).map(function(a){return a.getAttribute('href')}).filter(function(h){return h&&h.indexOf('#')!==0}).length,
    text_len: (document.body?document.body.innerText.length:0)
  }
})()"""

MOBILE_UA = ("Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36")


def _open_and_fingerprint(create_connection, url, wait, mobile_ua=None):
    """开 tab、（可选）设移动 UA、等渲染、返回关键节点指纹 + tabId。"""
    req = urllib.request.Request(f"http://localhost:{PORT}/json/new?{urllib.parse.quote(url, safe='')}", method="PUT")
    tab = json.load(urllib.request.urlopen(req, timeout=10))
    ws = create_connection(tab["webSocketDebuggerUrl"], suppress_origin=True, timeout=20)
    _id = [0]
    def send(method, params=None):
        _id[0] += 1
        ws.send(json.dumps({"id": _id[0], "method": method, "params": params or {}}))
        while True:
            m = json.loads(ws.recv())
            if m.get("id") == _id[0]:
                return m
    if mobile_ua:
        send("Network.setUserAgentOverride", {"userAgent": mobile_ua})
        send("Page.navigate", {"url": url})
    time.sleep(wait)
    r = send("Runtime.evaluate", {"expression": _FINGERPRINT_JS, "returnByValue": True})
    fp = r.get("result", {}).get("result", {}).get("value")
    ws.close()
    try:
        urllib.request.urlopen(f"http://localhost:{PORT}/json/close/{tab['id']}", timeout=5)
    except Exception:
        pass
    return fp


def compare_render(url, ssr_html=None, wait=8):
    """③ hydration 前后 diff + ⑤ 移动/桌面 DOM diff。
    返回 {hydration, mobile_desktop, issues}。ssr_html 传入 curl 拿的首个 HTML 做 hydration 对比。"""
    if not url.startswith("http"):
        url = "https://" + url
    out = {"issues": []}
    if not ensure_chrome():
        return {"error": "CDP 不可用", "issues": []}
    try:
        from websocket import create_connection
    except ImportError:
        return {"error": "缺 websocket-client", "issues": []}

    # 桌面渲染后指纹
    try:
        desktop = _open_and_fingerprint(create_connection, url, wait)
    except Exception as e:
        return {"error": f"桌面渲染抓取失败: {e}", "issues": []}
    out["rendered_desktop"] = desktop

    # ③ hydration：SSR 首个 HTML vs 渲染后 DOM
    if ssr_html is not None and desktop:
        import parse_html
        ssr = parse_html.parse(ssr_html, url)
        h1_ssr, h1_dom = ssr.get("h1_count", 0), len(desktop.get("h1") or [])
        can_ssr = (ssr.get("canonical") or "").rstrip("/")
        can_dom = (desktop.get("canonical") or "").rstrip("/")
        hy = {"h1_ssr": h1_ssr, "h1_rendered": h1_dom,
              "canonical_ssr": ssr.get("canonical"), "canonical_rendered": desktop.get("canonical"),
              "links_ssr": ssr.get("link_total"), "links_rendered": desktop.get("links")}
        out["hydration"] = hy
        if can_ssr and can_dom and can_ssr != can_dom:
            out["issues"].append(f"hydration 后 canonical 被改写（SSR {ssr.get('canonical')} → 渲染后 {desktop.get('canonical')}）")
        if h1_ssr >= 1 and h1_dom != h1_ssr:
            out["issues"].append(f"hydration 后 H1 数量变化（SSR {h1_ssr} → 渲染后 {h1_dom}）")
        if (ssr.get("link_total") or 0) > 0 and desktop.get("links", 0) < (ssr.get("link_total") or 0) * 0.5:
            out["issues"].append(f"hydration 后链接锐减（SSR {ssr.get('link_total')} → 渲染后 {desktop.get('links')}）")

    # ⑤ 移动 vs 桌面 DOM 差异
    try:
        mobile = _open_and_fingerprint(create_connection, url, wait, mobile_ua=MOBILE_UA)
    except Exception as e:
        mobile = None
        out["issues"].append(f"移动端抓取失败: {e}")
    if mobile and desktop:
        out["rendered_mobile"] = mobile
        dh, mh = len(desktop.get("h1") or []), len(mobile.get("h1") or [])
        if dh >= 1 and mh == 0:
            out["issues"].append("移动端缺 H1（桌面有，移动优先索引下会丢主主题）")
        dl, ml = desktop.get("links", 0), mobile.get("links", 0)
        if dl > 0 and ml < dl * 0.5:
            out["issues"].append(f"移动端链接远少于桌面（桌面 {dl} → 移动 {ml}，疑似移动端删减核心内链）")
        dt, mt = desktop.get("text_len", 0), mobile.get("text_len", 0)
        if dt > 500 and mt < dt * 0.5:
            out["issues"].append(f"移动端正文远少于桌面（桌面 {dt} → 移动 {mt} 字符，疑似移动端删减核心内容）")
    return out


if __name__ == "__main__":
    u = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    mode = sys.argv[2] if len(sys.argv) > 2 else "fetch"
    if mode == "compare":
        print(json.dumps(compare_render(u), ensure_ascii=False, indent=2))
    else:
        print(json.dumps(fetch(u), ensure_ascii=False, indent=2))
