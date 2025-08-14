#!/bin/bash

# Determine experiment number
EXP_NUM=1
while [ -f "exp${EXP_NUM}.pcap" ]; do
    ((EXP_NUM++))
done

echo "Running Experiment ${EXP_NUM}"

# Get all router containers
router_containers=$(docker ps --format '{{.ID}} {{.Names}}' | grep -E 'router|rs' | awk '{print $1}')

if [[ -z "$router_containers" ]]; then
  echo "No containers with 'router' or 'rs' in the name found."
  exit 0
fi

echo "Found router containers:"
docker ps --format '{{.Names}}' | grep -E 'router|rs'

# 1. Kill all BIRD processes
echo "Killing all BIRD processes..."
for container_id in $router_containers; do
  echo "  Killing BIRD processes in container $container_id..."

  # Get PIDs of bird processes
  pids=$(docker exec $container_id sh -c "ps aux | grep bird | grep -v grep | awk '{print \$2}'")

  if [[ -z "$pids" ]]; then
    echo "   No BIRD processes found in $container_id."
    continue
  fi

  for pid in $pids; do
    echo "   Killing PID $pid"
    docker exec $container_id kill -9 $pid
  done
done

echo "All BIRD processes have been killed."
sleep 2

# 2. Start BIRD on routers 142, 143, 144
echo "Starting BIRD on routers AS142, AS143, AS144..."
for as_num in 142 143 144; do
    container_name="as${as_num}r-router0-10.${as_num}.0.254"
    echo "  Starting BIRD on $container_name"
    docker exec $container_name bird
done

# 3. Wait 5 seconds
echo "Waiting 5 seconds..."
sleep 5

# 4. Start tcpdump for AS144 (10.144.0.0/24) and port 50051
echo "Starting tcpdump for AS144 network and port 50051..."
tcpdump -i any -w "exp${EXP_NUM}.pcap" 'net 10.0.0.0/8 and tcp port 50051' > /dev/null 2>&1 &
TCPDUMP_PID=$!

# Small wait to ensure tcpdump is running
sleep 1

# 5. Start BIRD on router 141
echo "Starting BIRD on router AS141..."
docker exec as141r-router0-10.141.0.254 bird

# Wait 20 seconds
echo "Waiting 10 seconds..."
sleep 10

# Stop tcpdump
echo "Stopping tcpdump..."
kill $TCPDUMP_PID

echo "Done. Capture saved to exp${EXP_NUM}.pcap"
