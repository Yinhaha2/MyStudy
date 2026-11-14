import json
import urllib.request
from pathlib import Path

key = (Path(__file__).resolve().parents[2] / ".deepseekToken").read_text(encoding="utf-8").strip()
body = {
    "model": "deepseek-chat",
    "temperature": 0,
    "max_tokens": 8,
    "messages": [
        {
            "role": "system",
            "content": "You are a GitHub Pull Request Classification Agent. Given a text combining the title and body of a pull request, determine whether the primary purpose of the pull request is to improve performance. Classify each pull request as either 'performance' or 'non-performance'. Reply with exactly one word.",
        },
        {"role": "user", "content": "fix: speed up table scan by caching row counts"},
    ],
}
req = urllib.request.Request(
    "https://api.deepseek.com/chat/completions",
    data=json.dumps(body).encode(),
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
)
with urllib.request.urlopen(req, timeout=60) as resp:
    data = json.loads(resp.read().decode())
print(resp.status)
print(data["choices"][0]["message"]["content"])
print(data.get("usage"))
