#!/usr/bin/env python3
"""对比两次快照的 findings.json → 已解决 / 新问题 / 指标变化。

用法:
  python compare.py [snapshotA] [snapshotB]   # 不传则自动取最近两份
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import snapshot

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def _ttfb(f):
    return f.get("homepage", {}).get("ttfb_avg")


def _smc(f):
    return f.get("sitemap", {}).get("url_count")


def diff(prev_dir, cur_dir, print_out=True):
    prev = snapshot.load_findings(prev_dir)
    cur = snapshot.load_findings(cur_dir)
    pi, ci = set(prev.get("issues", [])), set(cur.get("issues", []))
    resolved = sorted(pi - ci)
    new = sorted(ci - pi)
    still = sorted(pi & ci)

    metrics = []
    pt, ct = _ttfb(prev), _ttfb(cur)
    if pt and ct:
        d = "↓改善" if ct < pt else ("↑恶化" if ct > pt else "持平")
        metrics.append(("首页 TTFB(s)", pt, ct, d))
    ps, cs = _smc(prev), _smc(cur)
    if ps and cs:
        d = "↑增" if cs > ps else ("↓减" if cs < ps else "持平")
        metrics.append(("sitemap URLs", ps, cs, d))

    result = {"prev": prev_dir, "cur": cur_dir, "resolved": resolved,
              "new": new, "still_open": still, "metrics": metrics}

    if print_out:
        print("\n===== 快照对比 =====")
        print(f"上次: {os.path.basename(prev_dir)}   本次: {os.path.basename(cur_dir)}")
        print(f"\n✅ 已解决 ({len(resolved)}):")
        for x in resolved:
            print("  -", x)
        print(f"\n🔴 新问题 ({len(new)}):")
        for x in new:
            print("  -", x)
        print(f"\n⚪ 仍未解决 ({len(still)}):")
        for x in still:
            print("  -", x)
        print("\n📊 指标变化:")
        for name, a, b, d in metrics:
            print(f"  - {name}: {a} → {b}  {d}")
    return result


if __name__ == "__main__":
    if len(sys.argv) >= 3:
        diff(sys.argv[1], sys.argv[2])
    else:
        prev, cur = snapshot.latest_two()
        if prev:
            diff(prev, cur)
        else:
            print("需要至少两份快照才能对比")
