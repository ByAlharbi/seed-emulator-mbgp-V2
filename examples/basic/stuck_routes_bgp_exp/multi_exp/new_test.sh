#!/bin/bash

# === Configuration Variables ===
ROUTER149="as149r-router0-10.149.0.254"
ROUTER150="as150r-router0-10.150.0.254"
ROUTER151="as151r-router0-10.151.0.254"
ROUTER152="as152r-router0-10.152.0.254"
TOTAL_EXPERIMENTS=1
SHUTDOWN_OFFSET=3  # Seconds after route configuration to trigger 149 withdrawal
EXPERIMENT_DURATION=50  # Seconds to wait after 149 withdrawal before ending experiment

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

# Function to check if containers are running
check_containers() {
    for router in "$ROUTER149" "$ROUTER150" "$ROUTER151" "$ROUTER152"; do
        if ! get_container_id "$router" > /dev/null; then
            echo -e "${RED}❌ Required container '$router' is not running.${NC}"
            echo "Please make sure all router containers are running before starting the experiment."
            exit 1
        fi
    done
    echo -e "${GREEN}✅ All required router containers are running.${NC}"
}

# Function to check for the static route files
check_route_files() {
    if [ ! -f "route_149_static_routes.conf" ]; then
        echo -e "${RED}❌ File 'route_149_static_routes.conf' not found in current directory.${NC}"
        exit 1
    fi
    
    if [ ! -f "route_150_static_routes.conf" ]; then
        echo -e "${RED}❌ File 'route_150_static_routes.conf' not found in current directory.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Static route files found in current directory.${NC}"
}

# Function to kill all BIRD processes in router containers
kill_all_bird() {
    echo -e "${RED}🛑 Killing existing BIRD processes...${NC}"
    
    router_containers=$(docker ps --format '{{.ID}} {{.Names}}' | grep router | awk '{print $1}')
    
    if [[ -z "$router_containers" ]]; then
        echo "No containers with 'router' in the name found."
        return 1
    fi
    
    for container_id in $router_containers; do
        echo "  Killing BIRD processes in container $container_id..."
        
        # Get PIDs of bird processes
        pids=$(docker exec $container_id sh -c "ps aux | grep bird | grep -v grep | awk '{print \$2}'")
        
        if [[ -z "$pids" ]]; then
            echo "   No BIRD processes found in $container_id."
            continue
        fi
        
        for pid in $pids; do
            echo "   Killing PID $pid"
            docker exec $container_id kill -9 $pid
        done
        echo "--> Done with $container_id"
    done
    
    echo -e "${GREEN}✅ All BIRD processes have been killed.${NC}"
}

# Function to start BIRD on specific routers
start_bird_on_routers() {
    local routers=("$@")
    
    for router in "${routers[@]}"; do
        local container_id=$(get_container_id "$router")
        if [[ -z "$container_id" ]]; then
            echo -e "${RED}❌ Could not find container for router $router.${NC}"
            continue
        fi
        
        echo -e "${GREEN}🚀 Starting BIRD on $router (container ID: $container_id)...${NC}"
        docker exec "$container_id" mkdir -p /bird/mbgp_log
        docker exec -d "$container_id" sh -c "bird -d > /bird/mbgp_log/bird.log 2>&1 &"
    done
}

# Function to configure BIRD on a specific router
configure_bird_on_router() {
    local router=$1
    local container_id=$(get_container_id "$router")
    
    if [[ -z "$container_id" ]]; then
        echo -e "${RED}❌ Could not find container for router $router.${NC}"
        return 1
    fi
    
    echo -e "${BLUE}🔧 Configuring BIRD on $router...${NC}"
    docker exec "$container_id" birdc configure
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ BIRD configured successfully on $router${NC}"
    else
        echo -e "${RED}❌ BIRD configuration failed on $router${NC}"
    fi
}

# Function to withdraw routes from Router 149
withdraw_routes_from_router149() {
    local r149_id=$(get_container_id $ROUTER149)
    
    if [[ -z "$r149_id" ]]; then
        echo -e "${RED}❌ Could not find Router 149 container.${NC}"
        return 1
    fi
    
    echo -e "${RED}🛑 Withdrawing routes from Router 149 at $(date +"%H:%M:%S.%3N")...${NC}"
    
    # Check if static_routes protocol exists
    local has_static=$(docker exec $r149_id birdc show protocols | grep static_routes)
    
    if [[ -n "$has_static" ]]; then
        # Disable static_routes protocol to withdraw all routes
        docker exec $r149_id birdc disable static_routes
        echo -e "${GREEN}✅ Routes withdrawn from Router 149 at $(date +"%H:%M:%S.%3N")${NC}"
    else
        echo -e "${YELLOW}⚠️ No static_routes protocol found on Router 149${NC}"
    fi
}

# Function to check for stuck routes with 149
check_stuck_routes() {
    local exp_num=$1
    local output_file="${exp_num}_149_stuck_routes.log"
    
    echo -e "${BLUE}🔍 Checking for routes with AS 149 in BGP path...${NC}"
    echo "Experiment $exp_num - Routes with AS 149 in BGP path" > "$output_file"
    echo "------------------------------------------------" >> "$output_file"
    
    # Check Router 151
    local r151_id=$(get_container_id $ROUTER151)
    if [[ -n "$r151_id" ]]; then
        echo -e "\nRouter 151 routes with AS 149 in BGP path:" >> "$output_file"
        echo -e "Command: birdc 'show route where bgp_path ~ [149]'" >> "$output_file"
        echo -e "-------------------------------------------" >> "$output_file"
        docker exec $r151_id /bin/bash -c "birdc 'show route where bgp_path ~ [149]'" >> "$output_file" 2>&1
        
        # Count and display zombie routes
        local zombie_count=$(docker exec $r151_id birdc show route where bgp_path ~ [149] count | grep -o '[0-9]\+ of [0-9]\+' | head -1)
        echo -e "${BLUE}Router 151 zombie count: $zombie_count${NC}"
    fi
    
    # Check Router 152
    local r152_id=$(get_container_id $ROUTER152)
    if [[ -n "$r152_id" ]]; then
        echo -e "\nRouter 152 routes with AS 149 in BGP path:" >> "$output_file"
        echo -e "Command: birdc 'show route where bgp_path ~ [149]'" >> "$output_file"
        echo -e "-------------------------------------------" >> "$output_file"
        docker exec $r152_id /bin/bash -c "birdc 'show route where bgp_path ~ [149]'" >> "$output_file" 2>&1
        
        # Count and display zombie routes
        local zombie_count=$(docker exec $r152_id birdc show route where bgp_path ~ [149] count | grep -o '[0-9]\+ of [0-9]\+' | head -1)
        echo -e "${BLUE}Router 152 zombie count: $zombie_count${NC}"
    fi
    
    # Also save a consolidated file for all experiments
    if [ "$exp_num" == "1" ]; then
        cp "$output_file" "149_stuck_routes.log"
    else
        echo -e "\n\n========== Experiment $exp_num ==========" >> "149_stuck_routes.log"
        cat "$output_file" >> "149_stuck_routes.log"
    fi
    
    echo -e "${GREEN}✅ BGP path check completed. Results saved to $output_file and appended to 149_stuck_routes.log${NC}"
}

# Function to backup Router 150's original configuration
backup_router150_config() {
    local r150_id=$(get_container_id $ROUTER150)
    
    if [[ -z "$r150_id" ]]; then
        echo -e "${RED}❌ Could not find Router 150 container. Cannot backup config.${NC}"
        return 1
    fi
    
    if [ -f "150_router.conf" ]; then
        echo -e "${BLUE}📦 Using existing 150_router.conf as backup...${NC}"
    else
        echo -e "${BLUE}📦 Backing up Router 150 original configuration...${NC}"
        docker exec $r150_id cat /etc/bird/bird.conf > 150_router.conf
        echo -e "${GREEN}✅ Router 150 configuration backed up to 150_router.conf${NC}"
    fi
}

# Function to restore Router 150's original configuration
restore_router150_config() {
    local r150_id=$(get_container_id $ROUTER150)
    
    if [[ -z "$r150_id" ]]; then
        echo -e "${RED}❌ Could not find Router 150 container. Cannot restore config.${NC}"
        return 1
    fi
    
    if [ ! -f "150_router.conf" ]; then
        echo -e "${RED}❌ Backup file 150_router.conf not found. Cannot restore.${NC}"
        return 1
    fi
    
    echo -e "${BLUE}🔄 Restoring Router 150 original configuration...${NC}"
    docker cp 150_router.conf $r150_id:/etc/bird/bird.conf
    echo -e "${GREEN}✅ Router 150 configuration restored from 150_router.conf${NC}"
}

# Function to append static routes to Router 149
append_routes_to_router149() {
    local r149_id=$(get_container_id $ROUTER149)
    
    if [[ -z "$r149_id" ]]; then
        echo -e "${RED}❌ Could not find Router 149 container. Cannot append routes.${NC}"
        return 1
    fi
    
    # Check if static_routes protocol already exists
    local has_static=$(docker exec $r149_id grep "protocol static static_routes" /etc/bird/bird.conf)
    
    if [[ -n "$has_static" ]]; then
        echo -e "${YELLOW}⚠️ Static routes protocol already exists in Router 149 configuration. Skipping append.${NC}"
        return 0
    fi
    
    echo -e "${BLUE}🛠️ Appending static routes to Router 149 configuration...${NC}"
    docker cp route_149_static_routes.conf $r149_id:/tmp/
    docker exec $r149_id sh -c "cat /tmp/route_149_static_routes.conf >> /etc/bird/bird.conf"
    
    echo -e "${GREEN}✅ Routes appended to Router 149 configuration${NC}"
}

# Function to append static routes to Router 150
append_routes_to_router150() {
    local r150_id=$(get_container_id $ROUTER150)
    
    if [[ -z "$r150_id" ]]; then
        echo -e "${RED}❌ Could not find Router 150 container. Cannot append routes.${NC}"
        return 1
    fi
    
    # Check if static_routes protocol already exists
    local has_static=$(docker exec $r150_id grep "protocol static static_routes" /etc/bird/bird.conf)
    
    if [[ -n "$has_static" ]]; then
        echo -e "${YELLOW}⚠️ Static routes protocol already exists in Router 150 configuration. Skipping append.${NC}"
        return 0
    fi
    
    echo -e "${BLUE}🛠️ Appending static routes to Router 150 configuration...${NC}"
    docker cp route_150_static_routes.conf $r150_id:/tmp/
    docker exec $r150_id sh -c "cat /tmp/route_150_static_routes.conf >> /etc/bird/bird.conf"
    
    echo -e "${GREEN}✅ Routes appended to Router 150 configuration${NC}"
}

# Function to check route propagation
check_route_propagation() {
    echo -e "${BLUE}📊 Checking route propagation...${NC}"
    
    # Check Router 150
    echo -e "${BLUE}Router 150 route counts:${NC}"
    docker exec $ROUTER150 birdc show route count
    
    # Sample of routes from 149
    echo -e "${BLUE}Router 150 sample routes from 149:${NC}"
    docker exec $ROUTER150 birdc show route where proto ~ "x_as149" | head -n 5
    
    # Check Router 151
    echo -e "${BLUE}Router 151 route counts:${NC}"
    docker exec $ROUTER151 birdc show route count
    
    # Sample of routes with AS 149 in path
    echo -e "${BLUE}Router 151 sample routes with AS 149 in path:${NC}"
    docker exec $ROUTER151 birdc show route where bgp_path ~ [149] | head -n 5
    
    # Check Router 152
    echo -e "${BLUE}Router 152 route counts:${NC}"
    docker exec $ROUTER152 birdc show route count
    
    # Sample of routes with AS 149 in path
    echo -e "${BLUE}Router 152 sample routes with AS 149 in path:${NC}"
    docker exec $ROUTER152 birdc show route where bgp_path ~ [149] | head -n 5
}

# Function to check for zombie routes
check_for_zombies() {
    echo -e "${BLUE}🔍 Checking for zombie routes...${NC}"
    
    # Check Router 151
    echo -e "${BLUE}Router 151 zombie routes:${NC}"
    docker exec $ROUTER151 birdc show route where bgp_path ~ [149] count
    
    # Sample of zombie routes if any exist
    local zombie_count_151=$(docker exec $ROUTER151 birdc show route where bgp_path ~ [149] count | grep -o '[0-9]\+ of [0-9]\+' | head -1)
    if [[ -n "$zombie_count_151" && "$zombie_count_151" != "0 of 0" ]]; then
        echo -e "${RED}Zombie routes found in Router 151! Count: $zombie_count_151${NC}"
        echo -e "${BLUE}Sample zombie routes in Router 151:${NC}"
        docker exec $ROUTER151 birdc show route where bgp_path ~ [149] | head -n 5
    else
        echo -e "${GREEN}No zombie routes found in Router 151${NC}"
    fi
    
    # Check Router 152
    echo -e "${BLUE}Router 152 zombie routes:${NC}"
    docker exec $ROUTER152 birdc show route where bgp_path ~ [149] count
    
    # Sample of zombie routes if any exist
    local zombie_count_152=$(docker exec $ROUTER152 birdc show route where bgp_path ~ [149] count | grep -o '[0-9]\+ of [0-9]\+' | head -1)
    if [[ -n "$zombie_count_152" && "$zombie_count_152" != "0 of 0" ]]; then
        echo -e "${RED}Zombie routes found in Router 152! Count: $zombie_count_152${NC}"
        echo -e "${BLUE}Sample zombie routes in Router 152:${NC}"
        docker exec $ROUTER152 birdc show route where bgp_path ~ [149] | head -n 5
    else
        echo -e "${GREEN}No zombie routes found in Router 152${NC}"
    fi
}

# Function to run the experiment
run_experiment() {
    echo -e "\n${BLUE}=================================================${NC}"
    echo -e "${BLUE}🧪 Starting BGP Zombie Experiment${NC}"
    echo -e "${BLUE}=================================================${NC}"
    
    # 1. Kill all BIRD processes to start fresh
    kill_all_bird
    
    # 2. Backup Router 150's original configuration
    backup_router150_config
    
    # 3. Start tcpdump for BGP traffic
    local dump_file="zombie_experiment.pcap"
    echo -e "${BLUE}📡 Starting tcpdump for BGP traffic...${NC}"
    tcpdump -i any host 10.100.0.149 or host 10.100.0.150 or host 10.100.0.151 or host 10.100.0.152 or host 10.150.0.150 -w "$dump_file" > "tcpdump_stdout.log" 2> "tcpdump_stderr.log" &
    TCPDUMP_PID=$!
    
    # Let tcpdump initialize
    sleep 2

    # 4. Apply throttling to Router 150
    echo "🐢 Throttling Router 150 ix100 interface to simulate congestion..."
    docker exec $ROUTER150 tc qdisc del dev ix100 root 2>/dev/null
    docker exec $ROUTER150 tc qdisc add dev ix100 root tbf rate 5kbit burst 32kbit latency 400ms
    
    # 5. Append static routes to Router 149
    append_routes_to_router149

    # 6. Append static routes to Router 150
    append_routes_to_router150
    
    # 7. Start BIRD on all routers
    echo -e "${GREEN}🚀 Starting BIRD on all routers...${NC}"
    start_bird_on_routers "$ROUTER149" "$ROUTER150" "$ROUTER151" "$ROUTER152"
    
    # 8. Wait for routers to establish sessions
    echo -e "${YELLOW}⏱️ Waiting 60 seconds for all BGP sessions to establish...${NC}"
    sleep 60
    
    # 9. Check that routes are propagating properly
    check_route_propagation
    
    # 10. Wait for shutdown offset
    echo -e "${YELLOW}⏱️ Waiting ${SHUTDOWN_OFFSET} seconds before withdrawing routes from Router 149...${NC}"
    sleep $SHUTDOWN_OFFSET
    
    # 11. Withdraw routes from Router 149
    withdraw_routes_from_router149
    
    # 12. Let the experiment run for the specified duration after route withdrawal
    echo -e "${BLUE}🔬 Running experiment for ${EXPERIMENT_DURATION} seconds after route withdrawal...${NC}"
    
    # Show progress bar
    for i in $(seq 1 $EXPERIMENT_DURATION); do
        echo -ne "${YELLOW}Progress: ${i}/${EXPERIMENT_DURATION} seconds${NC}\r"
        
        # Check for zombies every 10 seconds
        if [ $((i % 10)) -eq 0 ]; then
            check_for_zombies
        fi
        
        sleep 1
    done
    echo -e "\n"
    
    # 13. Final check for stuck routes after experiment duration
    echo -e "${BLUE}🔍 Final check for stuck routes after experiment duration...${NC}"
    check_stuck_routes 1
    
    # 14. Stop tcpdump
    echo -e "${RED}🛑 Stopping tcpdump...${NC}"
    kill $TCPDUMP_PID
    wait $TCPDUMP_PID 2>/dev/null
    
    # 15. Kill all BIRD processes to clean up
    echo -e "${RED}🛑 Cleaning up - killing all BIRD processes...${NC}"
    kill_all_bird
    
    echo -e "${GREEN}✅ BGP Zombie experiment completed!${NC}"
    echo -e "Packet capture saved to ${BLUE}$dump_file${NC}"
    echo -e "Route checks saved to ${BLUE}1_149_stuck_routes.log${NC}"
}

# Main function
main() {
    check_containers
    check_route_files
    run_experiment
}

# Run the main function
main
