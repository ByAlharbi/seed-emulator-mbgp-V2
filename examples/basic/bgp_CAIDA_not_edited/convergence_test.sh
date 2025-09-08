#!/bin/bash
set -euo pipefail

# BGP Convergence Test Script
# Container IDs
AS158_ROUTER="eb2c57b36da0"
AS140_HOST="f0b838ecdfa5" 
AS133_ROUTER="aedcc5111bc2"

# Test parameters
IPERF_PORT=5001
TEST_DURATION=300
FAILURE_DURATION=60

echo "Starting BGP Convergence Test..."

# Start iperf3 server
echo "Starting iperf3 server on AS158..."
docker exec -d "$AS158_ROUTER" iperf3 -s -p "$IPERF_PORT"
sleep 2

# Start iperf3 client with logging
echo "Starting iperf3 client on AS140..."
LOGFILE="convergence_test_$(date +%Y%m%d_%H%M%S).log"
docker exec -d "$AS140_HOST" bash -c "iperf3 -c 10.158.0.254 -t $TEST_DURATION -p $IPERF_PORT | tee /tmp/iperf_client.log"

# Wait for traffic to stabilize
echo "Waiting 30 seconds for traffic to stabilize..."
sleep 30

# Trigger failure by killing BIRD
echo "$(date): Killing BIRD process on AS133..."
docker exec "$AS133_ROUTER" bash -c "kill -9 \$(pidof bird) || true"

# Wait during failure
echo "Waiting $FAILURE_DURATION seconds during failure..."
sleep "$FAILURE_DURATION"

# Restart BIRD
echo "$(date): Restarting BIRD on AS133..."
docker exec "$AS133_ROUTER" bird

# Wait for recovery
echo "Waiting 60 seconds for recovery..."
sleep 60

# Stop processes
echo "Stopping iperf3 processes..."
docker exec "$AS158_ROUTER" pkill iperf3 || true
docker exec "$AS140_HOST" pkill iperf3 || true

# Collect results
echo "Collecting results..."
docker exec "$AS140_HOST" cat /tmp/iperf_client.log > "$LOGFILE"

echo "Test completed. Results saved to: $LOGFILE"
echo "Look for throughput gaps to measure convergence time."
