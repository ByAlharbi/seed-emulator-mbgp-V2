#!/bin/bash

# === Step 1: Identify all router containers ===
router_containers=$(docker ps --format '{{.ID}} {{.Names}}' | grep router)

if [[ -z "$router_containers" ]]; then
  echo "❌ No running router containers found."
  exit 0
fi

echo "🔍 Found router containers:"
echo "$router_containers" | awk '{print $2}'

# === Step 2: Kill BIRD in all router containers ===
echo "🛑 Killing all BIRD processes..."
while read -r container_id container_name; do
  echo "# Killing BIRD in $container_name..."
  pids=$(docker exec "$container_id" sh -c "ps aux | grep bird | grep -v grep | awk '{print \$2}'")
  if [[ -n "$pids" ]]; then
    for pid in $pids; do
      docker exec "$container_id" kill -9 "$pid"
    done
  else
    echo "   No BIRD process found in $container_name."
  fi
done <<< "$router_containers"

# === Step 3: Generate unique pcap filename ===
i=1
while [[ -e "all_bgp_routes_$i.pcap" ]]; do
  ((i++))
done
DUMP_FILE="all_bgp_routes_$i.pcap"

# === Step 4: Start tcpdump ===
echo "📡 Starting tcpdump for 10.100.0.149, 150, 151, and 152..."
tcpdump -i any host 10.100.0.149 or host 10.100.0.150 or host 10.100.0.151 or host 10.100.0.152 -w "$DUMP_FILE" > tcpdump_stdout.log 2> tcpdump_stderr.log &
TCPDUMP_PID=$!
sleep 3

# === Step 5: Start BIRD in all routers at once ===
echo "🚀 Starting BIRD in all routers..."
while read -r container_id container_name; do
  echo "-- Starting BIRD in $container_name"
  docker exec "$container_id" mkdir -p /bird/mbgp_log
  docker exec -d "$container_id" sh -c "bird> /bird/mbgp_log/bird.log 2>&1 &"
done <<< "$router_containers"

# === Step 6: Wait 20 seconds ===
echo "⏳ Waiting 30 seconds for route propagation..."
sleep 30

# === Step 7: Determine next experiment number ===
ROUTE_COUNT_FILE="route_counts.txt"
if [[ -f $ROUTE_COUNT_FILE ]]; then
  EXP_NUM=$(( $(grep -c "^Exp " "$ROUTE_COUNT_FILE") + 1 ))
else
  EXP_NUM=1
fi

# === Step 8: Capture and append route counts ===
echo "📊 Capturing route counts..."
{
  echo ""
  echo "Exp $EXP_NUM:"
  echo "Router 149:"
  docker exec as149r-router0-10.149.0.254 birdc 'show route protocol x_as150 count'
  echo ""
  echo "Router 151:"
  docker exec as151r-router0-10.151.0.254 birdc 'show route protocol x_as150 count'
  echo ""
  echo "Router 152:"
  docker exec as152r-router0-10.152.0.254 birdc 'show route protocol x_as151 count'
} >> "$ROUTE_COUNT_FILE"

echo "✅ Appended results to $ROUTE_COUNT_FILE (Exp $EXP_NUM)"

# === Step 9: Stop tcpdump ===
kill $TCPDUMP_PID
echo "🛑 tcpdump stopped. PCAP saved as $DUMP_FILE"
