"""PageSpeed Insights —— 读 config.env 的 API key，返回 CWV（CrUX 真实 + Lighthouse 实验室）。"""
import os, sys, json, subprocess, urllib.parse

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _load_key():
    # 优先环境变量，其次 config.env
    env = os.environ.get("PAGESPEED_API_KEY")
    if env:
        return env.strip()
    cfg = os.path.join(os.path.dirname(__file__), "..", "config.env")
    try:
        for line in open(cfg, encoding="utf-8"):
            line = line.strip()
            if line.startswith("PAGESPEED_API_KEY="):
                return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return ""


def _g(d, *keys, default=None):
    for k in keys:
        if isinstance(d, dict) and k in d:
            d = d[k]
        else:
            return default
    return d


def _extract(j, strategy):
    le = j.get("loadingExperience", {})
    m = le.get("metrics", {})
    def fld(k):
        x = m.get(k, {})
        return {"p75": x.get("percentile"), "cat": x.get("category")}
    score = _g(j, "lighthouseResult", "categories", "performance", "score")
    aud = _g(j, "lighthouseResult", "audits", default={})
    return {
        "strategy": strategy,
        "crux_overall": le.get("overall_category", "NO_FIELD_DATA"),
        "field": {
            "LCP_ms": fld("LARGEST_CONTENTFUL_PAINT_MS"),
            "INP_ms": fld("INTERACTION_TO_NEXT_PAINT"),
            "CLS": fld("CUMULATIVE_LAYOUT_SHIFT_SCORE"),
            "FCP_ms": fld("FIRST_CONTENTFUL_PAINT_MS"),
            "TTFB_ms": fld("EXPERIENCE_TIME_TO_FIRST_BYTE"),
        },
        "lighthouse_score": round(score * 100) if isinstance(score, (int, float)) else None,
        "lab": {a: _g(aud, a, "displayValue") for a in
                ["largest-contentful-paint", "total-blocking-time",
                 "cumulative-layout-shift", "first-contentful-paint", "speed-index"]},
    }


def run(url, strategy="mobile", timeout=90):
    key = _load_key()
    api = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    params = {"url": url, "strategy": strategy, "category": "performance"}
    if key:
        params["key"] = key
    full = api + "?" + urllib.parse.urlencode(params)
    try:
        r = subprocess.run(["curl", "-sS", "--max-time", str(timeout), full],
                           capture_output=True, text=True, timeout=timeout + 10,
                           encoding="utf-8", errors="replace")
        j = json.loads(r.stdout)
    except Exception as e:
        return {"error": str(e), "has_key": bool(key)}
    if "error" in j:
        return {"error": _g(j, "error", "message", default="unknown"),
                "has_key": bool(key),
                "hint": "无 key 易触发匿名限额；在 config.env 配 PAGESPEED_API_KEY"}
    return _extract(j, strategy)


if __name__ == "__main__":
    import sys
    u = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    s = sys.argv[2] if len(sys.argv) > 2 else "mobile"
    print(json.dumps(run(u, s), ensure_ascii=False, indent=2))
