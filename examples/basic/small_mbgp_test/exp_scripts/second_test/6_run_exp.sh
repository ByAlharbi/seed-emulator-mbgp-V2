#!/bin/bash

# === Configuration ===
PERF_DURATION=45  # seconds to profile
PERF_FREQ=999     # sampling frequency

# === Step 1: Kill all router processes ===
echo "🔍 Finding router containers..."
router_containers=$(docker ps --format '{{.ID}} {{.Names}}' | grep router)

if [[ -z "$router_containers" ]]; then
  echo "❌ No running router containers found."
  exit 0
fi

echo "Found routers:"
echo "$router_containers" | awk '{print "  - " $2}'

echo -e "\n🛑 Killing all BIRD processes..."
while read -r container_id container_name; do
  pids=$(docker exec "$container_id" sh -c "ps aux | grep bird | grep -v grep | awk '{print \$2}'" 2>/dev/null)
  if [[ -n "$pids" ]]; then
    echo "  Killing BIRD in $container_name"
    for pid in $pids; do
      docker exec "$container_id" kill -9 "$pid" 2>/dev/null
    done
  fi
done <<< "$router_containers"

sleep 3

# === Step 2: Extract container IDs ===
ROUTER149_ID=$(echo "$router_containers" | grep "as149r-router0-10.149.0.254" | awk '{print $1}')
ROUTER150_ID=$(echo "$router_containers" | grep "as150r-router0-10.150.0.254" | awk '{print $1}')
ROUTER151_ID=$(echo "$router_containers" | grep "as151r-router0-10.151.0.254" | awk '{print $1}')
ROUTER152_ID=$(echo "$router_containers" | grep "as152r-router0-10.152.0.254" | awk '{print $1}')

# === Step 3: Start neighbors first ===
echo -e "\n🚀 Starting BIRD in neighbor routers (149, 150, 152)..."

for rid in "$ROUTER149_ID" "$ROUTER150_ID" "$ROUTER152_ID"; do
  if [[ -n "$rid" ]]; then
    docker exec -d "$rid" sh -c "bird"
    echo "  ✓ Started BIRD in container ${rid:0:12}"
  fi
done

echo "⏳ Waiting 5 seconds for neighbors to initialize..."
sleep 5

# === Step 4: Prepare for profiling ===
echo -e "\n🎯 Preparing to profile Router 151..."

# Find unique filename
i=1
while [[ -e "bird_151_profile_${i}.data" ]]; do
  ((i++))
done
PERF_FILE="bird_151_profile_${i}.data"
REPORT_FILE="bird_151_report_${i}.txt"
CPU_LOG="bird_151_cpu_${i}.log"

# === Step 5: Start Router 151 ===
echo "🚀 Starting Router 151..."
docker exec -d "$ROUTER151_ID" sh -c "bird"

# Wait for BIRD to appear
echo "⏳ Waiting for BIRD process..."
for attempt in {1..10}; do
  BIRD_PID=$(docker top "$ROUTER151_ID" 2>/dev/null | grep bird | grep -v grep | awk '{print $2}' | head -1)
  if [[ -n "$BIRD_PID" ]]; then
    echo "✓ Found BIRD PID: $BIRD_PID"
    break
  fi
  sleep 0.5
done

if [[ -z "$BIRD_PID" ]]; then
  echo "❌ Failed to find BIRD process!"
  exit 1
fi

# === Step 6: Start profiling ===
echo -e "\n🔥 Starting performance profiling..."
echo "  - Duration: ${PERF_DURATION} seconds"
echo "  - Frequency: ${PERF_FREQ} Hz"
echo "  - Output: ${PERF_FILE}"

# Method 1: Direct perf record (more reliable)
sudo perf record -F $PERF_FREQ -p "$BIRD_PID" -g -o "$PERF_FILE" &
PERF_PID=$!

# Monitor CPU usage in parallel
{
  echo "Time,PID,CPU%,VSZ,RSS,Command" > "$CPU_LOG"
  for ((i=0; i<$PERF_DURATION; i++)); do
    STATS=$(ps -p "$BIRD_PID" -o pid,%cpu,vsz,rss,comm --no-headers 2>/dev/null || echo "0 0 0 0 -")
    echo "$(date +%H:%M:%S),$STATS" >> "$CPU_LOG"
    echo "  $(date +%H:%M:%S) - CPU: $(echo $STATS | awk '{print $2}')%"
    sleep 1
  done
} &
CPU_PID=$!

# Wait for profiling duration
echo -e "\n⏳ Profiling for ${PERF_DURATION} seconds..."
sleep $PERF_DURATION

# === Step 7: Stop profiling cleanly ===
echo -e "\n🛑 Stopping profiler..."
sudo kill -INT $PERF_PID 2>/dev/null
sleep 3

# Make sure perf has finished writing
if ps -p $PERF_PID > /dev/null 2>&1; then
  echo "  Waiting for perf to finish..."
  sudo kill -TERM $PERF_PID 2>/dev/null
  sleep 2
fi

# Wait for CPU monitor
wait $CPU_PID 2>/dev/null

# === Step 8: Verify and analyze data ===
echo -e "\n📊 Checking captured data..."

if [[ -f "$PERF_FILE" ]]; then
  FILE_SIZE=$(stat -c%s "$PERF_FILE" 2>/dev/null || echo "0")
  echo "  Perf data file size: $FILE_SIZE bytes"
  
  # Try to read header
  SAMPLES=$(sudo perf report -i "$PERF_FILE" --header-only 2>&1 | grep -E "samples|Events:" | head -1)
  echo "  Samples info: $SAMPLES"
  
  if [[ $FILE_SIZE -gt 10000 ]]; then
    echo -e "\n📈 Generating analysis reports..."
    
    # Basic report
    sudo perf report -i "$PERF_FILE" --stdio > "$REPORT_FILE" 2>&1
    
    # Top functions
    echo -e "\n🔝 Top 20 CPU consuming functions:"
    echo "===================================="
    sudo perf report -i "$PERF_FILE" --stdio --no-children 2>/dev/null | \
      grep -v "^#" | grep -v "^$" | head -25 || echo "Failed to extract functions"
    
    # Look for mBGP functions
    echo -e "\n🎯 mBGP-related functions:"
    sudo perf report -i "$PERF_FILE" --stdio 2>/dev/null | \
      grep -iE "(mbgp|decode_cpp|encode_route|send_update|protocol_lookup)" | head -20 || echo "No mBGP functions found"
    
    # String operations
    echo -e "\n📝 String operation functions:"
    sudo perf report -i "$PERF_FILE" --stdio 2>/dev/null | \
      grep -E "(strncpy|strcpy|memcpy|string)" | head -10 || echo "No string functions found"
      
  else
    echo "❌ Perf data file seems too small. Trying alternative analysis..."
    
    # Try with perf script
    sudo perf script -i "$PERF_FILE" 2>/dev/null | head -20
  fi
else
  echo "❌ Perf data file not found!"
fi

# === Step 9: Check route propagation ===
echo -e "\n📊 Checking route counts..."
for name in "149:x_as151" "150:x_as151" "152:x_as151"; do
  router=${name%:*}
  proto=${name#*:}
  echo "Router $router:"
  docker exec "as${router}r-router0-10.${router}.0.254" birdc "show route protocol $proto count" 2>/dev/null || echo "  No connection"
done

# === Step 10: Summary ===
echo -e "\n✅ Profiling complete!"
echo "📁 Output files:"
echo "  - Perf data: $PERF_FILE"
echo "  - Analysis: $REPORT_FILE"  
echo "  - CPU log: $CPU_LOG"

echo -e "\n💡 To analyze further:"
echo "  sudo perf report -i $PERF_FILE"
echo "  sudo perf report -i $PERF_FILE --stdio --no-children | less"
echo "  cat $CPU_LOG"
