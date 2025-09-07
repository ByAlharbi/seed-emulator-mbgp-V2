#!/bin/bash

# Script to restart BIRD on all router containers
# Kills all BIRD processes and restarts them

echo "Starting BIRD restart process on all router containers..."

# Get list of all router container names (excluding host containers and route servers)
ROUTER_CONTAINERS=$(sudo docker ps --format "table {{.Names}}" | grep -E "^as[0-9]+r-router0-" | tail -n +2)

if [ -z "$ROUTER_CONTAINERS" ]; then
    echo "No router containers found!"
    exit 1
fi

echo "Found $(echo "$ROUTER_CONTAINERS" | wc -l) router containers"
echo ""

# Phase 1: Kill BIRD on all containers
echo "=== PHASE 1: Killing BIRD on all router containers ==="
for container in $ROUTER_CONTAINERS; do
    echo "Killing BIRD on: $container"
    sudo docker exec "$container" bash -c 'kill -9 $(pidof bird) 2>/dev/null || echo "  No BIRD processes found"'
done

echo ""
echo "Waiting 2 seconds for all processes to terminate..."
sleep 2

# Phase 2: Start BIRD on all containers
echo ""
echo "=== PHASE 2: Starting BIRD on all router containers ==="
for container in $ROUTER_CONTAINERS; do
    echo "Starting BIRD on: $container"
    sudo docker exec "$container" bash -c 'bird'
    
    # Quick check if it started
    if sudo docker exec "$container" bash -c 'pidof bird > /dev/null 2>&1'; then
        echo "  ✓ Started successfully"
    else
        echo "  ✗ Failed to start"
    fi
done

echo "BIRD restart process completed!"

# Optional: Show summary of BIRD processes
echo ""
echo "=== BIRD Process Summary ==="
for container in $ROUTER_CONTAINERS; do
    PID=$(sudo docker exec "$container" bash -c 'pidof bird 2>/dev/null' || echo "NOT RUNNING")
    echo "$container: BIRD PID = $PID"
done
