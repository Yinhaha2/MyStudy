import json
from pathlib import Path

nb = json.loads(Path(r"..\AIDevPerf\LLM-performance\Analysis.ipynb").read_text(encoding="utf-8"))
src = "".join(nb["cells"][9]["source"])
print(src)
