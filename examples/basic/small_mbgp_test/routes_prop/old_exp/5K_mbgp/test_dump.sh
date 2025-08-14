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
tcpdump -i any -w "exp${EXP_NUM}.pcap" 'net 10.0.0.0/8 or tcp port 179 or tcp port 50051 ' > /dev/null 2>&1 &
TCPDUMP_PID=$!

# Start BIRD on only the two specific routers
echo "Starting BIRD on specific routers only..."
target_containers=("68deeb2cfb15" "cbf4b6a7008d")
#target_containers=("68deeb2cfb15" "828d95f5b4a0")
for container_id in "${target_containers[@]}"; do
    # Get container name for display
    container_name=$(docker ps --format '{{.Names}}' -f "id=$container_id" 2>/dev/null)
    
    if [[ -z "$container_name" ]]; then
        echo "  Warning: Container $container_id not found or not running"
        continue
    fi
    
    echo "  Starting BIRD on $container_name ($container_id)"
    docker exec $container_id bird
done

# Wait 20 seconds
echo "Waiting 10 seconds..."
sleep 10

# Stop tcpdump
echo "Stopping tcpdump..."
kill $TCPDUMP_PID

echo "Done. Capture saved to exp${EXP_NUM}.pcap"
