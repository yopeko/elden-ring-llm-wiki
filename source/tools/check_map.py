"""②' 對照表檢查：撰寫投影片之前，先確認 slides/map.json 的每個引用都能在 Wiki 找到唯一一條、而且有標籤。

用法：py -X utf8 tools/check_map.py [輸出報告路徑]
"""
import json
import sys
from collections import Counter
from pathlib import Path

from wikiparse import ROOT, resolve

m = json.loads((ROOT / "slides" / "map.json").read_text(encoding="utf-8"))
errors, tags = [], Counter()
total = 0
for sid, slide in m.items():
    if sid.startswith("_"):
        continue
    for key, (page, find) in slide["refs"].items():
        total += 1
        line, tag, err = resolve(page, find)
        if err:
            errors.append(f"- `{sid}/{key}` {err}")
        else:
            tags[tag] += 1

out = ["# ②' 對照表檢查", f"引用數：{total}　錯誤：{len(errors)}",
       "標籤分布：" + "、".join(f"{t} {n}" for t, n in tags.most_common()), ""]
out += errors
text = "\n".join(out)
print(text)
if len(sys.argv) > 1:
    Path(sys.argv[1]).write_text(text, encoding="utf-8")
sys.exit(1 if errors else 0)
