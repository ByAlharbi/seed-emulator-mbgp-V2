#!/bin/bash

# Path to your local mbgp folder
LOCAL_MBGP_DIR=/home/bashayer/seed-emulator-mbgp/examples/basic/stuck_routes_mbgp_exp/bird

# List of router container names
routers=(
  as149r-router0-10.149.0.254
  as150r-router0-10.150.0.254
  as151r-router0-10.151.0.254
  as152r-router0-10.152.0.254
)

# Check if local mbgp directory exists
if [[ ! -d "$LOCAL_MBGP_DIR" ]]; then
  echo "❌ Local mbgp directory not found: $LOCAL_MBGP_DIR"
  exit 1
fi

for container in "${routers[@]}"; do
  container_id=$(docker ps -qf "name=$container")

  if [[ -z "$container_id" ]]; then
    echo "❌ Container not found or not running: $container"
    continue
  fi

  echo "🚮 Removing existing /bird/proto/mbgp in $container..."
  docker exec "$container_id" rm -rf /bird

  echo "📁 Copying local mbgp folder to $container..."
  docker cp "$LOCAL_MBGP_DIR" "$container_id":/bird

  echo "🔨 Running 'make install' in $container..."
  docker exec "$container_id" sh -c "cd /bird && autoreconf"
  docker exec "$container_id" sh -c "cd /bird && ./configure --sysconfdir=/etc/bird"
  docker exec "$container_id" sh -c "cd /bird && make install"

  echo "✅ Done with $container"
done

echo "🎉 All containers updated with new mbgp folder."
