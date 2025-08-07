#!/bin/bash

router_containers=$(docker ps --format '{{.ID}} {{.Names}}' | grep -E 'router|rs' | awk '{print $1}')
if [[ -z "$router_containers" ]]; then
  echo "No containers with 'router' in the name found."
  exit 0
fi

echo "Found router containers:"
docker ps --format '{{.Names}}' | grep router

# Loop through each container and kill BIRD processes
for container_id in $router_containers; do
  echo "#  Killing BIRD processes in container $container_id..."

  # Get PIDs of bird processes
  pids=$(docker exec $container_id sh -c "ps aux | grep bird | grep -v grep | awk '{print \$2}'")

  if [[ -z "$pids" ]]; then
    echo "   No BIRD processes found in $container_id."
    continue
  fi

  for pid in $pids; do
    echo "#   Killing PID $pid"
    docker exec $container_id kill -9 $pid
  done
  echo "--> Done with $container_id"
done

echo "## All BIRD processes have been killed."
