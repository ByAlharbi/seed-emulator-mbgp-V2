#!/bin/bash

# Paths to the local files you want to copy
LOCAL_MBGP_C=/home/bashayer/seed-emulator-mbgp/examples/basic/stuck_routes_mbgp_exp/bird/proto/bgp/attrs.c
LOCAL_EVENT_C=/home/bashayer/seed-emulator-mbgp/examples/basic/stuck_routes_mbgp_exp/bird/proto/mbgp/mbgp.h

# List of router container names
routers=(
#  as149r-router0-10.149.0.254
#  as150r-router0-10.150.0.254
  as151r-router0-10.151.0.254
  as152r-router0-10.152.0.254
)

# Check that both local files exist
if [[ ! -f "$LOCAL_MBGP_C" ]]; then
  echo "❌ File not found: $LOCAL_MBGP_C"
  exit 1
fi

if [[ ! -f "$LOCAL_EVENT_C" ]]; then
  echo "❌ File not found: $LOCAL_EVENT_C"
  exit 1
fi

for container in "${routers[@]}"; do
  container_id=$(docker ps -qf "name=$container")

  if [[ -z "$container_id" ]]; then
    echo "❌ Container not found or not running: $container"
    continue
  fi

  echo "🧹 Removing old mbgp.c and event.c in $container..."
  docker exec "$container_id" rm -f /bird/proto/bgp/attrs.c
  #docker exec "$container_id" rm -f /bird/proto/mbgp/mbgp.h

  echo "📁 Copying new mbgp.c and event.c to $container..."
  docker cp "$LOCAL_MBGP_C" "$container_id":/bird/proto/bgp/
  #docker cp "$LOCAL_EVENT_C" "$container_id":/bird/proto/mbgp/

  echo "🔨 Running 'make install' in $container..."
  docker exec "$container_id" sh -c "cd /bird && make install"

  echo "✅ Updated and rebuilt: $container"
done

echo "🎉 All containers updated successfully."
