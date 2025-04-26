#!/bin/bash

# List of router names and IP suffixes
declare -A routers=(
  [149]="as149r-router0-10.149.0.254"
  [150]="as150r-router0-10.150.0.254"
  [151]="as151r-router0-10.151.0.254"
  [152]="as152r-router0-10.152.0.254"
)

for id in "${!routers[@]}"; do
  container="${routers[$id]}"
  container_id=$(docker ps -qf "name=$container")

  if [[ -z "$container_id" ]]; then
    echo "❌ Router $id ($container) not found or not running."
    continue
  fi

  echo "🗑️ Removing /var/log/bird.log from Router $id ($container)..."
  docker exec "$container_id" rm -f /var/log/bird.log
done

echo "✅ bird.log removed from all running routers."
