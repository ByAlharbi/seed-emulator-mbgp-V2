#!/bin/bash

# Find all containers matching router, rs_ix, or -r
containers=$(docker ps -a --format '{{.ID}} {{.Names}} {{.Status}}' | grep -E 'router|rs_ix|\-r')

if [[ -z "$containers" ]]; then
  echo "No containers matching router, rs_ix, or -r found."
  exit 0
fi

echo "-- Checking container statuses and birdc responsiveness..."

all_good=true

while read -r container_id container_name container_status; do
  if [[ "$container_status" != Up* ]]; then
    echo "❌ $container_name is NOT running (status: $container_status)"
    all_good=false
  else
    echo "✅ $container_name is running. Checking birdc..."

    # Try to run 'birdc show status' with a timeout of 2 seconds
    docker exec "$container_id" timeout 2 birdc show status > /dev/null 2>&1

    if [[ $? -ne 0 ]]; then
      echo "   ❌ birdc not responding in $container_name (stuck or crashed)"
      all_good=false
    else
      echo "   ✅ birdc responded correctly."
    fi
  fi
done <<< "$containers"

if [ "$all_good" = true ]; then
  echo "✅✅ All routers are UP and birdc is healthy!"
else
  echo "⚠️⚠️ Some routers are NOT healthy (either down or birdc stuck)."
fi
