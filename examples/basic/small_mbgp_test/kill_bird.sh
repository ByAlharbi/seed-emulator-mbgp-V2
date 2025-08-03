#!/bin/bash

# Get matching container IDs
router_containers=$(docker ps --format '{{.ID}} {{.Names}}' | grep -E 'router|-r|rs' | awk '{print $1}')

if [[ -z "$router_containers" ]]; then
  echo "❌ No matching containers found."
  exit 1
fi

for container_id in $router_containers; do
  echo "🔪 Killing BIRD in $container_id..."

  pids=$(docker exec "$container_id" sh -c "ps aux | grep bird | grep -v grep | awk '{print \$2}'")

  if [[ -z "$pids" ]]; then
    echo "   ⚠️ No BIRD processes found."
    continue
  fi

  for pid in $pids; do
    echo "   🔫 Killing PID $pid"
    docker exec "$container_id" kill -9 "$pid"
  done

  echo "✅ Done with $container_id"
done

echo "🎯 All BIRD processes killed."
