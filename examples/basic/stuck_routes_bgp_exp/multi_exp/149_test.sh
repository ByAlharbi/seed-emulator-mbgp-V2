#!/bin/bash

# Router container names
ROUTER149="as149r-router0-10.149.0.254"
ROUTER150="as150r-router0-10.150.0.254"
ROUTER151="as151r-router0-10.151.0.254"
ROUTER152="as152r-router0-10.152.0.254"

# Colors for better readability
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check routes from AS149
check_routes_from_149() {
    echo -e "${BLUE}======= CHECKING ROUTES FROM AS149 =======${NC}"
    echo "Time: $(date +"%H:%M:%S")"
    
    # Check Router 150
    echo -e "${BLUE}Router 150 routes from 149:${NC}"
    docker exec $ROUTER150 birdc 'show route where proto ~ "x_as149"' | grep -e "^[0-9]" | wc -l
    
    # Check Router 151
    echo -e "${BLUE}Router 151 routes with AS 149 in path:${NC}"
    docker exec $ROUTER151 birdc 'show route where bgp_path ~ [149]' | grep -e "^[0-9]" | wc -l
    
    # Check Router 152
    echo -e "${BLUE}Router 152 routes with AS 149 in path:${NC}"
    docker exec $ROUTER152 birdc 'show route where bgp_path ~ [149]' | grep -e "^[0-9]" | wc -l
}

# Function to withdraw routes from AS149
withdraw_routes_from_149() {
    echo -e "${RED}======= WITHDRAWING ROUTES FROM AS149 =======${NC}"
    echo "Time: $(date +"%H:%M:%S")"
    
    # Disable static_routes protocol to withdraw all routes
    docker exec $ROUTER149 birdc disable static_routes
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Routes withdrawal initiated from Router 149${NC}"
    else
        echo -e "${RED}❌ Failed to withdraw routes from Router 149${NC}"
    fi
}

# Main execution flow

# Initial check
echo -e "${YELLOW}Initial route check before withdrawal${NC}"
check_routes_from_149

# Withdraw routes
echo -e "${YELLOW}Withdrawing routes${NC}"
withdraw_routes_from_149

# Monitor route withdrawal every 5 seconds
echo -e "${YELLOW}Monitoring route withdrawal${NC}"
for i in {1..12}; do
    sleep 5
    echo -e "${YELLOW}Check #$i (after $((i*5)) seconds)${NC}"
    check_routes_from_149
done

echo -e "${GREEN}======= WITHDRAWAL VERIFICATION COMPLETE =======${NC}"
