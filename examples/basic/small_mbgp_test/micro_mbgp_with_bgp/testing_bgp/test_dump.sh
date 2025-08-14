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

# Kill all BIRD processes
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

# Wait a moment for processes to die
sleep 2

# Start tcpdump
echo "Starting tcpdump..."
tcpdump -i any -w "exp${EXP_NUM}.pcap" '(host 10.109.0.142 or host 10.109.0.141)' > /dev/null 2>&1 &
TCPDUMP_PID=$!

# Start BIRD on all routers
echo "Starting BIRD on all routers..."
for container in $router_containers; do
    docker exec $container bird
done

# Wait 20 seconds
echo "Waiting 10 seconds..."
sleep 10

# Stop tcpdump
echo "Stopping tcpdump..."
kill $TCPDUMP_PID

echo "Done. Capture saved to exp${EXP_NUM}.pcap"
