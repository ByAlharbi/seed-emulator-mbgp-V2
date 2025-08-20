#!/bin/bash

# Path to your local mbgp folder
LOCAL_MBGP_DIR=/home/bashayer/seed-emulator-mbgp/examples/basic/small_mbgp_test/bird/proto/bgp

# Check if local mbgp directory exists
if [[ ! -d "$LOCAL_MBGP_DIR" ]]; then
  echo "❌ Local bgp directory not found: $LOCAL_MBGP_DIR"
  exit 1
fi

# Get matching router container IDs (router, -r, or rs in name)
#router_containers=$(docker ps --format '{{.ID}} {{.Names}}' | grep -E 'router|-r|rs' | awk '{print $1}')
#router_containers='7f39b1650d6c'
router_containers='as141r-router0-10.141.0.254 as142r-router0-10.142.0.254'
#router_containers='5c7d838c2f02'
if [[ -z "$router_containers" ]]; then
  echo "❌ No matching router containers found."
  exit 1
fi

for container_id in $router_containers; do
  echo "🚮 Removing existing /bird/proto/bgp in container $container_id..."
  docker exec "$container_id" rm -rf /bird/proto/bgp

  echo "📁 Copying local mbgp folder to container $container_id..."
  docker cp "$LOCAL_MBGP_DIR" "$container_id":/bird/proto/bgp

  echo "🔨 Running 'make install' in container $container_id..."
  docker exec "$container_id" sh -c 'cd /bird && export CFLAGS="-g -O0 -fno-omit-frame-pointer" && make -j && make install'

  echo "✅ Done with container $container_id"
done

echo "🎉 All router containers updated with new mbgp folder."
