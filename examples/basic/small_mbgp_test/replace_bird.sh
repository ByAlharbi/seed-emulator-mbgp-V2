#!/bin/bash

# Path to your local mbgp folder
LOCAL_MBGP_DIR=/home/bashayer/seed-emulator-mbgp/examples/basic/small_mbgp_test/bird/proto/mbgp

# Check if local mbgp directory exists
if [[ ! -d "$LOCAL_MBGP_DIR" ]]; then
  echo "❌ Local mbgp directory not found: $LOCAL_MBGP_DIR"
  exit 1
fi

# Get matching router container IDs (router, -r, or rs in name)
router_containers=$(docker ps --format '{{.ID}} {{.Names}}' | grep -E 'router|-r|rs' | awk '{print $1}')

if [[ -z "$router_containers" ]]; then
  echo "❌ No matching router containers found."
  exit 1
fi

for container_id in $router_containers; do
  echo "🚮 Removing existing /bird/proto/mbgp in container $container_id..."
  docker exec "$container_id" rm -rf /bird/proto/mbgp

  echo "📁 Copying local mbgp folder to container $container_id..."
  docker cp "$LOCAL_MBGP_DIR" "$container_id":/bird/proto/mbgp

  echo "🔨 Running 'make install' in container $container_id..."
  docker exec "$container_id" sh -c "cd /bird && make install"

  echo "✅ Done with container $container_id"
done

echo "🎉 All router containers updated with new mbgp folder."
