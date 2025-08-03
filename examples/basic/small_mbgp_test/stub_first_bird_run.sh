#!/bin/bash

# Function to start bird in containers matching a pattern
start_bird_for_pattern() {
    local pattern=$1
    local description=$2
    local delay=$3
    
    echo "🔍 Starting BIRD for $description..."
    
    containers=$(docker ps --format '{{.ID}} {{.Names}}' | grep -E "$pattern" | awk '{print $1}')
    
    if [[ -z "$containers" ]]; then
        echo "⚠️  No $description containers found."
        return
    fi
    
    for container_id in $containers; do
        container_name=$(docker ps --format '{{.Names}}' -f "id=$container_id")
        echo "  🚀 Starting BIRD in $container_name..."
        docker exec "$container_id" bird
        echo "  ✅ BIRD started in $container_name"
    done
    
    if [[ -n "$delay" ]]; then
        echo "⏳ Waiting $delay seconds before continuing..."
        sleep $delay
    fi
}

echo "🎯 Starting BIRD processes in reversed order..."
echo

# 1. Start stub AS routers (AS 150-171)
start_bird_for_pattern 'as1[567][0-9]r-router' "stub AS routers (AS 150-171)" 3

# 2. Start route servers at IXes
start_bird_for_pattern 'rs_ix_ix|as10[0-9]rs-' "route servers" 2

# 3. Start core/transit routers (AS 2, 3, 4, 11, 12)
start_bird_for_pattern 'as[234]r-router|as1[12]r-router' "core/transit routers (AS 2, 3, 4, 11, 12)" 0

echo
echo "🎉 All BIRD processes started in reversed order!"
echo "📊 Summary:"
echo "  - Stub AS routers: Started first"
echo "  - Route servers: Started second"  
echo "  - Core/transit routers: Started last"
