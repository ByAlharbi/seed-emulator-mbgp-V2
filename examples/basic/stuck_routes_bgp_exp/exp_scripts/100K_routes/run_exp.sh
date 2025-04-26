#!/bin/bash

# === Step 1: Find all running router containers ===
router_containers=$(docker ps --format '{{.ID}} {{.Names}}' | grep router | awk '{print $1}')

if [[ -z "$router_containers" ]]; then
  echo "❌ No running router containers found."
  exit 0
fi

echo "🔍 Found router containers:"
docker ps --format '{{.Names}}' | grep router

# === Step 2: Kill BIRD in all router containers ===
echo "🛑 Killing existing BIRD processes..."
../kill_bird.sh

# === Step 3: Append routes to Router 150 ===
echo "🛠️ Appending static routes to Router 150..."
ROUTER150="as150r-router0-10.150.0.254"
r150_id=$(docker ps -qf "name=$ROUTER150")

if [[ -z "$r150_id" ]]; then
  echo "❌ Router 150 container not found."
  exit 1
fi

# Copy the routes file to the container
echo "📄 Copying route file to Router 150..."
docker cp ../route_150_static_routes.conf $r150_id:/tmp/

# Append the routes to bird.conf
echo "➕ Appending routes to Router 150 configuration..."
docker exec $r150_id sh -c "cat /tmp/route_150_static_routes.conf >> /etc/bird/bird.conf"
echo "✅ Routes appended to Router 150 configuration"

# === Step 4: Run tcpdump on the host for 151 & 152 silently ===
DUMP_FILE="all_bgp_routes.pcap"
echo "📡 Starting silent tcpdump for 10.100.0.151 and 10.100.0.152..."
tcpdump -i any host 10.100.0.151 or host 10.100.0.152 or host 10.100.0.150 -w "$DUMP_FILE" > tcpdump_stdout.log 2> tcpdump_stderr.log &
TCPDUMP_PID=$!

# Optional: Let tcpdump run for a short time before continuing
sleep 3

# === Step 5: Start BIRD and log output ===
echo "🚀 Starting BIRD..."
../run_bird.sh

# === Step 6: Optional: Stop tcpdump after N seconds (uncomment to auto-stop) ===
# sleep 60
# kill $TCPDUMP_PID && echo "🛑 tcpdump stopped."

echo "✅ BIRD processes restarted, routes injected to Router 150, and tcpdump running in background (PID: $TCPDUMP_PID)."
