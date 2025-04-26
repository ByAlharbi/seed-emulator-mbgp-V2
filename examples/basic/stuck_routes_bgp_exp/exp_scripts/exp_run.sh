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
./kill_bird.sh

# === Step 3: Append new routes using Python ===
echo "🛠️ Generating and appending new routes using Python..."
python3 generate_IPs_py.py

# === Step 4: Run tcpdump on the host for 151 & 152 silently ===
DUMP_FILE="all_bgp_routes.pcap"
echo "📡 Starting silent tcpdump for 10.100.0.151 and 10.100.0.152..."
tcpdump -i any host 10.100.0.151 or host 10.100.0.152 -w "$DUMP_FILE" > tcpdump_stdout.log 2> tcpdump_stderr.log &
TCPDUMP_PID=$!

# Optional: Let tcpdump run for a short time before continuing
sleep 3

# === Step 5: Start BIRD and log output ===
echo "🚀 Starting BIRD..."
./run_bird.sh

# === Step 6: Optional: Stop tcpdump after N seconds (uncomment to auto-stop) ===
# sleep 60
# kill $TCPDUMP_PID && echo "🛑 tcpdump stopped."

echo "✅ BIRD processes restarted, routes injected via Python, and tcpdump running in background (PID: $TCPDUMP_PID)."
