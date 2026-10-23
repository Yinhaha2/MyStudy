import csv
import json
import urllib.request
from pathlib import Path

token = Path(r"C:\Users\Y2698\Desktop\研究生\毕设\datebase\影子仓\.github_token").read_text(encoding="utf-8").strip()
HERE = Path(__file__).resolve().parent
rows = list(csv.DictReader(open(HERE / "prs_with_perf_tests.csv", encoding="utf-8")))
cands = []
for row in rows:
    files = [item for item in row["perf_files"].split(" | ") if item]
    if len(files) != 1:
        continue
    name = files[0]
    if not (
        name.endswith("_bench_test.go")
        or name.endswith("_benchmark_test.go")
        or name.endswith(".bench.ts")
        or "/benches/" in name
    ):
        continue
    if int(row["n_added"]) < 1:
        continue
    cands.append(row)
print("cands", len(cands))


def get(url: str):
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": "mystudy-perf-test",
        },
    )
    with urllib.request.urlopen(req, timeout=40) as resp:
        return json.load(resp)


out = HERE / "examples"
out.mkdir(parents=True, exist_ok=True)
found = set()
for kind in ("closed_unmerged", "merged"):
    for row in cands:
        if row["outcome"] != kind or kind in found:
            continue
        repo = row["html_url"].split("github.com/")[1].rsplit("/pull/", 1)[0]
        number = row["html_url"].rstrip("/").split("/")[-1]
        name = row["perf_files"]
        try:
            files = get(f"https://api.github.com/repos/{repo}/pulls/{number}/files?per_page=100")
        except Exception as exc:
            print("err", row["html_url"], type(exc).__name__)
            continue
        hit = next((item for item in files if item["filename"] == name), None)
        patch = (hit or {}).get("patch") or ""
        if "Benchmark" not in patch and "fn " not in patch and "bench" not in patch.lower():
            continue
        (out / f"perf_{row['pr_id']}.patch").write_text(patch, encoding="utf-8")
        print("GOT", kind, row["html_url"])
        print(name)
        print(patch[:800])
        print("---")
        found.add(kind)
        break
print("found", found)
