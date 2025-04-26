#!/bin/bash

# === Configuration Variables ===
ROUTER149="as149r-router0-10.149.0.254"
ROUTER150="as150r-router0-10.150.0.254"
ROUTER151="as151r-router0-10.151.0.254"
ROUTER152="as152r-router0-10.152.0.254"
DUMP_FILE="all_bgp_routes.pcap"
KILL_DELAY=5  # Seconds to wait before killing Router 149 (adjust as needed)

# Colors for better readability
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to get container ID by name
get_container_id() {
    local name=$1
    local container_id=$(docker ps -qf "name=$name")
    if [[ -z "$container_id" ]]; then
        echo -e "${RED}❌ Container '$name' not found.${NC}"
        return 1
    fi
    echo "$container_id"
}

# Function to kill Router 149's BIRD process with delay
kill_router149() {
    local delay=$1
    local r149_id=$(get_container_id $ROUTER149)
    
    if [[ -z "$r149_id" ]]; then
        echo -e "${RED}❌ Could not find Router 149 container. Cannot schedule shutdown.${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}⏱️ Waiting $delay seconds before killing Router 149 BIRD process...${NC}"
    sleep $delay
    
    echo -e "${RED}🛑 Shutting down Router 149 BIRD process...${NC}"
    # Get PIDs of bird processes in Router 149
    pids=$(docker exec $r149_id sh -c "ps aux | grep bird | grep -v grep | awk '{print \$2}'")
    
    if [[ -z "$pids" ]]; then
        echo "   No BIRD processes found in Router 149."
        return 1
    else
        for pid in $pids; do
            echo "   Killing PID $pid on Router 149"
            docker exec $r149_id kill -9 $pid
        done
        echo -e "${GREEN}✅ Router 149 BIRD process killed at $(date +"%H:%M:%S.%3N")${NC}"
    fi
}

# === Step 1: Find all running router containers ===
router_containers=$(docker ps --format '{{.ID}} {{.Names}}' | grep router | awk '{print $1}')

if [[ -z "$router_containers" ]]; then
  echo -e "${RED}❌ No running router containers found.${NC}"
  exit 0
fi

echo -e "${BLUE}🔍 Found router containers:${NC}"
docker ps --format '{{.Names}}' | grep router

# === Step 2: Kill BIRD in all router containers ===
echo -e "${RED}🛑 Killing existing BIRD processes...${NC}"
./kill_bird.sh

# === Step 3: Generate non-overlapping routes for Router 149 and 150 ===
echo -e "${BLUE}🛠️ Generating non-overlapping routes for Router 149 (100) and Router 150 (100K)...${NC}"
python3 optimized_route_generator.py

# === Step 4: Run tcpdump on the host for BGP traffic ===
echo -e "${BLUE}📡 Starting tcpdump for BGP traffic...${NC}"
tcpdump -i any host 10.100.0.149 or host 10.100.0.150 or host 10.100.0.151 or host 10.100.0.152 or host 10.150.0.150 -w "$DUMP_FILE" > tcpdump_stdout.log 2> tcpdump_stderr.log &
TCPDUMP_PID=$!

# Let tcpdump initialize
sleep 2

# === Step 5: Start BIRD on all routers ===
echo -e "${GREEN}🚀 Starting BIRD on all routers at $(date +"%H:%M:%S.%3N")...${NC}"
./run_bird.sh

# === Step 6: Kill Router 149 with timing delay (in background) ===
echo -e "${YELLOW}⏱️ Scheduling Router 149 shutdown in $KILL_DELAY seconds...${NC}"
kill_router149 $KILL_DELAY &
KILL_PID=$!

# === Step 7: Let the experiment run ===
echo -e "${BLUE}🔬 Running experiment for 120 seconds...${NC}"
echo "   Router 150 should be sending 100K updates to Router 151"
echo "   Router 149 will be killed during this process to create withdrawal scenario"

# Show progress bar for 120 seconds
for i in {1..120}; do
    echo -ne "${YELLOW}Progress: ${i}/120 seconds${NC}\r"
    sleep 1
done
echo -e "\n"

# === Step 8: Ensure kill script has finished ===
if ps -p $KILL_PID > /dev/null; then
    echo "Waiting for Router 149 kill process to complete..."
    wait $KILL_PID
fi

# === Step 9: Stop tcpdump ===
echo -e "${RED}🛑 Stopping tcpdump...${NC}"
kill $TCPDUMP_PID
wait $TCPDUMP_PID 2>/dev/null

echo ""
echo -e "${GREEN}✅ BGP experiment completed!${NC}"
echo -e "Packet capture saved to ${BLUE}$DUMP_FILE${NC}"
