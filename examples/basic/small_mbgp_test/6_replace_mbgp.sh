#!/bin/bash

# Path to your local full bird directory
LOCAL_BIRD_DIR=/home/bashayer/seed-emulator-mbgp/examples/basic/small_mbgp_test/bird

# List of router container names
routers=(
#  as149r-router0-10.149.0.254
  as150r-router0-10.150.0.254
  as151r-router0-10.151.0.254
  as152r-router0-10.152.0.254
)

# Verify local bird directory exists
if [[ ! -d "$LOCAL_BIRD_DIR" ]]; then
  echo "❌ Local bird directory not found: $LOCAL_BIRD_DIR"
  exit 1
fi

for container in "${routers[@]}"; do
  container_id=$(docker ps -qf "name=$container")

  if [[ -z "$container_id" ]]; then
    echo "❌ Container not found or not running: $container"
    continue
  fi

  echo "🚮 Removing /bird in $container..."
  docker exec "$container_id" rm -rf /bird
  docker exec "$container_id" mkdir -p /bird

  echo "📁 Copying full bird dir contents to $container:/bird..."
  docker cp "$LOCAL_BIRD_DIR/." "$container_id":/bird

  echo "🔧 Running autoreconf and configure..."
  docker exec "$container_id" sh -c "cd /bird && autoreconf -fiv"
  docker exec "$container_id" sh -c "cd /bird && ./configure --sysconfdir=/etc/bird"

  echo "🔨 Running make install..."
  docker exec "$container_id" sh -c "cd /bird && make install"

  echo "✅ Done with $container"
done

echo "🎉 All containers updated with full bird source and rebuilt."
