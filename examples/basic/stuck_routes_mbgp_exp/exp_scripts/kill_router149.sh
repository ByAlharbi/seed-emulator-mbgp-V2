#!/bin/bash

# Configuration
ROUTER149="as149r-router0-10.149.0.254"
DELAY_SECONDS=${1:-5}  # Default delay is 5 seconds if not specified

# Function to get container ID
get_container_id() {
    local name=$1
    local container_id=$(docker ps -qf "name=$name")
    if [[ -z "$container_id" ]]; then
        echo "❌ Container '$name' not found."
        exit 1
    fi
    echo "$container_id"
}

# Get Router 149 container ID
R149_ID=$(get_container_id $ROUTER149)
if [[ -z "$R149_ID" ]]; then
    echo "❌ Could not find Router 149 container. Aborting."
    exit 1
fi

echo "⏱️ Waiting $DELAY_SECONDS seconds before killing Router 149 BIRD process..."
sleep $DELAY_SECONDS

echo "🛑 Shutting down Router 149 BIRD process..."
# Get PIDs of bird processes in Router 149
pids=$(docker exec $R149_ID sh -c "ps aux | grep bird | grep -v grep | awk '{print \$2}'")

if [[ -z "$pids" ]]; then
    echo "   No BIRD processes found in Router 149."
    exit 1
else
    for pid in $pids; do
        echo "   Killing PID $pid on Router 149"
        docker exec $R149_ID kill -9 $pid
    done
    echo "✅ Router 149 BIRD process killed at $(date +"%H:%M:%S.%3N")"
fi
