#!/bin/bash

echo "Enabling core dumps on all routers and route servers..."

# Get all router containers (including route servers)
router_containers=$(docker ps --format '{{.Names}}' | grep -E 'router|^rs_')

# Counter for progress
count=0
total=$(echo "$router_containers" | wc -l)

# Loop through each container
for container in $router_containers; do
    count=$((count + 1))
    echo "[$count/$total] Configuring $container..."
    
    # Enable unlimited core dumps
    docker exec $container sh -c "ulimit -c unlimited"
    
    # Set core dump pattern
    docker exec $container sh -c "echo '/tmp/core.%e.%p.%t' > /proc/sys/kernel/core_pattern"
    
    # Verify settings
    echo "  Core dump limit: $(docker exec $container sh -c 'ulimit -c')"
    echo "  Core pattern: $(docker exec $container sh -c 'cat /proc/sys/kernel/core_pattern')"
done

echo ""
echo "✅ Core dumps enabled on all $total routers"
echo "Core files will be saved as: /tmp/core.<executable>.<pid>.<timestamp>"
