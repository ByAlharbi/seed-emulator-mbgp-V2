#!/bin/bash

# Paths to the local files you want to copy
LOCAL_MBGP_C=/mydata/seed-emulator-mbgp/examples/basic/small_mbgp_test/bird/proto/mbgp/mbgp.c
LOCAL_MBGP_H=/mydata/seed-emulator-mbgp/examples/basic/small_mbgp_test/bird/proto/mbgp/mbgp.h

# Get all router containers dynamically
echo "🔍 Finding all router containers..."
router_containers=$(docker ps --format '{{.ID}} {{.Names}}' | grep -E 'router|_r|rs' | awk '{print $1}')

# Check that both local files exist
if [[ ! -f "$LOCAL_MBGP_C" ]]; then
  echo "❌ File not found: $LOCAL_MBGP_C"
  exit 1
fi

if [[ ! -f "$LOCAL_MBGP_H" ]]; then
  echo "❌ File not found: $LOCAL_MBGP_H"
  exit 1
fi

# Count containers for progress
total=$(echo "$router_containers" | wc -l)
count=0

echo "📊 Found $total router containers to update"

# Process each container
for container_id in $router_containers; do
  count=$((count + 1))
  
  # Get container name for display
  container_name=$(docker ps --format '{{.Names}}' -f "id=$container_id")
  
  echo ""
  echo "[$count/$total] Processing $container_name..."
  
  echo "  🧹 Removing old mbgp.c and mbgp.h..."
  docker exec "$container_id" rm -f /bird/proto/mbgp/mbgp.c
  docker exec "$container_id" rm -f /bird/proto/mbgp/mbgp.h

  echo "  📁 Copying new files..."
  docker cp "$LOCAL_MBGP_C" "$container_id":/bird/proto/mbgp/
  docker cp "$LOCAL_MBGP_H" "$container_id":/bird/proto/mbgp/

  echo "  🔨 Running 'make install'..."
  docker exec "$container_id" sh -c "cd /bird && make install"

  echo "  ✅ Updated: $container_name"
done

echo ""
echo "🎉 All $total containers updated successfully!"
