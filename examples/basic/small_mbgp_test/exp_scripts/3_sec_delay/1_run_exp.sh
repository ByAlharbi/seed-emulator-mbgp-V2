#!/bin/bash

# === Step 1: Kill all router processes ===
router_containers=$(docker ps --format '{{.ID}} {{.Names}}' | grep router)

if [[ -z "$router_containers" ]]; then
  echo "❌ No running router containers found."
  exit 0
fi

echo "🔍 Found router containers:"
echo "$router_containers" | awk '{print $2}'

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

# === Step 2: Start routers 149, 151, 152 ===
echo "🚀 Starting BIRD in routers 149, 151, 152..."

# Start Router 149
ROUTER149_NAME="as149r-router0-10.149.0.254"
ROUTER149_ID=$(echo "$router_containers" | grep "$ROUTER149_NAME" | awk '{print $1}')
if [[ -n "$ROUTER149_ID" ]]; then
  echo "-- Starting BIRD in Router 149"
  docker exec "$ROUTER149_ID" mkdir -p /bird/mbgp_log
  docker exec -d "$ROUTER149_ID" sh -c "bird -d > /bird/mbgp_log/bird.log 2>&1 &"
else
  echo "❌ Router 149 container not found."
fi

# Start Router 151
ROUTER151_NAME="as151r-router0-10.151.0.254"
ROUTER151_ID=$(echo "$router_containers" | grep "$ROUTER151_NAME" | awk '{print $1}')
if [[ -n "$ROUTER151_ID" ]]; then
  echo "-- Starting BIRD in Router 151"
  docker exec "$ROUTER151_ID" mkdir -p /bird/mbgp_log
  docker exec -d "$ROUTER151_ID" sh -c "bird -d > /bird/mbgp_log/bird.log 2>&1 &"
else
  echo "❌ Router 151 container not found."
fi

# Start Router 152
ROUTER152_NAME="as152r-router0-10.152.0.254"
ROUTER152_ID=$(echo "$router_containers" | grep "$ROUTER152_NAME" | awk '{print $1}')
if [[ -n "$ROUTER152_ID" ]]; then
  echo "-- Starting BIRD in Router 152"
  docker exec "$ROUTER152_ID" mkdir -p /bird/mbgp_log
  docker exec -d "$ROUTER152_ID" sh -c "bird -d > /bird/mbgp_log/bird.log 2>&1 &"
else
  echo "❌ Router 152 container not found."
fi

echo "⏳ Waiting 2 seconds for routers to initialize..."
sleep 2

# === Step 3: Add routes to Router 150 ===
echo "🛠️ Appending static routes to Router 150..."
ROUTER150_NAME="as150r-router0-10.150.0.254"
ROUTER150_ID=$(echo "$router_containers" | grep "$ROUTER150_NAME" | awk '{print $1}')

if [[ -z "$ROUTER150_ID" ]]; then
  echo "❌ Router 150 container not found."
  exit 1
fi

echo "📄 Copying route file to Router 150..."
docker cp ../route_150_static_routes.conf "$ROUTER150_ID":/tmp/

echo "➕ Appending routes to Router 150 configuration..."
docker exec "$ROUTER150_ID" sh -c "cat /tmp/route_150_static_routes.conf >> /etc/bird/bird.conf"
echo "✅ Routes appended to Router 150 configuration"

# === Step 4: Start tcpdump on all containers ===
echo "📡 Starting tcpdump for all containers..."

# Generate unique pcap filename
i=1
while [[ -e "all_bgp_routes_$i.pcap" ]]; do
  ((i++))
done
DUMP_FILE="all_bgp_routes_$i.pcap"

tcpdump -i any host 10.100.0.149 or host 10.100.0.150 or host 10.100.0.151 or host 10.100.0.152 -w "$DUMP_FILE" > tcpdump_stdout.log 2> tcpdump_stderr.log &
TCPDUMP_PID=$!
sleep 3

# === Step 5: Start Router 150 ===
echo "🚀 Starting BIRD in Router 150..."
docker exec "$ROUTER150_ID" mkdir -p /bird/mbgp_log
docker exec -d "$ROUTER150_ID" sh -c "bird -d > /bird/mbgp_log/bird.log 2>&1 &"

# === Step 6: Wait for route propagation ===
echo "⏳ Waiting 20 seconds for route propagation..."
sleep 20

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
