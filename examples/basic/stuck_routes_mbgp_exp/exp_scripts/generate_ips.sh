#!/bin/bash

# Find container ID by name
container_name="as150r-router0-10.150.0.254"
container_id=$(docker ps -qf "name=$container_name")

if [[ -z "$container_id" ]]; then
  echo "Container named '$container_name' not found."
  exit 1
fi

# Static block header
static_block="protocol static static_routes {\n    ipv4 { import all; };"

# Generate 10,000 routes
count=0
max_routes=10000
via_ip="10.100.0.150"

while [[ $count -lt $max_routes ]]; do
  octet1=$((RANDOM % 223 + 1))
  [[ $octet1 -eq 10 ]] && continue
  octet2=$((RANDOM % 256))
  octet3=$((RANDOM % 256))
  octet4=0
  prefix_len=$((16 + RANDOM % 9))  # Random prefix length between /16 and /24

  route="    route $octet1.$octet2.$octet3.$octet4/$prefix_len via $via_ip;"
  static_block+="\n$route"
  ((count++))
done

# Close the block
static_block+="\n}"

# Escape for bash and pass to docker exec
escaped_block=$(echo -e "$static_block")

# Append to bird.conf inside the container
docker exec --workdir /etc/bird $container_id /bin/bash -c "echo -e \"$escaped_block\" >> bird.conf"

# Reload BIRD configuration
#docker exec $container_id /bin/bash -c "birdc configure"

echo "## Added $max_routes routes to bird.conf in container $container_name."
