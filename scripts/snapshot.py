"""快照读写。快照存在 <当前工作目录>/.seo-audit/snapshots/<YYYY-MM-DD-HHMM>/。

快照跟项目走：在哪个目录跑，就存到那个目录下，多站互不干扰。
"""
import os, json, datetime, glob


def root():
    return os.path.join(os.getcwd(), ".seo-audit", "snapshots")


def _ensure_gitignore():
    """在 .seo-audit/ 写 .gitignore：保留 findings.json，raw 大文件不入库。"""
    base = os.path.join(os.getcwd(), ".seo-audit")
    os.makedirs(base, exist_ok=True)
    gi = os.path.join(base, ".gitignore")
    if not os.path.exists(gi):
        with open(gi, "w", encoding="utf-8") as f:
            f.write("# seo-check 快照：保留 findings.json 供对比；raw 大文件不入库\n"
                    "*.html\n*.xml\n*.txt\n")


def new_dir():
    _ensure_gitignore()
    ts = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
    d = os.path.join(root(), ts)
    os.makedirs(d, exist_ok=True)
    return d


def save_findings(snapshot_dir, findings):
    with open(os.path.join(snapshot_dir, "findings.json"), "w", encoding="utf-8") as f:
        json.dump(findings, f, ensure_ascii=False, indent=2)


def save_raw(snapshot_dir, name, content):
    p = os.path.join(snapshot_dir, name)
    if isinstance(content, bytes):
        with open(p, "wb") as f:
            f.write(content)
    else:
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)


def list_snapshots():
    return sorted(glob.glob(os.path.join(root(), "*")))


def load_findings(snapshot_dir):
    with open(os.path.join(snapshot_dir, "findings.json"), encoding="utf-8") as f:
        return json.load(f)


def latest_two():
    """返回 (前一个, 最新)；不足两个时前一个为 None。"""
    s = list_snapshots()
    if len(s) >= 2:
        return s[-2], s[-1]
    return None, (s[-1] if s else None)


if __name__ == "__main__":
    for s in list_snapshots():
        print(s)
