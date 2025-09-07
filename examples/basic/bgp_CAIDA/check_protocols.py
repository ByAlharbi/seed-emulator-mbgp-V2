#!/bin/bash

# Script to show BGP protocols on all router containers
# Runs 'birdc show protocols' on each router

echo "Showing BGP protocols on all router containers..."
echo "================================================"

# Get list of all router container names (excluding host containers and route servers)
ROUTER_CONTAINERS=$(sudo docker ps --format "table {{.Names}}" | grep -E "^as[0-9]+r-router0-" | tail -n +2)

if [ -z "$ROUTER_CONTAINERS" ]; then
    echo "No router containers found!"
    exit 1
fi

echo "Found $(echo "$ROUTER_CONTAINERS" | wc -l) router containers"
echo ""

# Show protocols on each container
for container in $ROUTER_CONTAINERS; do
    echo "=== $container ==="
    
    # Check if BIRD is running first
    if sudo docker exec "$container" bash -c 'pidof bird > /dev/null 2>&1'; then
        sudo docker exec "$container" birdc show protocols
    else
        echo "BIRD is not running on this container"
    fi
    
    echo ""
done

echo "Protocol status check completed!"
