"""⑤ 產生 HTML：slides/content.json ＋ slides/map.json ＋ Wiki → slides/index.html

- 每句話的標籤（文本／考據／推測／爭議）由它引用的 Wiki 條目自動決定，不由撰寫者手填。
- 點標籤可展開出處：Wiki 頁名 → 影片集數與時間點（可直接跳到 YouTube 該時間）。
用法：py -X utf8 tools/build_slides.py
"""
import html
import json
import re
from pathlib import Path

from wikiparse import ROOT, SEVERITY, pages, resolve

SRC_RE = re.compile(r"\[(環學[0-9A-Z]+(?:重製)?)([^\]]*)\]")
EP_RE = re.compile(r"(環學[0-9A-Z]+(?:重製)?)")
TIME_RE = re.compile(r"\b(\d{2}):(\d{2})\b")
TAG_CLASS = {"文本": "t-text", "考據": "t-inter", "推測": "t-guess", "爭議": "t-dispute"}

content = json.loads((ROOT / "slides" / "content.json").read_text(encoding="utf-8"))
mp = json.loads((ROOT / "slides" / "map.json").read_text(encoding="utf-8"))
P = pages()

# 影片網址
VIDEO, VTITLE = {}, {}
for name, p in P.items():
    if p.parent.name == "sources":
        t = p.read_text(encoding="utf-8")
        m = re.search(r"^video: (\S+)", t, re.M)
        h = re.search(r"^# (.+)$", t, re.M)
        if m:
            VIDEO[name] = m.group(1)
            VTITLE[name] = h.group(1) if h else name


def cites(line):
    """從 Wiki 條目抓出 (集數, mm:ss) 清單"""
    out = []
    for m in SRC_RE.finditer(line):
        ep = None
        for part in re.split(r"[；;]", m.group(0).strip("[]")):
            e = EP_RE.search(part)
            if e:
                ep = e.group(1)
            for mm, ss in TIME_RE.findall(part):
                out.append((ep, f"{mm}:{ss}", int(mm) * 60 + int(ss)))
    return out


def ref_info(sid, keys):
    refs = mp[sid]["refs"]
    tag, wiki, vids = None, [], []
    for k in keys:
        page, find = refs[k]
        line, t, err = resolve(page, find)
        assert not err, err
        if tag is None or SEVERITY[t] > SEVERITY[tag]:
            tag = t
        if page not in wiki:
            wiki.append(page)
        for c in cites(line):
            if c not in vids:
                vids.append(c)
    return tag, wiki, vids


def vlink(ep, ts, sec):
    url = VIDEO.get(ep, "#")
    return f'<a href="{url}&t={sec}s" target="_blank" rel="noopener">{ep} {ts}</a>'


slide_wiki, slide_vids = [], []


def claim(sid, text, keys, tagname="span"):
    if not keys:
        return f"<{tagname} class=\"claim\">{text}</{tagname}>"
    tag, wiki, vids = ref_info(sid, keys)
    for w in wiki:
        if w not in slide_wiki:
            slide_wiki.append(w)
    for v in vids:
        if v not in slide_vids:
            slide_vids.append(v)
    src = "Wiki：" + "、".join(html.escape(w) for w in wiki)
    if vids:
        src += "　影片：" + "、".join(vlink(*v) for v in vids[:4])
    return (f'<{tagname} class="claim">{text} '
            f'<button class="tag {TAG_CLASS[tag]}" aria-expanded="false" title="點擊查看出處">{tag}</button>'
            f'<span class="src" hidden>{src}</span></{tagname}>')


def items_html(sid, items):
    return "<ul class=\"items\">" + "".join(claim(sid, it["t"], it.get("r", []), "li") for it in items) + "</ul>"


def render(s, n, total):
    global slide_wiki, slide_vids
    slide_wiki, slide_vids = [], []
    sid, typ = s["id"], s["type"]
    head = ""
    if typ != "cover":
        head = (f'<header><p class="kicker">{html.escape(s.get("kicker", ""))}</p>'
                f'<h2>{html.escape(s["title"])}</h2></header>')
    body = ""
    if typ == "cover":
        body = (f'<div class="cover"><p class="eyebrow">教學簡報 · LLM Wiki 產生</p>'
                f'<h1>{html.escape(content["title"])}</h1><p class="sub">{html.escape(content["subtitle"])}</p>'
                f'<div class="ring" aria-hidden="true"></div>'
                f'<p class="hint">按 → 或點右下角開始　·　每句話旁的標籤可以點開看出處</p></div>')
    elif typ == "goals":
        goals = "".join(f"<li><b>{k}</b>{html.escape(v)}</li>" for k, v in content["goals"].items())
        body = (f'<div class="two"><div><h3>看完你應該能：</h3><ol class="goals">{goals}</ol></div>'
                f'<div>{items_html(sid, s["items"])}'
                f'<ul class="legend"><li><span class="tag t-text">文本</span>遊戲內的文字（道具說明、台詞）</li>'
                f'<li><span class="tag t-inter">考據</span>考據者從文本推出的解讀</li>'
                f'<li><span class="tag t-guess">推測</span>考據者自己承認沒有直接證據</li>'
                f'<li><span class="tag t-dispute">爭議</span>不同集數說法不同</li></ul></div></div>')
    elif typ == "list":
        body = items_html(sid, s["items"])
        if s.get("note"):
            body += f'<p class="note">{html.escape(s["note"])}</p>'
        if s.get("sources"):
            vids = "".join(f'<li><a href="{VIDEO[k]}" target="_blank" rel="noopener">{html.escape(VTITLE[k])}</a></li>'
                           for k in sorted(VIDEO))
            body += f'<h3>資料來源：6 集「環學」影片</h3><ul class="vids">{vids}</ul>'
    elif typ == "pyramid":
        lv = s["levels"]
        rows = ""
        for i, l in enumerate(lv):
            w = 34 + i * 66 / max(1, len(lv) - 1)  # 由上而下變寬，堆成金字塔
            rows += (f'<div class="lvl" style="--w:{w:.0f}%"><span class="lname">{html.escape(l["name"])}</span>'
                     f'{claim(sid, l["t"], l["r"], "p")}</div>')
        body = f'<div class="pyramid">{rows}</div><p class="note">↑ 越往上，知道的事情越多；越往下，只看得到上一層。</p>'
    elif typ == "timeline":
        cells = "".join(f'<li><span class="era">{i+1}. {html.escape(e["name"])}</span>{claim(sid, e["t"], e["r"], "p")}</li>'
                        for i, e in enumerate(s["eras"]))
        body = f'<ol class="timeline">{cells}</ol>'
    elif typ == "compare":
        body = items_html(sid, s["intro"])
        body += ('<div class="vs">'
                 f'<div class="side l"><h3>{html.escape(s["left"]["head"])}</h3>{claim(sid, s["left"]["t"], s["left"]["r"], "p")}</div>'
                 '<div class="vsmark">VS</div>'
                 f'<div class="side r"><h3>{html.escape(s["right"]["head"])}</h3>{claim(sid, s["right"]["t"], s["right"]["r"], "p")}</div>'
                 '</div><p class="note">同一件事，從不同立場看會得出完全不同的結論——這正是讀法環故事的樂趣。</p>')
    elif typ == "plan":
        steps = "".join(f'<div class="step"><h3>{html.escape(st["name"])}</h3>{claim(sid, st["t"], st["r"], "p")}</div>'
                        for st in s["steps"])
        body = f'<div class="steps">{steps}</div>' + items_html(sid, s["items"])
    elif typ == "spectrum":
        bands = "".join(f'<div class="band"><h3>{html.escape(b["name"])}</h3>{claim(sid, b["t"], b["r"], "p")}</div>'
                        for b in s["bands"])
        a, z = s["ends"]
        body = (f'<div class="spectrum"><div class="axis"><span>← {a}</span><span>{z} →</span></div>'
                f'<div class="bands">{bands}</div></div>' + items_html(sid, s["items"]))
    elif typ == "quiz":
        qs = "".join(f'<details class="q"><summary><b>Q{i+1}</b> {html.escape(q["q"])}</summary>{claim(sid, q["a"], q["r"], "p")}</details>'
                     for i, q in enumerate(s["qs"]))
        body = f'<div class="quiz">{qs}</div>'
    foot = ""
    if slide_wiki:
        foot = '<footer>📚 Wiki 來源：' + "、".join(html.escape(w) for w in slide_wiki) + "</footer>"
    return (f'<section class="slide s-{typ}" id="{sid}" data-n="{n}" aria-label="第 {n} 張，共 {total} 張">'
            f'<div class="inner">{head}<div class="body">{body}</div>{foot}</div></section>')


total = len(content["slides"])
sections = "\n".join(render(s, i + 1, total) for i, s in enumerate(content["slides"]))
tpl = (ROOT / "slides" / "template.html").read_text(encoding="utf-8")
out = tpl.replace("{{TITLE}}", html.escape(content["title"])).replace("{{SLIDES}}", sections)
(ROOT / "slides" / "index.html").write_text(out, encoding="utf-8")
print(f"已產生 slides/index.html：{total} 張")
