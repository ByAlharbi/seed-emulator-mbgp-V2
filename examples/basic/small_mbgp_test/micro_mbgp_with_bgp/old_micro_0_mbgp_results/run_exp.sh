#!/bin/bash

# Determine experiment number
EXP_NUM=1
while [ -f "bgp_dump_exp${EXP_NUM}.pcap" ]; do
    ((EXP_NUM++))
done

echo "Running Experiment ${EXP_NUM}"

# 1. Kill all routers and start all except AS150
echo "Stopping all routers..."
docker stop $(docker ps -q --filter "name=router") $(docker ps -q --filter "name=rs")

echo "Starting all routers except AS150..."
docker start $(docker ps -aq --filter "name=router" | grep -v "as150r-router0") $(docker ps -aq --filter "name=rs")

# 2. Wait 5 seconds
echo "Waiting 5 seconds..."
sleep 5

# 3. Start tcpdump
echo "Starting tcpdump..."
tcpdump -i any -w "bgp_dump_exp${EXP_NUM}.pcap" 'tcp port 179 or tcp port 50051' > /dev/null 2>&1 &
TCPDUMP_PID=$!

# 4. Wait 2 seconds
sleep 2

# 5. Start AS150 router
echo "Starting AS150 router..."
docker start as150r-router0-10.150.0.254

# 6. Wait 20 seconds then stop tcpdump
echo "Waiting 20 seconds..."
sleep 20
kill $TCPDUMP_PID

# 7. Check routes on all stub AS routers
echo "Checking routes on stub AS routers..."
echo -e "\nExp ${EXP_NUM}:" >> routes.txt

for AS in 150 151 152 160 161 162; do
    echo "AS${AS}: $(docker exec as${AS}r-router0-10.${AS}.0.254 birdc show route count)" >> routes.txt
done

echo "Done. Results appended to routes.txt"
echo "Capture saved to bgp_dump_exp${EXP_NUM}.pcap"
