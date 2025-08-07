#!/bin/bash

# Get all container IDs with 'router' in their name
router_containers=$(docker ps --format '{{.ID}} {{.Names}}' | grep -E 'router|rs' | awk '{print $1}')
if [[ -z "$router_containers" ]]; then
  echo "No containers with 'router' in the name found."
  exit 0
fi

for container_id in $router_containers; do
  echo "-- Setting up BIRD in $container_id..."
  #docker exec $container_id mkdir -p /bird/mbgp_log
  #docker exec -d $container_id sh -c "bird"
  docker exec -d $container_id sh -c "bird" 
done

echo "DONE"
