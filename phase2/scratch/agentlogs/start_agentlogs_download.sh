#!/usr/bin/env bash
set -euo pipefail

DEST=/downloads/yzy/agentlogs
LOGDIR=/downloads/yzy/logs
mkdir -p "$DEST" "$LOGDIR"

export http_proxy=http://127.0.0.1:7890
export https_proxy=http://127.0.0.1:7890
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890
export ALL_PROXY=http://127.0.0.1:7890
export HF_HUB_ENABLE_HF_TRANSFER=0

python3 - <<'PY'
import time
import urllib.request

proxy = urllib.request.ProxyHandler({
    "http": "http://127.0.0.1:7890",
    "https": "http://127.0.0.1:7890",
})
opener = urllib.request.build_opener(proxy)
urllib.request.install_opener(opener)

url = "https://huggingface.co/api/datasets/risenlab/agentlogs"
t = time.perf_counter()
with urllib.request.urlopen(url, timeout=30) as r:
    print("api", r.status, "sec", round(time.perf_counter() - t, 2))

url2 = (
    "https://huggingface.co/datasets/risenlab/agentlogs/resolve/main/"
    "agent_session_logs/part_00000_of_00505.parquet"
)
req = urllib.request.Request(url2, headers={"Range": "bytes=0-8388607"})
t = time.perf_counter()
with urllib.request.urlopen(req, timeout=120) as r:
    data = r.read()
elapsed = time.perf_counter() - t
print(
    "probe_bytes",
    len(data),
    "sec",
    round(elapsed, 2),
    "MBps",
    round(len(data) / 1e6 / elapsed, 2),
)
PY

if pgrep -f "huggingface_hub|hf download risenlab/agentlogs" >/dev/null 2>&1; then
  echo "download already running:"
  pgrep -af "huggingface_hub|hf download risenlab/agentlogs" || true
  exit 0
fi

cat >"$LOGDIR/run_download.py" <<'PY'
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="risenlab/agentlogs",
    repo_type="dataset",
    local_dir="/downloads/yzy/agentlogs",
    max_workers=8,
)
print("DOWNLOAD_COMPLETE")
PY

nohup env \
  http_proxy=http://127.0.0.1:7890 \
  https_proxy=http://127.0.0.1:7890 \
  HTTP_PROXY=http://127.0.0.1:7890 \
  HTTPS_PROXY=http://127.0.0.1:7890 \
  ALL_PROXY=http://127.0.0.1:7890 \
  HF_HUB_ENABLE_HF_TRANSFER=0 \
  python3 "$LOGDIR/run_download.py" \
  >"$LOGDIR/agentlogs_download.log" 2>&1 &

echo $! >"$LOGDIR/agentlogs_download.pid"
sleep 3
echo "PID=$(cat "$LOGDIR/agentlogs_download.pid")"
ps -p "$(cat "$LOGDIR/agentlogs_download.pid")" -o pid,etime,cmd || true
tail -n 40 "$LOGDIR/agentlogs_download.log" || true
