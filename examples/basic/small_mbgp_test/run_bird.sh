#!/bin/bash

# Get matching container IDs
router_containers=$(docker ps --format '{{.ID}} {{.Names}}' | grep -E 'router|-r|rs' | awk '{print $1}')

if [[ -z "$router_containers" ]]; then
  echo "❌ No matching containers found."
  exit 1
fi

for container_id in $router_containers; do
  echo "🚀 Starting BIRD in $container_id..."
  docker exec "$container_id" bird
  echo "✅ bird started in $container_id"
done

echo "🎉 All BIRD processes started."
