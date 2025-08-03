#!/bin/bash
# Monitor only the important routers for cleaner results
IMPORTANT_ROUTERS="as2r-router0|as3r-router0|as4r-router0|as11r-router0|as12r-router0|as150r-router0"

echo "timestamp,router,cpu_percent"
while true; do
    for container in $(docker ps --format '{{.Names}}' | grep -E "$IMPORTANT_ROUTERS"); do
        # Your CPU measurement code here
        cpu=$(docker exec $container top -bn1 | grep bird | awk '{print $9}' || echo "0")
        echo "$(date +%s.%3N),$container,$cpu"
    done
    sleep 0.5
done > cpu_measurements.csv
