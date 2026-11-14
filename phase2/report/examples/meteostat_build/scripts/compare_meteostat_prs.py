import json
import urllib.request

proxy = urllib.request.ProxyHandler(
    {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}
)
opener = urllib.request.build_opener(proxy)

for n in (217, 269, 293):
    url = f"https://api.github.com/repos/meteostat/meteostat/pulls/{n}"
    with opener.open(url) as r:
        pr = json.load(r)
    with opener.open(url + "/files?per_page=100") as r:
        files = json.load(r)
    print("=" * 60)
    print(f"PR #{n}", pr.get("title"))
    print(
        "state",
        pr.get("state"),
        "merged",
        bool(pr.get("merged_at")),
        pr.get("merged_at"),
    )
    print("user", (pr.get("user") or {}).get("login"))
    body = (pr.get("body") or "")[:800].replace("\n", " ")
    print("body:", body)
    print("files:")
    for f in files:
        print(
            " ",
            f["status"],
            f["filename"],
            f"+{f['additions']}/-{f['deletions']}",
        )
    benchish = [
        f["filename"]
        for f in files
        if "bench" in f["filename"].lower()
        or "perf" in f["filename"].lower()
        or "interpolat" in f["filename"].lower()
    ]
    print("bench/perf/interp related files in this PR:", benchish or "NONE")
