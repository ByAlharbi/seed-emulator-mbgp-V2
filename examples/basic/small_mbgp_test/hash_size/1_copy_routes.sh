#!/bin/bash

# Router details
AS_NUM="171"
ROUTER_NAME="as${AS_NUM}r-router0-10.${AS_NUM}.0.254"
ROUTE_FILE="route_${AS_NUM}_static_routes.conf"

# Check if route file exists
if [[ ! -f "$ROUTE_FILE" ]]; then
    echo "❌ Error: $ROUTE_FILE not found in current directory"
    exit 1
fi

# Get container ID
CONTAINER_ID=$(docker ps --format '{{.ID}} {{.Names}}' | grep "$ROUTER_NAME" | awk '{print $1}')

if [[ -z "$CONTAINER_ID" ]]; then
    echo "❌ Error: Router $ROUTER_NAME not found"
    exit 1
fi

echo "📄 Copying $ROUTE_FILE to $ROUTER_NAME..."
docker cp "$ROUTE_FILE" "$CONTAINER_ID:/tmp/"

echo "➕ Appending routes to bird.conf..."
docker exec "$CONTAINER_ID" sh -c "cat /tmp/$ROUTE_FILE >> /etc/bird/bird.conf"

echo "✅ Done! Routes added to $ROUTER_NAME"

