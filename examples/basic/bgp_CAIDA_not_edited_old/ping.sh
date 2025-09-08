#!/bin/bash

# Get all containers with 'host0' in their name
hnode_containers=($(docker ps --format '{{.Names}}' | grep host0))

if [[ ${#hnode_containers[@]} -lt 2 ]]; then
  echo "Need at least two host0 containers to test connectivity."
  exit 1
fi

# Use the first one as the source
source_container="${hnode_containers[0]}"
echo "-- Using $source_container as source"

# Loop through all others and test ping
for target_container in "${hnode_containers[@]:1}"; do
  # Get IP address of the target container
  target_ip=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' "$target_container")

  if [[ -z "$target_ip" ]]; then
    echo "❌ Could not get IP for $target_container"
    continue
  fi

  echo "--> Pinging $target_container ($target_ip)..."
  docker exec "$source_container" ping -c 2 -W 1 "$target_ip" > /dev/null 2>&1

  if [[ $? -eq 0 ]]; then
    echo "   ✅ Reachable"
  else
    echo "   ❌ Unreachable"
  fi
done

echo "## Connectivity test complete from $source_container"
