#!/bin/bash

# Get all router containers
router_containers=$(docker ps --format '{{.ID}} {{.Names}}' | grep -E 'router|rs' | awk '{print $1}')

if [[ -z "$router_containers" ]]; then
  echo "No containers with 'router' or 'rs' in the name found."
  exit 0
fi

echo "Found router containers:"
docker ps --format '{{.Names}}' | grep -E 'router|rs'

# Start BIRD on all routers except AS150
echo "Starting BIRD on all routers except AS150..."
for container_id in $router_containers; do
    # Get container name
    container_name=$(docker ps --format '{{.Names}}' -f "id=$container_id")
    
    # Skip if this is AS150 router
    if [[ "$container_name" == "as150r-router0-10.150.0.254" ]]; then
        echo "  Skipping $container_name"
        continue
    fi
    
    echo "  Starting BIRD on $container_name"
    docker exec $container_id bird
done

echo "Done. BIRD started on all routers except AS150."
