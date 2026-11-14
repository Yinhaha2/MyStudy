#!/usr/bin/env bash
set -eu
mkdir -p /downloads/yzy/agentlogs /downloads/yzy/logs
cd /downloads/yzy/logs
nohup env \
  http_proxy=http://127.0.0.1:7890 \
  https_proxy=http://127.0.0.1:7890 \
  HTTP_PROXY=http://127.0.0.1:7890 \
  HTTPS_PROXY=http://127.0.0.1:7890 \
  ALL_PROXY=http://127.0.0.1:7890 \
  HF_HUB_ENABLE_HF_TRANSFER=0 \
  python3 /downloads/yzy/logs/run_download.py \
  > /downloads/yzy/logs/agentlogs_download.log 2>&1 &
echo $! > /downloads/yzy/logs/agentlogs_download.pid
sleep 4
echo PID=$(cat /downloads/yzy/logs/agentlogs_download.pid)
ps -p "$(cat /downloads/yzy/logs/agentlogs_download.pid)" -o pid,etime,cmd || true
tail -n 40 /downloads/yzy/logs/agentlogs_download.log || true
