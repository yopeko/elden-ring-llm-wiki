"""把要繳交的東西整理成可以直接瀏覽的網站：site/

  site/index.html   作業報告：除了 Wiki 以外的所有繳交內容（1 主題 → 6 反思＋附錄）
  site/wiki.html    LLM Wiki 瀏覽頁（39 頁，頁面互相連結，出處可點到 YouTube 時間點）
  （原本的 report.html 已合併進 index.html）
  site/slides.html  教學簡報（slides/index.html 的複本）

用法：py -X utf8 tools/build_site.py
"""
import html
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
SITE.mkdir(exist_ok=True)

PAGES = {p.stem: p for p in (ROOT / "wiki").rglob("*.md") if p.name not in ("index.md", "log.md")}
VIDEO = {}
for name, p in PAGES.items():
    m = re.search(r"^video: (\S+)", p.read_text(encoding="utf-8"), re.M)
    if m:
        VIDEO[name] = m.group(1)

SRC_RE = re.compile(r"\[(環學[0-9A-Z]+(?:重製)?)([^\]\[]*)\]")
EP_RE = re.compile(r"(環學[0-9A-Z]+(?:重製)?)")
TIME_RE = re.compile(r"\b(\d{2}):(\d{2})\b")
TAGS = {"文本": "t-text", "考據": "t-inter", "推測": "t-guess"}
SLUG = {name: f"p{i:02d}" for i, name in enumerate(sorted(PAGES), 1)}  # 發佈平台的網址錨點只接受英數字


def src_link(m, page_mode):
    """[環學08 §區塊三 14:09；環學03 §區塊一 01:08] → 每個時間點都變成 YouTube 連結"""
    parts, ep = [], None
    for part in re.split(r"[；;]", m.group(0)[1:-1]):
        e = EP_RE.search(part)
        if e:
            ep = e.group(1)
        def tl(t):
            sec = int(t.group(1)) * 60 + int(t.group(2))
            url = VIDEO.get(ep)
            return f'<a href="{url}&t={sec}s" target="_blank" rel="noopener">{t.group(0)}</a>' if url else t.group(0)
        parts.append(TIME_RE.sub(tl, part))
    return f'<span class="cite">［{"；".join(parts)}］</span>'


def inline(s, page_mode="wiki"):
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\[\[([^\]]+)\]\]",
               lambda m: f'<a class="wl" href="{"#" if page_mode == "wiki" else "wiki.html#"}{SLUG.get(m.group(1), "home")}">{m.group(1)}</a>', s)
    s = SRC_RE.sub(lambda m: src_link(m, page_mode), s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"〔(文本|考據|推測)〕", lambda m: f'<span class="tag {TAGS[m.group(1)]}">{m.group(1)}</span>', s)
    return s


def md(text, page_mode="wiki", shift=None):
    """夠用的 Markdown 轉換：標題、清單（含縮排）、表格、引言、程式碼／mermaid、段落"""
    lines = text.splitlines()
    out, i, list_stack = [], 0, []

    def close_lists(level=0):
        while len(list_stack) > level:
            out.append(f"</{list_stack.pop()}>")

    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            close_lists()
            lang = ln[3:].strip()
            buf = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            body = html.escape("\n".join(buf))
            out.append(f'<pre class="mermaid">{body}</pre>' if lang == "mermaid" else f"<pre>{body}</pre>")
            i += 1
            continue
        if ln.startswith("|"):
            close_lists()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i])
                i += 1
            cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
            head, body = cells[0], [r for r in cells[1:] if not set("".join(r)) <= set("-: ")]
            t = "<div class=\"tw\"><table><thead><tr>" + "".join(f"<th>{inline(c, page_mode)}</th>" for c in head) + "</tr></thead><tbody>"
            t += "".join("<tr>" + "".join(f"<td>{inline(c, page_mode)}</td>" for c in r) + "</tr>" for r in body)
            out.append(t + "</tbody></table></div>")
            continue
        m = re.match(r"^(#{1,4}) (.*)", ln)
        if m:
            close_lists()
            lv = len(m.group(1)) + (shift if shift is not None else (1 if page_mode == "wiki" else 0))
            out.append(f"<h{min(lv, 5)}>{inline(m.group(2), page_mode)}</h{min(lv, 5)}>")
            i += 1
            continue
        m = re.match(r"^(\s*)([-*]|\d+\.) (.*)", ln)
        if m:
            level = len(m.group(1)) // 2 + 1
            kind = "ol" if m.group(2)[0].isdigit() else "ul"
            while len(list_stack) < level:
                list_stack.append(kind)
                out.append(f"<{kind}>")
            close_lists(level)
            out.append(f"<li>{inline(m.group(3), page_mode)}</li>")
            i += 1
            continue
        if ln.startswith(">"):
            close_lists()
            out.append(f'<blockquote>{inline(ln.lstrip("> "), page_mode)}</blockquote>')
            i += 1
            continue
        if ln.strip() in ("---", ""):
            close_lists()
            if ln.strip() == "---":
                out.append("<hr>")
            i += 1
            continue
        close_lists()
        out.append(f"<p>{inline(ln, page_mode)}</p>")
        i += 1
    close_lists()
    return "\n".join(out)


def split_front(t):
    if t.startswith("---"):
        end = t.find("\n---", 3)
        return t[3:end], t[end + 4:]
    return "", t


CSS = """
:root{--bg:#0f0d0a;--bg2:#17140f;--panel:#1f1b14;--line:#3a3224;--text:#ece4d4;--muted:#a89c86;--gold:#d9b45a;--gold2:#f3d98c;--t-text:#6fbf8e;--t-inter:#d9b45a;--t-guess:#e07a5f;color-scheme:dark}
@media (prefers-color-scheme: light){:root:not([data-theme="dark"]){--bg:#f6f1e6;--bg2:#efe7d6;--panel:#fffaf0;--line:#d8ccb2;--text:#2a2418;--muted:#6e624c;--gold:#9a7420;--gold2:#7a5a12;--t-text:#2f7d4f;--t-inter:#9a7420;--t-guess:#b8492c;color-scheme:light}}
:root[data-theme="light"]{--bg:#f6f1e6;--bg2:#efe7d6;--panel:#fffaf0;--line:#d8ccb2;--text:#2a2418;--muted:#6e624c;--gold:#9a7420;--gold2:#7a5a12;--t-text:#2f7d4f;--t-inter:#9a7420;--t-guess:#b8492c;color-scheme:light}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:16px/1.75 "Noto Sans TC",system-ui,sans-serif}
a{color:var(--gold)}
h1,h2,h3,h4,h5{font-family:"Noto Serif TC",serif;color:var(--gold2);line-height:1.35}
code{background:var(--bg2);padding:.1em .35em;border-radius:4px;font-size:.9em}
pre{background:var(--bg2);border:1px solid var(--line);border-radius:8px;padding:12px;overflow:auto;font-size:.85em}
pre.mermaid{background:#fffaf0;color:#2a2418;text-align:center}
blockquote{margin:1em 0;padding:.6em 1em;border-left:3px solid var(--gold);background:var(--panel);border-radius:0 8px 8px 0}
.tw{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:.9em;margin:1em 0}
th,td{border:1px solid var(--line);padding:.45em .6em;vertical-align:top;text-align:left}
th{background:var(--panel);color:var(--gold2)}
hr{border:0;border-top:1px dashed var(--line);margin:2em 0}
.tag{display:inline-block;font-size:.72em;line-height:1;padding:.3em .5em;border-radius:99px;border:1px solid currentColor;margin:0 .2em;vertical-align:.1em}
.t-text{color:var(--t-text)}.t-inter{color:var(--t-inter)}.t-guess{color:var(--t-guess)}
.cite{color:var(--muted);font-size:.8em}
.top{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;background:var(--bg2);border-bottom:1px solid var(--line);padding:10px 16px;display:flex;gap:16px;flex-wrap:wrap;align-items:center}
.top b{color:var(--gold2);font-family:"Noto Serif TC",serif}
.top a{text-decoration:none}
.wrap{max-width:960px;margin:0 auto;padding:16px}
"""
FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;700&family=Noto+Serif+TC:wght@700;900&display=swap" rel="stylesheet">')
NAV = ('<nav class="top"><b>艾爾登法環 LLM Wiki 作業</b><a href="index.html">作業報告</a><a href="wiki.html">LLM Wiki</a>'
       '<a href="slides.html">教學簡報</a></nav>')


def page(title, body, extra_head="", extra_css=""):
    return (f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
            f"<title>{title}</title>{FONTS}<style>{CSS}{extra_css}</style>{extra_head}</head><body>{NAV}{body}</body></html>")


# ---------- wiki.html ----------
index_md = (ROOT / "wiki" / "index.md").read_text(encoding="utf-8")
nav_html = md(index_md, "wiki")
articles = []
intro = ('<article id="home"><h2>LLM Wiki：艾爾登法環世界觀</h2>'
         '<p>由 6 集「環學」考據影片整理而成，共 39 頁、384 條重點。每條重點都有：</p>'
         '<ul><li>可信度標籤：<span class="tag t-text">文本</span>遊戲原文　<span class="tag t-inter">考據</span>影片作者的解讀　'
         '<span class="tag t-guess">推測</span>作者自己承認沒有直接證據</li>'
         '<li>出處：［環學08 §區塊三 <a>14:09</a>］＝第幾集、影片的第幾段、時間點（點時間會跳到 YouTube 該秒）</li>'
         '<li>⚠ 矛盾與更正：不同集數說法不同時，兩種說法都保留</li></ul>'
         '<p>從左邊目錄選一頁開始；建議從「時代總覽」或「艾爾登法環」看起。Wiki 的維護規則見<a href="#rules">維護規則</a>，'
         '逐筆操作紀錄見<a href="#log">操作紀錄</a>。</p></article>')
articles.append(intro)
for name, p in sorted(PAGES.items()):
    front, body = split_front(p.read_text(encoding="utf-8"))
    meta = re.search(r"^sources: \[(.*)\]", front, re.M)
    typ = re.search(r"^type: (\w+)", front, re.M)
    label = {"entity": "人物與勢力", "concept": "概念", "event": "事件", "source": "影片摘要"}.get(typ.group(1) if typ else "", "")
    m_line = f'<p class="meta">{label}{"　·　資料來源：" + meta.group(1) if meta else ""}</p>'
    articles.append(f'<article id="{SLUG[name]}" hidden>{m_line}{md(body, "wiki")}</article>')
articles.append(f'<article id="rules" hidden>{md((ROOT / "CLAUDE.md").read_text(encoding="utf-8").replace("[[連結]]", "［［連結］］"), "wiki")}</article>')
articles.append(f'<article id="log" hidden>{md((ROOT / "wiki" / "log.md").read_text(encoding="utf-8").replace("[[連結]]", "［［連結］］"), "wiki")}</article>')

wiki_css = """
.layout{display:grid;grid-template-columns:280px 1fr;max-width:1240px;margin:0 auto}
aside{position:sticky;top:calc(49px + env(safe-area-inset-top,0px));height:calc(100vh - 49px);overflow:auto;border-right:1px solid var(--line);padding:12px 16px;font-size:.9em}
aside h2{font-size:1.1em}aside h3{font-size:.95em;margin:1em 0 .2em}aside ul{padding-left:1em;margin:0}aside li{margin:.15em 0}
aside blockquote{font-size:.85em}
main{padding:16px 28px;min-width:0}
.meta{color:var(--muted);font-size:.85em}
@media (max-width:760px){.layout{grid-template-columns:1fr}aside{position:static;height:auto;border-right:0;border-bottom:1px solid var(--line)}main{padding:16px}}
"""
wiki_js = """<script>
function show(){const id=decodeURIComponent(location.hash.slice(1))||'home';
let found=false;document.querySelectorAll('main article').forEach(a=>{const on=a.id===id;a.hidden=!on;if(on)found=true;});
if(!found)document.getElementById('home').hidden=false;window.scrollTo(0,0);}
window.addEventListener('hashchange',show);show();
</script>"""
(SITE / "wiki.html").write_text(page("艾爾登法環 LLM Wiki",
    f'<div class="layout"><aside><p><a href="#home">← Wiki 首頁</a></p>{nav_html}'
    f'<h3>其他</h3><ul><li><a href="#rules">維護規則（CLAUDE.md）</a></li><li><a href="#log">操作紀錄（log.md）</a></li></ul></aside>'
    f'<main>{"".join(articles)}</main></div>{wiki_js}', extra_css=wiki_css), encoding="utf-8")

# ---------- index.html：作業報告（Wiki 以外的所有繳交內容合成一份） ----------
def body_without_title(fn):
    """去掉 md 檔第一行的 # 大標題，由報告自己給章節標題"""
    lines = (ROOT / "report" / fn).read_text(encoding="utf-8").splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    return "\n".join(lines)

sub = (ROOT / "繳交說明.md").read_text(encoding="utf-8")
blocks = re.split(r"\n(?=## )", sub)
title = blocks[0].splitlines()[0].lstrip("# ").strip()
lead = "\n".join(l for l in blocks[0].splitlines()[1:] if l.startswith(">"))
sec = {b.splitlines()[0][3:5].strip(". "): "\n".join(b.splitlines()[1:]) for b in blocks[1:]}

GLOSSARY = """<details class="gloss"><summary>紀錄中出現的代號是什麼意思？</summary>
<p><b>raw</b>＝原始資料（影片整理稿）　<b>ingest</b>＝把一集資料讀進 Wiki　<b>lint</b>＝Wiki 的自動檢查程式　<b>index</b>＝Wiki 的目錄頁</p>
<p><b>L1–L10</b>＝lint 的各項檢查：L1 連結、L2 可信度標籤、L3 出處、L4 孤兒頁面、L5 引文是否存在於原始資料、L6 時間點是否存在、L7 原始資料沒有的英文詞、L8 目錄一致性、L9 句子與所引影片段落的用字比對、L10 標成原文就必須有引文</p>
<p><b>①～⑥</b>＝簡報流程的節點；<b>②'</b>＝動筆前的「對照表檢查」；<b>S1–S5</b>＝簡報內容檢查：S1 出處、S2 是否寫了 Wiki 沒有的內容、S3 名詞先解釋後使用、S4 學習目標覆蓋、S5 原文標籤</p>
<p><b>C1–C10</b>＝影片前後集說法不同的 10 個地方　<b>Q1–Q25</b>＝討論階段由我決定的 25 個問題</p></details>"""

TOC = [("intro", "1. 主題與簡介"), ("wiki", "2. LLM Wiki"), ("slides", "3. 教學簡報"),
       ("flow", "4. loop／graph"), ("record", "5. 執行紀錄"), ("reflection", "6. 反思"), ("appendix", "附錄")]
toc_html = "".join(f'<a href="#{i}">{t}</a>' for i, t in TOC)

parts = [f'<header class="hero"><p class="eyebrow">生成式 AI 作業｜用 LLM Wiki 做一份教學 HTML 簡報</p><h1>{html.escape(title)}</h1>{md(lead, "report")}</header>',
         f'<nav class="toc" aria-label="目錄">{toc_html}</nav>']
parts.append(f'<section id="intro"><h2>1. LLM Wiki 主題與簡短介紹</h2>{md(sec["1"], "report", shift=1)}</section>')
parts.append(f'<section id="wiki"><h2>2. LLM Wiki 連結與成果</h2>{md(sec["2"], "report", shift=1)}'
             '<p>Wiki 的維護規則（頁面格式、可信度標籤、出處格式、矛盾處理）與逐筆操作紀錄，也都可以在 Wiki 網頁左側的「其他」找到。</p></section>')
parts.append(f'<section id="slides"><h2>3. 教學 HTML 簡報連結</h2>{md(sec["3"], "report", shift=1)}</section>')
parts.append(f'<section id="flow"><h2>4. loop／graph 的流程圖與說明</h2>{md(body_without_title("流程說明.md"), "report", shift=1)}</section>')
parts.append(f'<section id="record"><h2>5. 一次實際執行的結果與檢查紀錄</h2>{GLOSSARY}{md(body_without_title("執行紀錄.md"), "report", shift=1)}</section>')
parts.append(f'<section id="reflection"><h2>6. 反思</h2>{md(body_without_title("反思.md"), "report", shift=1)}</section>')
parts.append('<section id="appendix"><h2>附錄</h2>'
             f'<details><summary>附錄 A：每一集的討論紀錄（先討論、後生成的原始紀錄）</summary>{md(body_without_title("ingest討論紀錄.md"), "report", shift=2)}</details>'
             f'<details><summary>附錄 B：簡報規劃（當時的大綱與 graph 草案）</summary>{md(body_without_title("簡報規劃.md"), "report", shift=2)}</details>'
             '<p class="foot">本作業與 AI 程式助理（Claude Code）協作完成：AI 負責閱讀資料、提出討論稿、寫 Wiki 與簡報、撰寫檢查程式；我負責每一集的決策與方向確認。</p></section>')

report_css = """
.hero{padding-block:8px 4px}
.hero .eyebrow{color:var(--muted);font-size:.85em;letter-spacing:.06em;margin:0}
.hero h1{font-size:clamp(1.6em,4vw,2.3em);margin:.2em 0 .4em;text-wrap:balance}
.toc{display:flex;flex-wrap:wrap;gap:6px 8px;margin:12px 0 8px;padding:10px 0;border-block:1px solid var(--line)}
.toc a{padding:.25em .7em;border:1px solid var(--line);border-radius:99px;text-decoration:none;font-size:.9em;background:var(--panel)}
.toc a:hover{border-color:var(--gold)}
section{scroll-margin-top:64px;padding-top:12px}
section>h2{font-size:1.55em;border-bottom:2px solid var(--gold);padding-bottom:.25em;margin-top:1.6em}
details{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:.6em .9em;margin:1em 0}
details summary{cursor:pointer;color:var(--gold2);font-weight:700}
details.gloss p{font-size:.9em;margin:.5em 0}
.foot{color:var(--muted);font-size:.85em;margin-top:2em}
"""
NAV2 = ('<nav class="top"><b>艾爾登法環 LLM Wiki 作業</b><a href="index.html">作業報告</a><a href="wiki.html">LLM Wiki</a>'
        '<a href="slides.html">教學簡報</a></nav>')
mermaid = ('<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>'
           '<script>addEventListener("load",()=>setTimeout(()=>{if(window.mermaid&&!document.querySelector("pre.mermaid svg")){mermaid.initialize({startOnLoad:false,theme:"default"});mermaid.run({querySelector:"pre.mermaid"});}},600));</script>')
report_html = (f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
               f'<title>{html.escape(title)}｜作業報告</title>{FONTS}<style>{CSS}{report_css}</style>{mermaid}</head>'
               f'<body>{NAV2}<main class="wrap">{"".join(parts)}</main></body></html>')
(SITE / "index.html").write_text(report_html, encoding="utf-8")
old_report = SITE / "report.html"
if old_report.exists():
    old_report.unlink()  # 已合併進 index.html
for leftover in ("main.html",):
    if (SITE / leftover).exists():
        (SITE / leftover).unlink()

# ---------- slides.html ----------
shutil.copyfile(ROOT / "slides" / "index.html", SITE / "slides.html")
print("已產生 site/：index.html（作業報告）、wiki.html、slides.html")
