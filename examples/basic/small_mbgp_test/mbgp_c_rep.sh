#!/bin/bash

# Paths to the local files you want to copy
LOCAL_MBGP_C=/home/bashayer/seed-emulator-mbgp/examples/basic/small_mbgp_test/bird/proto/mbgp/mbgp.c
LOCAL_MBGP_H=/home/bashayer/seed-emulator-mbgp/examples/basic/small_mbgp_test/bird/proto/mbgp/mbgp.h

# Check that both local files exist
if [[ ! -f "$LOCAL_MBGP_C" ]]; then
  echo "❌ File not found: $LOCAL_MBGP_C"
  exit 1
fi

if [[ ! -f "$LOCAL_MBGP_H" ]]; then
  echo "❌ File not found: $LOCAL_MBGP_H"
  exit 1
fi

# Get matching router container IDs
router_containers=$(docker ps --format '{{.ID}} {{.Names}}' | grep -E 'router|-r|rs' | awk '{print $1}')

if [[ -z "$router_containers" ]]; then
  echo "❌ No matching router containers found."
  exit 1
fi

for container_id in $router_containers; do
  echo "🧹 Removing old mbgp.c and mbgp.h in $container_id..."
  docker exec "$container_id" rm -f /bird/proto/mbgp/mbgp.c
  docker exec "$container_id" rm -f /bird/proto/mbgp/mbgp.h

  echo "📁 Copying new mbgp.c and mbgp.h to $container_id..."
  docker cp "$LOCAL_MBGP_C" "$container_id":/bird/proto/mbgp/
  docker cp "$LOCAL_MBGP_H" "$container_id":/bird/proto/mbgp/

  echo "🔨 Running 'make install' in $container_id..."
  docker exec "$container_id" sh -c "cd /bird && make install"

  echo "✅ Updated and rebuilt: $container_id"
done

echo "🎉 All matching containers updated with new mbgp.c and mbgp.h."
