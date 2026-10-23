import json
from pathlib import Path

nb = json.loads(Path(r"..\AIDevPerf\LLM-performance\Analysis.ipynb").read_text(encoding="utf-8"))
print("cells", len(nb["cells"]))
for i, cell in enumerate(nb["cells"]):
    src = "".join(cell.get("source", []))
    low = src.lower()
    if any(k in low for k in ("keyword", "classifier", "llmclassifier", "filter_performance", "regex")):
        print("---", i, cell["cell_type"], "chars", len(src))
        print(src[:500].replace("\n", " | "))
        print()
