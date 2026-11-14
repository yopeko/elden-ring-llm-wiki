"""④ 投影片內容檢查（產生 HTML 之前）

S1 溯源：每一句都要引用 map.json 裡「這張投影片」的 key；沒有引用的句子必須標 "meta": true（簡報自己的說明）
S2 對照：句子 vs 它引用的 Wiki 條目，中文雙字組重疊率 < 門檻 → 可能寫了 Wiki 沒有的東西
S3 術語：每個術語（各張的 defines）第一次出現的投影片，不能早於定義它的那一張
S4 目標：學習目標 1–5 都至少有一張投影片負責
S5 標籤強度：自動帶出〔文本〕的句子必須含引文（「」或《》）；而且任何「」內的字都必須逐字出現在所引的 Wiki 條目

用法：py -X utf8 tools/check_slides.py [門檻=0.3] [輸出報告路徑]
"""
import json
import re
import sys
from pathlib import Path

from wikiparse import ROOT, resolve

CJK = re.compile(r"[一-鿿]")


def bigrams(s):
    c = [x for x in s if CJK.match(x)]
    return {c[i] + c[i + 1] for i in range(len(c) - 1)}


def plain(s):
    return re.sub(r"<[^>]+>", "", s)


def claims(slide):
    """列出一張投影片裡所有「有內容的句子」：(文字, 引用 keys, meta)"""
    out = []
    for key in ("items", "intro", "levels", "eras", "steps", "bands"):
        for it in slide.get(key, []):
            out.append((it["t"], it.get("r", []), it.get("meta", False)))
    for key in ("left", "right"):
        if key in slide:
            out.append((slide[key]["t"], slide[key]["r"], False))
    for q in slide.get("qs", []):
        out.append((q["a"], q["r"], False))
    return out


def main():
    th = float(sys.argv[1]) if len(sys.argv) > 1 else 0.3
    content = json.loads((ROOT / "slides" / "content.json").read_text(encoding="utf-8"))
    mp = json.loads((ROOT / "slides" / "map.json").read_text(encoding="utf-8"))
    s1, s2, s3, s4, s5, scores = [], [], [], [], [], []

    order = [s["id"] for s in content["slides"]]
    defined_at = {}
    for s in content["slides"]:
        for term in s.get("defines", []):
            defined_at[term] = order.index(s["id"])

    first_seen = {}
    for idx, s in enumerate(content["slides"]):
        sid = s["id"]
        refs = mp.get(sid, {}).get("refs", {})
        texts = []
        for text, rkeys, meta in claims(s):
            texts.append(plain(text))
            if not rkeys:
                if not meta:
                    s1.append(f"- `{sid}` 沒有引用也沒標 meta：{plain(text)[:30]}")
                continue
            ref_lines, tags = [], []
            for k in rkeys:
                if k not in refs:
                    s1.append(f"- `{sid}` 引用了對照表裡沒有的 key：{k}")
                    continue
                line, tag, err = resolve(*refs[k])
                if err:
                    s1.append(f"- `{sid}/{k}` {err}")
                else:
                    ref_lines.append(line)
                    tags.append(tag)
            if tags and all(tg == "文本" for tg in tags) and not re.search(r"[「《]", text):
                s5.append(f"- `{sid}` 標成〔文本〕卻沒有引文：{plain(text)[:40]}")
            # 引號內的字必須逐字出現在所引的 Wiki 條目（不能「改寫過的引文」）
            joined_refs = "".join(ref_lines)
            for q in re.findall(r"「([^」]{4,})」", plain(text)):
                for frag in re.split(r"……|…", q):
                    if len(frag) >= 4 and frag not in joined_refs:
                        s5.append(f"- `{sid}` 引號內容不在所引的 Wiki 條目裡：「{frag}」")
            if ref_lines:
                cb = bigrams(plain(text))
                rb = set().union(*(bigrams(l) for l in ref_lines))
                if cb:
                    sc = len(cb & rb) / len(cb)
                    scores.append(sc)
                    if sc < th:
                        s2.append(f"- {sc:.2f} `{sid}` {plain(text)[:50]}")
        for extra in ("title", "kicker", "note"):
            if s.get(extra):
                texts.append(s[extra])
        for q in s.get("qs", []):
            texts.append(q["q"])
        for lv in s.get("levels", []) + s.get("eras", []) + s.get("steps", []) + s.get("bands", []):
            texts.append(lv["name"])
        joined = "\n".join(texts)
        for term in defined_at:
            if term not in first_seen and term in joined:
                first_seen[term] = idx

    for term, at in defined_at.items():
        seen = first_seen.get(term)
        if seen is not None and seen < at:
            s3.append(f"- 「{term}」在 {order[seen]} 就出現了，但到 {order[at]} 才定義")

    covered = set()
    for sid, v in mp.items():
        if not sid.startswith("_"):
            covered.update(v.get("goal", []))
    for g in content["goals"]:
        if int(g) not in covered:
            s4.append(f"- 學習目標 {g} 沒有任何投影片負責")

    import statistics
    out = [f"# ④ 投影片內容檢查（S2 門檻 {th}）",
           f"句子數：{len(scores)}　S2 分數：最低 {min(scores):.2f}／中位數 {statistics.median(scores):.2f}" if scores else "",
           f"S1 溯源：{len(s1)}　S2 對照：{len(s2)}　S3 術語：{len(s3)}　S4 目標：{len(s4)}　S5 標籤強度：{len(s5)}", ""]
    for name, lst in (("S1 溯源", s1), ("S2 對照（低重疊）", s2), ("S3 術語順序", s3), ("S4 學習目標", s4), ("S5 標籤強度", s5)):
        if lst:
            out += [f"## {name}"] + lst + [""]
    text = "\n".join(out)
    print(text)
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(text, encoding="utf-8")
    sys.exit(1 if (s1 or s2 or s3 or s4 or s5) else 0)


if __name__ == "__main__":
    main()
