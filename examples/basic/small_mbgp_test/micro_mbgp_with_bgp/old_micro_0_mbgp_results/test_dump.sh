#!/bin/bash

# Get all router containers
router_containers=$(docker ps --format '{{.ID}} {{.Names}}' | grep -E 'router|rs' | awk '{print $1}')

# Kill all BIRD processes
echo "Killing all BIRD processes..."
for container in $router_containers; do
    docker exec $container pkill bird || true
done

# Wait a moment for processes to die
sleep 2

# Start tcpdump
echo "Starting tcpdump..."
tcpdump -i any -w capture.pcap 'net 10.0.0.0/8' > /dev/null 2>&1 &
TCPDUMP_PID=$!

# Start BIRD on all routers
echo "Starting BIRD on all routers..."
for container in $router_containers; do
    docker exec $container bird
done

# Wait 20 seconds
echo "Waiting 20 seconds..."
sleep 20

# Stop tcpdump
echo "Stopping tcpdump..."
kill $TCPDUMP_PID

echo "Done. Capture saved to capture.pcap"
