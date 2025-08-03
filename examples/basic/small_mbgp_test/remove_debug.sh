#!/bin/bash

# Match all relevant containers
router_containers=$(docker ps --format '{{.ID}} {{.Names}}' | grep -E 'router|-r|rs' | awk '{print $1}')

if [[ -z "$router_containers" ]]; then
  echo "❌ No matching containers found."
  exit 1
fi

for container_id in $router_containers; do
  echo "🔍 Checking /etc/bird/bird.conf in $container_id..."

  # Extract the first two lines
  lines=$(docker exec "$container_id" head -n 2 /etc/bird/bird.conf)

  if [[ "$lines" == *'log "/var/log/bird.log" all;'* && "$lines" == *'debug protocols all;'* ]]; then
    echo "🧹 Found debug lines. Removing them from $container_id..."

    # Remove the first two lines and overwrite the file
    docker exec "$container_id" sh -c "tail -n +3 /etc/bird/bird.conf > /etc/bird/bird.tmp && mv /etc/bird/bird.tmp /etc/bird/bird.conf"

    echo "✅ Cleaned bird.conf in $container_id"
  else
    echo "✔️ bird.conf is already clean in $container_id"
  fi
done

echo "🎉 All containers processed."
