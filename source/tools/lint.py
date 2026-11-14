"""Wiki lint：檢查 Wiki 頁面是否符合 CLAUDE.md 的規則。

用法：py -X utf8 tools/lint.py [輸出報告路徑]
檢查項目：
  L1 斷掉的 [[連結]]
  L2 重點沒有〔文本〕〔考據〕〔推測〕標籤
  L3 重點沒有 [環學xx …] 來源
  L4 孤兒頁面（沒有任何頁面連過來）
  L5 〔文本〕引用的「原文」在 raw 裡找不到（可能是捏造或改寫）
  L6 引用的時間點在該集 raw 裡不存在
  L7 出現 raw 裡沒有的英文詞（LLM 自己的知識混進來）
  L10 〔文本〕的條目沒有引文（「」或《》），可能把解讀當成原文
  L8 index.md 和實際頁面不一致（頁面沒列進 index，或 index 列了不存在的頁面）
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI = ROOT / "wiki"
RAW = ROOT / "raw"

TAG_RE = re.compile(r"〔(文本|考據|推測)〕")
SRC_RE = re.compile(r"\[(環學[0-9A-Z]+(?:重製)?)([^\]]*)\]")
EP_RE = re.compile(r"(環學[0-9A-Z]+(?:重製)?)")
LINK_RE = re.compile(r"\[\[([^\]]+)\]\]")
QUOTE_RE = re.compile(r"「([^」]{6,})」")
TIME_RE = re.compile(r"\b(\d{2}:\d{2})\b")
LATIN_RE = re.compile(r"[A-Za-z][A-Za-z'\-]+(?: [A-Z][A-Za-z'\-]+)*")
LATIN_OK = {"DLC", "type", "aliases", "sources", "updated", "raw", "video", "ingested",
            "md", "https", "www", "youtube", "com", "watch", "entity", "concept", "event",
            "source", "Boss", "LLM", "Wiki", "ingest", "vs", "CLAUDE"}
SKIP_SECTIONS = ("相關頁面", "⚠", "這篇產生", "注意", "兩種觀點")


def norm(s: str) -> str:
    return re.sub(r"[\s，。、：；！？「」『』…\.,!?]", "", s)


def load_raw():
    raws = {}
    for p in RAW.glob("*.md"):
        key = p.stem.split("_")[0]  # 例：環學01重製
        raws[key] = p.read_text(encoding="utf-8")
    return raws


def split_front(text):
    if text.startswith("---"):
        end = text.find("\n---", 3)
        return text[3:end], text[end + 4:]
    return "", text


def main():
    raws = load_raw()
    raw_all = "\n".join(raws.values())
    raw_all_norm = norm(raw_all)
    pages = {p.stem: p for p in WIKI.rglob("*.md") if p.name not in ("index.md", "log.md")}
    inbound = {name: 0 for name in pages}
    issues = []

    for name, path in pages.items():
        text = path.read_text(encoding="utf-8")
        front, body = split_front(text)
        rel = path.relative_to(ROOT).as_posix()

        for link in LINK_RE.findall(text):
            if link not in pages:
                issues.append(("L1", rel, f"斷掉的連結 [[{link}]]"))
            elif link != name:
                inbound[link] += 1

        section = ""
        table_tagged = False  # 表格列沿用表格上方那一行（標題或條目）的標籤與來源
        prev = ""
        for ln, line in enumerate(body.splitlines(), 1):
            if line.startswith("|") and not prev.startswith("|"):
                table_tagged = bool(TAG_RE.search(prev) and SRC_RE.search(prev)) or bool(
                    TAG_RE.search(section) and SRC_RE.search(section))
            prev = line if line.strip() else prev
            if line.startswith("#"):
                section = line.lstrip("# ").strip()
                continue
            if line.startswith("|") and table_tagged:
                continue
            is_claim = (line.startswith("- ") or (line.startswith("|") and not set(line) <= set("|-: ")))
            if not is_claim or any(section.startswith(s) for s in SKIP_SECTIONS):
                continue
            if line.startswith("|") and ("來源" in line or "時代" in line and "統治者" in line or "位置" in line or "父系" in line or "區塊 |" in line):
                continue  # 表頭
            if section.startswith("六個區塊") or path.parent.name == "sources":
                continue
            head = line[:40]
            if not TAG_RE.search(line) and not line.rstrip().endswith("："):
                issues.append(("L2", f"{rel}:{ln}", f"沒有標籤：{head}"))
            if TAG_RE.search(line) and not SRC_RE.search(line):
                issues.append(("L3", f"{rel}:{ln}", f"沒有來源：{head}"))
            # L10：〔文本〕必須真的引用文本
            if "〔文本〕" in line and not re.search(r"[「《]", line):
                issues.append(("L10", f"{rel}:{ln}", f"〔文本〕卻沒有引文：{head}"))
            # L5：〔文本〕的引號內容要能在 raw 找到
            if "〔文本〕" in line:
                for q in QUOTE_RE.findall(line):
                    for frag in re.split(r"……|…", q):
                        f = norm(frag)
                        if len(f) >= 4 and f not in raw_all_norm:
                            issues.append(("L5", f"{rel}:{ln}", f"引文在 raw 找不到：「{frag}」"))
            # L6：時間點要存在於所引的那一集
            for m in SRC_RE.finditer(line):
                # 一個方括號裡可能有多集：[環學01重製 §區塊四 19:50；環學03 §區塊三 18:15]
                ep = None
                for seg in re.split(r"[；;]", m.group(0).strip("[]")):
                    em = EP_RE.search(seg)
                    if em:
                        ep = em.group(1)
                    src_text = raws.get(ep)
                    if src_text is None:
                        issues.append(("L6", f"{rel}:{ln}", f"引用了不存在的來源 {ep}"))
                        continue
                    for t in TIME_RE.findall(seg):
                        if t not in src_text:
                            issues.append(("L6", f"{rel}:{ln}", f"{ep} 中沒有時間點 {t}"))

        # L7：英文詞必須出現在 raw
        scan = re.sub(r"(video|raw): .*", "", front) + "\n" + body
        for w in set(LATIN_RE.findall(scan)):
            if w in LATIN_OK or w.lower() in LATIN_OK or "http" in w:
                continue
            if w not in raw_all:
                issues.append(("L7", rel, f"raw 中沒有的英文詞：{w}"))

    index_links = set(LINK_RE.findall((WIKI / "index.md").read_text(encoding="utf-8")))
    for name in pages:
        if name not in index_links:
            issues.append(("L8", pages[name].relative_to(ROOT).as_posix(), "沒有列在 index.md"))
    for name in index_links - set(pages):
        issues.append(("L8", "wiki/index.md", f"列了不存在的頁面 [[{name}]]"))

    for name, n in inbound.items():
        if n == 0 and pages[name].parent.name != "sources":
            issues.append(("L4", pages[name].relative_to(ROOT).as_posix(), "孤兒頁面"))

    issues.sort()
    lines = [f"# Lint 報告", f"頁面數：{len(pages)}　問題數：{len(issues)}", ""]
    for code in ("L1", "L2", "L3", "L4", "L5", "L6", "L7", "L8", "L10"):
        group = [i for i in issues if i[0] == code]
        if group:
            lines.append(f"## {code}（{len(group)}）")
            lines += [f"- `{loc}` {msg}" for _, loc, msg in group]
            lines.append("")
    out = "\n".join(lines)
    print(out)
    if len(sys.argv) > 1:
        Path(sys.argv[1]).write_text(out, encoding="utf-8")


if __name__ == "__main__":
    main()
