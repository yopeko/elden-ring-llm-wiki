"""把要繳交的東西整理成一個可以直接上傳 GitHub 的資料夾：github-upload/

用法：py -X utf8 tools/pack_github.py [GitHub帳號] [repo名稱]
  例：py -X utf8 tools/pack_github.py yourname elden-ring-llm-wiki
  不給帳號時，網址會用「你的帳號」當佔位字，之後可以重跑一次填入。

產生：
  github-upload/                ← 這整個資料夾的「內容」上傳成 repo 的根目錄
    index.html                  作業報告：Wiki 以外的所有繳交內容（GitHub Pages 首頁）
    wiki.html / slides.html     LLM Wiki、教學簡報
    .nojekyll                   讓 GitHub Pages 原樣提供檔案
    README.md                   repo 首頁說明
    source/                     原始檔：Wiki markdown、檢查紀錄、檢查程式、原始資料
  貼到繳交表單.txt              繳交時要貼的文字（網址已填好）
"""
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "github-upload"
user = sys.argv[1] if len(sys.argv) > 1 else "你的帳號"
repo = sys.argv[2] if len(sys.argv) > 2 else "elden-ring-llm-wiki"
PAGES = f"https://{user}.github.io/{repo}/"
REPO = f"https://github.com/{user}/{repo}"

# 1) 先重新產生網站（確保是最新內容）
subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "tools" / "build_slides.py")], check=True)
subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "tools" / "build_site.py")], check=True)

# 2) 重建 github-upload/
if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir()
for f in ("index.html", "wiki.html", "slides.html"):
    t = (ROOT / "site" / f).read_text(encoding="utf-8")
    t = t.replace('href="source/"', f'href="{REPO}/tree/main/source"')
    (OUT / f).write_text(t, encoding="utf-8")
(OUT / ".nojekyll").write_text("", encoding="utf-8")
(OUT / ".gitignore").write_text("__pycache__/" + chr(10) + "site/" + chr(10), encoding="utf-8")

src = OUT / "source"
src.mkdir()
shutil.copy2(ROOT / "CLAUDE.md", src / "CLAUDE.md")
shutil.copy2(ROOT / "繳交說明.md", src / "繳交說明.md")
for d in ("wiki", "report", "raw", "tools"):
    shutil.copytree(ROOT / d, src / d, ignore=shutil.ignore_patterns("__pycache__"))
(src / "slides").mkdir()
for f in ("map.json", "content.json", "template.html", "index.html"):
    shutil.copy2(ROOT / "slides" / f, src / "slides" / f)

# 3) README.md（repo 首頁）
readme = f"""# 艾爾登法環 LLM Wiki 與教學簡報

生成式 AI 作業：用 LLM Wiki 做一份教學 HTML 簡報。

**作業報告（網頁版）：{PAGES}**　·　Wiki 以外的所有繳交內容都在這一頁，依作業要求 1～6 排列。

| 作業要求 | 連結 |
|---|---|
| 1. LLM Wiki 主題與簡短介紹 | [作業報告 第 1 節]({PAGES}#intro) |
| 2. LLM Wiki 連結／成果 | [Wiki 網頁版]({PAGES}wiki.html)　·　[markdown 原檔](source/wiki/index.md) |
| 3. 教學 HTML 簡報連結 | [教學簡報]({PAGES}slides.html) |
| 4. loop／graph 流程圖與說明 | [作業報告 第 4 節]({PAGES}#flow)　·　[markdown](source/report/流程說明.md) |
| 5. 一次實際執行的結果與檢查紀錄 | [作業報告 第 5 節]({PAGES}#record)　·　[markdown](source/report/執行紀錄.md)　·　[每集討論紀錄](source/report/ingest討論紀錄.md)　·　[操作 log](source/wiki/log.md) |
| 6. 反思 | [作業報告 第 6 節]({PAGES}#reflection)　·　[markdown](source/report/反思.md) |

## 資料夾說明
- `index.html`：作業報告（第 1～6 項＋附錄，一份 HTML）
- `wiki.html`：LLM Wiki 網頁版
- `slides.html`：教學簡報
- `source/wiki/`：LLM Wiki 原檔（39 頁 markdown，入口 `index.md`，操作紀錄 `log.md`）
- `source/CLAUDE.md`：Wiki 的維護規則（頁面格式、可信度標籤、出處格式、衝突處理）
- `source/report/`：流程說明、執行紀錄、反思、每集討論紀錄，以及每一次自動檢查的報告（`lint/`、`ground/`、`slides/`）
- `source/slides/`：簡報的對照表（`map.json`）與內容（`content.json`）
- `source/tools/`：檢查與產生程式（Python 標準函式庫即可執行）
- `source/raw/`：6 集「環學」影片的整理稿（Wiki 的原始資料）

## 重跑檢查
```
cd source
python -X utf8 tools/lint.py          # Wiki 格式與出處檢查
python -X utf8 tools/ground.py        # 句子與所引影片段落的對照
python -X utf8 tools/check_map.py     # 簡報對照表檢查
python -X utf8 tools/check_slides.py  # 簡報內容檢查
```

資料來源：YouTube「環學」系列考據影片（各頁出處皆附影片時間點連結）。
"""
(OUT / "README.md").write_text(readme, encoding="utf-8")

# 4) 繳交表單要貼的文字（放在上傳資料夾外面）
sub = (ROOT / "繳交說明.md").read_text(encoding="utf-8")
title = sub.splitlines()[0].lstrip("# ").strip()
paste = f"""繳交標題：{title}

1. LLM Wiki 主題與簡短介紹
主題：《艾爾登法環》的世界觀與主線劇情。以 YouTube「環學」系列 6 集劇情考據影片為資料，用「先討論、後生成」的方式建立 LLM Wiki：每一集先由 AI 整理重點與矛盾、由我決定後才寫入。共 39 頁、384 條重點，每條都附可信度標籤（遊戲原文／作者解讀／推測）與影片時間點出處。
詳細介紹：{PAGES}#intro

2. LLM Wiki 連結
{PAGES}wiki.html
（markdown 原檔：{REPO}/tree/main/source/wiki）

3. 教學 HTML 簡報連結
{PAGES}slides.html

4. loop / graph 流程圖與說明
{PAGES}#flow

5. 一次實際執行的結果與檢查紀錄
{PAGES}#record

6. 反思
{PAGES}#reflection

（第 1、4、5、6 項都在同一份作業報告：{PAGES}）
GitHub repo：{REPO}
"""
(ROOT / "貼到繳交表單.txt").write_text(paste, encoding="utf-8")

n = sum(1 for _ in OUT.rglob("*") if _.is_file())
print(f"已產生 github-upload/（{n} 個檔案）與 貼到繳交表單.txt")
print(f"Pages 網址：{PAGES}")
