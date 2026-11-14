"""共用：把 Wiki 頁面解析成「可引用的條目」，並找出每條的標籤。"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "wiki"
TAG_RE = re.compile(r"〔(文本|考據|推測)〕")
SRC_RE = re.compile(r"\[(環學[0-9A-Z]+(?:重製)?)([^\]]*)\]")
SEVERITY = {"文本": 0, "考據": 1, "推測": 2, "爭議": 3}


def pages():
    return {p.stem: p for p in WIKI.rglob("*.md") if p.name not in ("index.md", "log.md")}


def resolve(page_name, find):
    """回傳 (那一行文字, 標籤, 錯誤訊息)。標籤：該行自己的；表格列沿用表格上方或小標的；⚠ 區的衝突條目為「爭議」。"""
    ps = pages()
    if page_name not in ps:
        return None, None, f"Wiki 沒有「{page_name}」這頁"
    lines = ps[page_name].read_text(encoding="utf-8").splitlines()
    hits = [i for i, l in enumerate(lines) if find in l]
    if not hits:
        return None, None, f"「{page_name}」裡找不到：{find}"
    if len(hits) > 1:
        return None, None, f"「{page_name}」裡有 {len(hits)} 行符合，無法唯一定位：{find}"
    i = hits[0]
    line = lines[i]
    indent = len(line) - len(line.lstrip())
    # 有子項目的條目（例如 ⚠ 區的 C1），把縮排較深的子項目一起帶上
    if line.lstrip().startswith("- "):
        for j in range(i + 1, len(lines)):
            l = lines[j]
            if l.strip() and len(l) - len(l.lstrip()) > indent and l.lstrip().startswith("- "):
                line += "\n" + l
            else:
                break
    # 子項目本身沒標籤時，沿用上一層條目的標籤
    if indent > 0 and not TAG_RE.search(lines[i]):
        for j in range(i - 1, -1, -1):
            l = lines[j]
            if l.lstrip().startswith("- ") and len(l) - len(l.lstrip()) < indent:
                pt = TAG_RE.findall(l)
                if pt:
                    return line, max(pt, key=lambda t: SEVERITY[t]), None
                break
    section = ""
    for j in range(i, -1, -1):
        if lines[j].startswith("#"):
            section = lines[j]
            break
    if "⚠" in section:
        return line, "爭議", None
    tags = TAG_RE.findall(line)
    if not tags and line.startswith("|"):
        j = i
        while j > 0 and lines[j - 1].startswith("|"):
            j -= 1
        above = lines[j - 1] if j > 0 else ""
        tags = TAG_RE.findall(above) or TAG_RE.findall(section)
    if not tags:
        return line, None, f"「{page_name}」這一行沒有標籤：{line[:30]}"
    tag = max(tags, key=lambda t: SEVERITY[t])  # 一行多個標籤時取最保守的
    return line, tag, None
