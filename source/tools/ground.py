"""L9 引用對照檢查（grounding check）

對 Wiki 中每一條有來源的重點：
  1. 依 [環學xx §區塊N mm:ss] 找出 raw 裡那個時間點開頭的段落
  2. 把重點和段落都切成「中文雙字組」（bigram）
  3. 重疊率 = 重點的雙字組中，有出現在段落裡的比例
重疊率太低 → 這句話可能不是出自它引用的那一段（錯誤歸因、混用別集、LLM 自己的話），
列出來給人工確認。這是「提示」不是「判決」：改寫得很口語的正確句子也可能分數偏低。

用法：py -X utf8 tools/ground.py [門檻=0.4] [輸出報告路徑]
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "wiki"
RAW = ROOT / "raw"

SRC_RE = re.compile(r"\[(環學[0-9A-Z]+(?:重製)?)([^\]]*)\]")
EP_RE = re.compile(r"(環學[0-9A-Z]+(?:重製)?)")
BLOCK_RE = re.compile(r"§(區塊[一二三四五六七八九十]+)")
TIME_RE = re.compile(r"\b(\d{2}:\d{2})\b")
TAG_RE = re.compile(r"〔(文本|考據|推測)〕")
CJK = re.compile(r"[一-鿿]")


def bigrams(s):
    chars = [c for c in s if CJK.match(c)]
    return {chars[i] + chars[i + 1] for i in range(len(chars) - 1)}


def load_raw():
    return {p.stem.split("_")[0]: p.read_text(encoding="utf-8").splitlines() for p in RAW.glob("*.md")}


def segment(lines, block, ts):
    """回傳 raw 中 [block] 區塊裡、以時間點 ts 開頭的那一段（到下一個同層小標為止）。"""
    start, end = 0, len(lines)
    if block:
        for i, l in enumerate(lines):
            if l.startswith("### ") and block in l:
                start = i
                for j in range(i + 1, len(lines)):
                    if lines[j].startswith("### "):
                        end = j
                        break
                break
    for i in range(start, end):
        l = lines[i]
        if f"（{ts}" in l or f"({ts}" in l:
            out = [l]
            for j in range(i + 1, end):
                if lines[j].startswith("  - **") or lines[j].startswith("###"):
                    break
                out.append(lines[j])
            return "\n".join(out)
    return None


def claim_text(line):
    t = re.sub(r"\[\[([^\]]+)\]\]", r"\1", line)  # 先拆 [[連結]]，避免被當成來源方括號
    t = SRC_RE.sub("", t)
    t = TAG_RE.sub("", t)
    t = re.sub(r"→ 見.*", "", t)  # 「→ 見 [[頁面]]」是導覽，不算內容
    return t


def main():
    threshold = float(sys.argv[1]) if len(sys.argv) > 1 else 0.4
    raws = load_raw()
    rows, missing = [], []
    for path in sorted(WIKI.rglob("*.md")):
        if path.parent.name == "sources" or path.name in ("index.md", "log.md"):
            continue
        rel = path.relative_to(ROOT).as_posix()
        for ln, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not (line.lstrip().startswith("- ") and TAG_RE.search(line) and SRC_RE.search(line)):
                continue
            segs = []
            for m in SRC_RE.finditer(line):
                ep, block = None, None
                for part in re.split(r"[；;]", m.group(0).strip("[]")):
                    if (e := EP_RE.search(part)):
                        ep = e.group(1)
                    if (b := BLOCK_RE.search(part)):
                        block = b.group(1)
                    for ts in TIME_RE.findall(part):
                        s = segment(raws.get(ep, []), block, ts)
                        if s is None:
                            missing.append((rel, ln, f"{ep} {block} {ts}"))
                        else:
                            segs.append(s)
            cb = bigrams(claim_text(line))
            if len(cb) < 6 or not segs:  # 太短的句子（例如表格上方的標題句）不具判斷意義
                continue
            sb = set().union(*(bigrams(s) for s in segs))
            score = len(cb & sb) / len(cb)
            rows.append((score, rel, ln, claim_text(line).strip()[:60]))

    rows.sort()
    low = [r for r in rows if r[0] < threshold]
    out = [f"# L9 引用對照檢查（門檻 {threshold}）",
           f"檢查重點數：{len(rows)}　低於門檻：{len(low)}　找不到對應段落：{len(missing)}", ""]
    if low:
        out.append("## 低重疊（需人工確認）")
        out += [f"- {s:.2f} `{rel}:{ln}` {txt}" for s, rel, ln, txt in low]
        out.append("")
    if missing:
        out.append("## 找不到引用的段落（時間點不是段落開頭，或區塊寫錯）")
        out += [f"- `{rel}:{ln}` {what}" for rel, ln, what in missing]
        out.append("")
    import statistics
    if rows:
        out.append(f"分數分布：最低 {rows[0][0]:.2f}／中位數 {statistics.median(r[0] for r in rows):.2f}／最高 {rows[-1][0]:.2f}")
    text = "\n".join(out)
    print(text)
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
