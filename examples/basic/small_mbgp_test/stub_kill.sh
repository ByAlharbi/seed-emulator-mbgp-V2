#!/bin/bash

# Function to kill bird in stub AS containers
kill_stub_bird() {
    echo "🔍 Finding stub AS routers (AS 150-171)..."
    
    stub_containers=$(docker ps --format '{{.ID}} {{.Names}}' | grep -E 'as1[567][0-9]r-router' | awk '{print $1}')
    
    if [[ -z "$stub_containers" ]]; then
        echo "❌ No stub AS router containers found."
        return 1
    fi
    
    echo "🛑 Killing BIRD in stub AS routers..."
    for container_id in $stub_containers; do
        container_name=$(docker ps --format '{{.Names}}' -f "id=$container_id")
        echo "  ❌ Killing BIRD in $container_name..."
        
        # Get PIDs of bird processes
        pids=$(docker exec $container_id sh -c "ps aux | grep bird | grep -v grep | awk '{print \$2}'")
        
        if [[ -z "$pids" ]]; then
            echo "    ⚠️  No BIRD processes found in $container_name"
            continue
        fi
        
        for pid in $pids; do
            docker exec $container_id kill -9 $pid
            echo "    ✅ Killed BIRD process (PID: $pid)"
        done
    done
    
    echo "✅ All BIRD processes in stub ASes killed."
}

# Function to start bird in stub AS containers
start_stub_bird() {
    echo "🔍 Starting BIRD in stub AS routers (AS 150-171)..."
    
    stub_containers=$(docker ps --format '{{.ID}} {{.Names}}' | grep -E 'as1[567][0-9]r-router' | awk '{print $1}')
    
    if [[ -z "$stub_containers" ]]; then
        echo "❌ No stub AS router containers found."
        return 1
    fi
    
    for container_id in $stub_containers; do
        container_name=$(docker ps --format '{{.Names}}' -f "id=$container_id")
        echo "  🚀 Starting BIRD in $container_name..."
        
        # Create log directory
        docker exec "$container_id" mkdir -p /bird/mbgp_log
        
        # Start BIRD with logging
        docker exec -d "$container_id" sh -c "bird -d > /bird/mbgp_log/bird.log 2>&1 &"
        
        echo "  ✅ BIRD started in $container_name (logging to /bird/mbgp_log/bird.log)"
        
        # Wait 1 second before starting the next router
        echo "  ⏳ Waiting 1 second before next router..."
        sleep 1
    done
    
    echo "✅ All BIRD processes in stub ASes started with logging."
}

# Main execution
echo "🔄 Restarting BIRD in stub ASes only (AS 150-171)..."
echo "================================================"
echo

# Kill BIRD in stub ASes
kill_stub_bird

echo
echo "⏳ Waiting 2 seconds before restarting..."
sleep 2
echo

# Start BIRD in stub ASes
start_stub_bird

echo
echo "🎉 BIRD restart complete for stub ASes!"
echo "📊 Summary:"
echo "  - Killed BIRD in: AS 150-171 routers"
echo "  - Restarted BIRD in: AS 150-171 routers"
echo "  - Transit/Core routers: Untouched"
echo "  - Route servers: Untouched"
