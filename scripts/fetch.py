"""HTTP fetch helpers via curl —— 零额外依赖（除系统 curl）。"""
import subprocess, re, os, tempfile

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def _curl(args, timeout=30):
    try:
        r = subprocess.run(
            ["curl", "-sS", "-A", UA, "--max-time", str(timeout)] + args,
            capture_output=True, text=True, timeout=timeout + 8,
            encoding="utf-8", errors="replace")
        return r.stdout or "", r.stderr or "", r.returncode
    except Exception as e:
        return "", str(e), -1


def redirect_chain(url, timeout=30):
    """返回 {'chain': [[code, location], ...], 'final': url, 'hops': n}。"""
    out, _, _ = _curl(["-IL", "-w", "FINAL:%{url_effective}\n", url], timeout)
    chain = []
    for line in out.splitlines():
        m = re.match(r'HTTP/[\d.]+\s+(\d{3})', line)
        if m:
            chain.append([m.group(1), None])
        m = re.match(r'[Ll]ocation:\s*(.+)', line)
        if m and chain:
            chain[-1][1] = m.group(1).strip()
    final = re.search(r'FINAL:(.+)', out)
    redirects = [c for c in chain if c[0].startswith('3')]
    return {"chain": chain, "final": final.group(1).strip() if final else None,
            "hops": len(redirects)}


def ttfb(url, n=2, timeout=30):
    """测 n 次，返回 [{'ttfb','total','size'}, ...]（秒）。"""
    res = []
    fd, tmp = tempfile.mkstemp(); os.close(fd)
    try:
        for _ in range(n):
            out, _, _ = _curl(
                ["-L", "-o", tmp, "-w",
                 "%{time_starttransfer} %{time_total} %{size_download}", url],
                timeout)
            p = out.split()
            if len(p) >= 3:
                res.append({"ttfb": float(p[0]), "total": float(p[1]),
                            "size": int(p[2])})
    finally:
        try: os.unlink(tmp)
        except OSError: pass
    return res


def get(url, timeout=30):
    """跟随跳转，返回页面 HTML 文本。"""
    out, _, _ = _curl(["-L", url], timeout)
    return out


def status(url, timeout=20):
    """不跟随跳转，返回首个 HTTP 状态码字符串。"""
    out, _, _ = _curl(["-o", os.devnull, "-w", "%{http_code}", url], timeout)
    return out.strip()


def status_follow(url, timeout=20):
    """跟随跳转，返回 (最终状态码, 最终url)。"""
    out, _, _ = _curl(["-L", "-o", os.devnull, "-w",
                       "%{http_code} %{url_effective}", url], timeout)
    p = out.strip().split(None, 1)
    return (p[0] if p else "000", p[1] if len(p) > 1 else url)


if __name__ == "__main__":
    import sys, json
    u = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
    print(json.dumps({"redirect": redirect_chain(u), "ttfb": ttfb(u, 1)},
                     ensure_ascii=False, indent=2))
