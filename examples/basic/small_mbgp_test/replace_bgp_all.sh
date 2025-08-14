#!/bin/bash
set -Eeuo pipefail

# Path to your local BIRD source ROOT (the whole "bird" folder)
LOCAL_BIRD_DIR="/home/bashayer/seed-emulator-mbgp/examples/basic/small_mbgp_test/bird"

# Sanity checks
if [[ ! -d "$LOCAL_BIRD_DIR" ]]; then
  echo "❌ Local bird directory not found: $LOCAL_BIRD_DIR"
  exit 1
fi

# Get matching router container IDs (router, -r, or rs in name)
#router_containers=$(docker ps --format '{{.ID}} {{.Names}}' | grep -E 'router|-r|rs' | awk '{print $1}')
router_containers='7f39b1650d6c' 
#router_containers='5c7d838c2f02'
#router_containers='7f39b1650d6c 5c7d838c2f02'
router_containers='edbf1c614b2a f3a2d078107a'
if [[ -z "${router_containers:-}" ]]; then
  echo "❌ No matching router containers found."
  exit 1
fi

for container_id in $router_containers; do
  echo "🚮 Removing existing /bird in container $container_id..."
  docker exec "$container_id" rm -rf /bird

  echo "📁 Copying local bird folder to container $container_id..."
  # Copies the entire bird tree so it becomes /bird inside the container
  docker cp "$LOCAL_BIRD_DIR" "$container_id":/bird

  echo "🔧 Bootstrapping & building in container $container_id..."
  docker exec "$container_id" sh -lc '
    cd /bird
    # Ensure config dir exists
    mkdir -p /etc/bird
    # Autotools bootstrap + configure + build + install
    autoreconf -i
    ./configure --sysconfdir=/etc/bird
    make install
  '

  echo "✅ Done with container $container_id"
done

echo "🎉 All router containers updated with a fresh BIRD build and installed."
