# 艾爾登法環 LLM Wiki 與教學簡報

生成式 AI 作業：用 LLM Wiki 做一份教學 HTML 簡報。

**作業報告（網頁版）：https://yopeko.github.io/elden-ring-llm-wiki/**　·　Wiki 以外的所有繳交內容都在這一頁，依作業要求 1～6 排列。

| 作業要求 | 連結 |
|---|---|
| 1. LLM Wiki 主題與簡短介紹 | [作業報告 第 1 節](https://yopeko.github.io/elden-ring-llm-wiki/#intro) |
| 2. LLM Wiki 連結／成果 | [Wiki 網頁版](https://yopeko.github.io/elden-ring-llm-wiki/wiki.html)　·　[markdown 原檔](source/wiki/index.md) |
| 3. 教學 HTML 簡報連結 | [教學簡報](https://yopeko.github.io/elden-ring-llm-wiki/slides.html) |
| 4. loop／graph 流程圖與說明 | [作業報告 第 4 節](https://yopeko.github.io/elden-ring-llm-wiki/#flow)　·　[markdown](source/report/流程說明.md) |
| 5. 一次實際執行的結果與檢查紀錄 | [作業報告 第 5 節](https://yopeko.github.io/elden-ring-llm-wiki/#record)　·　[markdown](source/report/執行紀錄.md)　·　[每集討論紀錄](source/report/ingest討論紀錄.md)　·　[操作 log](source/wiki/log.md) |
| 6. 反思 | [作業報告 第 6 節](https://yopeko.github.io/elden-ring-llm-wiki/#reflection)　·　[markdown](source/report/反思.md) |

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
