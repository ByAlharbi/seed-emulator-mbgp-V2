#!/bin/bash

# === Configuration Variables ===
ROUTER149="as149r-router0-10.149.0.254"
ROUTER150="as150r-router0-10.150.0.254"
ROUTER151="as151r-router0-10.151.0.254"
ROUTER152="as152r-router0-10.152.0.254"
TOTAL_EXPERIMENTS=15
SHUTDOWN_OFFSET=1  # Seconds after route configuration to trigger 149 shutdown
EXPERIMENT_DURATION=50  # Seconds to wait after 149 shutoff before ending experiment

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

# Function to kill Router 149's BIRD process
kill_router149() {
    local r149_id=$(get_container_id $ROUTER149)
    
    if [[ -z "$r149_id" ]]; then
        echo -e "${RED}❌ Could not find Router 149 container. Cannot shut down.${NC}"
        return 1
    fi
    
    echo -e "${RED}🛑 Shutting down Router 149 BIRD process at $(date +"%H:%M:%S.%3N")...${NC}"
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
    fi
    
    # Check Router 152
    local r152_id=$(get_container_id $ROUTER152)
    if [[ -n "$r152_id" ]]; then
        echo -e "\nRouter 152 routes with AS 149 in BGP path:" >> "$output_file"
        echo -e "Command: birdc 'show route where bgp_path ~ [149]'" >> "$output_file"
        echo -e "-------------------------------------------" >> "$output_file"
        docker exec $r152_id /bin/bash -c "birdc 'show route where bgp_path ~ [149]'" >> "$output_file" 2>&1
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
    
    echo -e "${BLUE}🛠️ Appending static routes to Router 150 configuration...${NC}"
    docker cp route_150_static_routes.conf $r150_id:/tmp/
    docker exec $r150_id sh -c "cat /tmp/route_150_static_routes.conf >> /etc/bird/bird.conf"
    
    echo -e "${GREEN}✅ Routes appended to Router 150 configuration${NC}"
}

# Function to run the first experiment
run_first_experiment() {
    echo -e "\n${BLUE}=================================================${NC}"
    echo -e "${BLUE}🧪 Starting First Experiment${NC}"
    echo -e "${BLUE}=================================================${NC}"
    
    # 1. Kill all BIRD processes to start fresh
    kill_all_bird
    
    # 2. Backup Router 150's original configuration
    backup_router150_config
    
    # 3. Start tcpdump for BGP traffic
    local dump_file="1_exp.pcap"
    echo -e "${BLUE}📡 Starting tcpdump for BGP traffic...${NC}"
    tcpdump -i any host 10.100.0.149 or host 10.100.0.150 or host 10.100.0.151 or host 10.100.0.152 or host 10.150.0.150 -w "$dump_file" > "tcpdump_stdout_1.log" 2> "tcpdump_stderr_1.log" &
    TCPDUMP_PID=$!
    
    # Let tcpdump initialize
    sleep 2
    
    # 4. Append static routes to Router 149
    append_routes_to_router149
    
    # 5. Start BIRD on routers 149 and 150
    echo -e "${GREEN}🚀 Starting BIRD on Router 149 and 150...${NC}"
    start_bird_on_routers "$ROUTER149" "$ROUTER150"
    
    # 6. Wait 30 seconds for 149 and 150
    echo -e "${YELLOW}⏱️ Waiting 30 seconds for Router 149 and 150 to connect...${NC}"
    sleep 30
    
    # 7. Start BIRD on routers 151 and 152
    echo -e "${GREEN}🚀 Starting BIRD on Router 151 and 152...${NC}"
    start_bird_on_routers "$ROUTER151" "$ROUTER152"
    
    # 8. Wait 30 seconds for 151 and 152
    echo -e "${YELLOW}⏱️ Waiting 30 seconds for Router 151 and 152 to connect...${NC}"
    sleep 30
    
    # 9. Append static routes to Router 150 and configure BIRD
    append_routes_to_router150
    configure_bird_on_router "$ROUTER150"
    
    # 10. Wait for shutdown offset
    echo -e "${YELLOW}⏱️ Waiting ${SHUTDOWN_OFFSET} seconds before killing Router 149...${NC}"
    sleep $SHUTDOWN_OFFSET
    
    # 11. Kill Router 149 BIRD process
    kill_router149
    
    # 12. Let the experiment run for the specified duration after 149 shutoff
    echo -e "${BLUE}🔬 Running experiment for ${EXPERIMENT_DURATION} seconds after Router 149 shutdown...${NC}"
    
    # Show progress bar
    for i in $(seq 1 $EXPERIMENT_DURATION); do
        echo -ne "${YELLOW}Progress: ${i}/${EXPERIMENT_DURATION} seconds${NC}\r"
        sleep 1
    done
    echo -e "\n"
    
    # 13. Check for stuck routes after experiment duration
    echo -e "${BLUE}🔍 Checking for stuck routes after experiment duration...${NC}"
    check_stuck_routes 1
    
    # 14. Stop tcpdump
    echo -e "${RED}🛑 Stopping tcpdump...${NC}"
    kill $TCPDUMP_PID
    wait $TCPDUMP_PID 2>/dev/null
    
    # 15. Kill all BIRD processes to ensure clean state for next experiment
    echo -e "${RED}🛑 Cleaning up - killing all BIRD processes...${NC}"
    kill_all_bird
    
    # Add an extra pause between experiments
    echo -e "${YELLOW}⏱️ Pausing 5 seconds between experiments...${NC}"
    sleep 5
    
    echo -e "${GREEN}✅ First experiment completed!${NC}"
    echo -e "Packet capture saved to ${BLUE}$dump_file${NC}"
    echo -e "Route checks saved to ${BLUE}1_149_stuck_routes.log${NC}"
}

# Function to run subsequent experiments
run_subsequent_experiment() {
    local exp_num=$1
    
    echo -e "\n${BLUE}=================================================${NC}"
    echo -e "${BLUE}🧪 Starting Experiment $exp_num${NC}"
    echo -e "${BLUE}=================================================${NC}"
    
    # 1. Kill all BIRD processes to start fresh
    kill_all_bird
    
    # 2. Restore Router 150's original configuration
    restore_router150_config
    
    # 3. Start tcpdump for BGP traffic
    local dump_file="${exp_num}_exp.pcap"
    echo -e "${BLUE}📡 Starting tcpdump for BGP traffic...${NC}"
    tcpdump -i any host 10.100.0.149 or host 10.100.0.150 or host 10.100.0.151 or host 10.100.0.152 or host 10.150.0.150 -w "$dump_file" > "tcpdump_stdout_${exp_num}.log" 2> "tcpdump_stderr_${exp_num}.log" &
    TCPDUMP_PID=$!
    
    # Let tcpdump initialize
    sleep 2
    
    # 4. Start BIRD on routers 149 and 150
    echo -e "${GREEN}🚀 Starting BIRD on Router 149 and 150...${NC}"
    start_bird_on_routers "$ROUTER149" "$ROUTER150"
    
    # 5. Wait 30 seconds for 149 and 150
    echo -e "${YELLOW}⏱️ Waiting 30 seconds for Router 149 and 150 to connect...${NC}"
    sleep 30
    
    # 6. Start BIRD on routers 151 and 152
    echo -e "${GREEN}🚀 Starting BIRD on Router 151 and 152...${NC}"
    start_bird_on_routers "$ROUTER151" "$ROUTER152"
    
    # 7. Wait 30 seconds for 151 and 152
    echo -e "${YELLOW}⏱️ Waiting 30 seconds for Router 151 and 152 to connect...${NC}"
    sleep 30
    
    # 8. Append static routes to Router 150 and configure BIRD
    append_routes_to_router150
    configure_bird_on_router "$ROUTER150"
    
    # 9. Wait for shutdown offset
    echo -e "${YELLOW}⏱️ Waiting ${SHUTDOWN_OFFSET} seconds before killing Router 149...${NC}"
    sleep $SHUTDOWN_OFFSET
    
    # 10. Kill Router 149 BIRD process
    kill_router149
    
    # 11. Let the experiment run for the specified duration after 149 shutoff
    echo -e "${BLUE}🔬 Running experiment for ${EXPERIMENT_DURATION} seconds after Router 149 shutdown...${NC}"
    
    # Show progress bar
    for i in $(seq 1 $EXPERIMENT_DURATION); do
        echo -ne "${YELLOW}Progress: ${i}/${EXPERIMENT_DURATION} seconds${NC}\r"
        sleep 1
    done
    echo -e "\n"
    
    # 12. Check for stuck routes after experiment duration
    echo -e "${BLUE}🔍 Checking for stuck routes after experiment duration...${NC}"
    check_stuck_routes $exp_num
    
    # 13. Stop tcpdump
    echo -e "${RED}🛑 Stopping tcpdump...${NC}"
    kill $TCPDUMP_PID
    wait $TCPDUMP_PID 2>/dev/null
    
    # 14. Kill all BIRD processes to ensure clean state for next experiment
    echo -e "${RED}🛑 Cleaning up - killing all BIRD processes...${NC}"
    kill_all_bird
    
    # Add an extra pause between experiments
    echo -e "${YELLOW}⏱️ Pausing 5 seconds between experiments...${NC}"
    sleep 5
    
    echo -e "${GREEN}✅ Experiment $exp_num completed!${NC}"
    echo -e "Packet capture saved to ${BLUE}$dump_file${NC}"
    echo -e "Route checks saved to ${BLUE}${exp_num}_149_stuck_routes.log${NC}"
}

# Main function to run the entire experimental procedure
main() {
    # Check if all required containers are running
    check_containers
    
    # Check if route files exist
    check_route_files
    
    # Run the first experiment (with different procedure)
    run_first_experiment
    
    # Run the remaining experiments (with restore procedure)
    for i in $(seq 2 $TOTAL_EXPERIMENTS); do
        run_subsequent_experiment $i
    done
    
    echo -e "\n${GREEN}🎉 All $TOTAL_EXPERIMENTS experiments completed successfully!${NC}"
    echo -e "PCAP files saved as ${BLUE}[1-$TOTAL_EXPERIMENTS]_exp.pcap${NC}"
    echo -e "Consolidated stuck routes saved as ${BLUE}149_stuck_routes.log${NC}"
}

# Run the main function
main
