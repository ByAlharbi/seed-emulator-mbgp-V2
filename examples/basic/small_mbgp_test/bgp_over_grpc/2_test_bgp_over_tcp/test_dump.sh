#!/bin/bash
set -euo pipefail

# ---------- experiment id ----------
EXP_NUM=1
while [ -f "exp${EXP_NUM}.pcap" ]; do ((EXP_NUM++)); done
echo "Running Experiment ${EXP_NUM}"

# ---------- containers ----------
router_containers=$(docker ps --format '{{.ID}} {{.Names}}' | grep -E 'router|rs' | awk '{print $1}')
# hard-pinned list (your note); comment this out if you want auto-detect above
router_containers='7c0dbcee9680 7fec6f92fb7b'
if [[ -z "${router_containers}" ]]; then
  echo "No containers with 'router' or 'rs' in the name found."
  exit 0
fi

echo "Found router containers:"
docker ps --format '{{.Names}}' | grep -E 'router|rs' || true

# ---------- kill all bird ----------
echo "Killing all BIRD processes..."
for container_id in $router_containers; do
  echo "  Killing BIRD in $container_id..."
  pids=$(docker exec "$container_id" sh -c "ps aux | grep bird | grep -v grep | awk '{print \$2}'" || true)
  if [[ -z "$pids" ]]; then
    echo "   No BIRD processes found in $container_id."
    continue
  fi
  for pid in $pids; do docker exec "$container_id" kill -9 "$pid" || true; done
done
echo "All BIRD processes have been killed."
sleep 2

# ---------- tcpdump ----------
echo "Starting tcpdump..."
tcpdump -i any -w "exp${EXP_NUM}.pcap" '(host 10.109.0.142 or host 10.109.0.141)' > /dev/null 2>&1 &
TCPDUMP_PID=$!

# ---------- start birds ----------
echo "Starting BIRD on all routers..."
for container in $router_containers; do
  docker exec -d "$container" bird
done

# ---------- CPU monitor (per-container) ----------
PERF_DURATION=60     # seconds (match your wait)
CPU_MON_PIDS=()

start_cpu_monitor() {
  local cid="$1"
  local cname
  cname=$(docker ps --filter "id=$cid" --format '{{.Names}}' | head -1)
  local cpu_log="cpu_${cname:-$cid}_exp${EXP_NUM}.log"

  # Find BIRD host PID (docker top shows host PIDs)
  local bird_pid=""
  for _ in {1..20}; do
    # works on recent Docker: show PID + COMM, then pick 'bird'
    bird_pid=$(docker top "$cid" -eo pid,comm 2>/dev/null | awk '$2=="bird"{print $1; exit}')
    [[ -n "$bird_pid" ]] && break
    sleep 0.5
  done

  if [[ -z "$bird_pid" ]]; then
    echo "WARN: Could not find BIRD PID in $cid; skipping CPU log."
    return 0
  fi

  {
    echo "Time,PID,CPU%,VSZ,RSS,Command"
    for ((i=0; i<PERF_DURATION; i++)); do
      # ps on host with host PID from docker top
      STATS=$(ps -p "$bird_pid" -o pid,%cpu,vsz,rss,comm --no-headers 2>/dev/null || echo "0 0 0 0 -")
      echo "$(date +%H:%M:%S),$STATS"
      sleep 1
    done
  } > "$cpu_log" &
  CPU_MON_PIDS+=($!)
  echo "CPU monitor started for ${cname:-$cid} (PID $bird_pid) → $cpu_log"
}

echo "Starting CPU monitors..."
for cid in $router_containers; do start_cpu_monitor "$cid"; done

# ---------- run window ----------
echo "Waiting ${PERF_DURATION} seconds..."
sleep "${PERF_DURATION}"

# ---------- stop ----------
echo "Stopping tcpdump..."
kill "$TCPDUMP_PID" 2>/dev/null || true

# Wait for all CPU monitors to finish cleanly
for mpid in "${CPU_MON_PIDS[@]:-}"; do wait "$mpid" 2>/dev/null || true; done

echo "Done. Capture saved to exp${EXP_NUM}.pcap"
echo "CPU logs:"
ls -1 cpu_*_exp${EXP_NUM}.log 2>/dev/null || echo "  (none)"
