#!/usr/bin/env bash
PIDFILE=/downloads/yzy/logs/agentlogs_download.pid
LOG=/downloads/yzy/logs/agentlogs_download.log
DEST=/downloads/yzy/agentlogs
echo "=== process ==="
if [[ -f "$PIDFILE" ]]; then
  PID=$(cat "$PIDFILE")
  echo "pid=$PID"
  ps -p "$PID" -o pid,etime,%cpu,%mem,cmd || echo "NOT RUNNING"
else
  echo "no pidfile"
fi
echo "=== size ==="
du -sh "$DEST" 2>/dev/null || true
find "$DEST" -type f 2>/dev/null | wc -l
echo "=== df ==="
df -h /downloads | tail -n 1
echo "=== log tail ==="
tail -n 20 "$LOG" 2>/dev/null || true
grep -E "DOWNLOAD_COMPLETE|Error|Traceback" "$LOG" 2>/dev/null | tail -n 10 || true
