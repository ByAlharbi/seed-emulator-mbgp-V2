#!/bin/bash

echo "📡 Starting tcpdump..."
TIMESTAMP=$(date +%s)
PCAP_FILE="mbgp_capture_${TIMESTAMP}.pcap"
ROUTES_FILE="routes_count_${TIMESTAMP}.txt"

tcpdump -i any -w "$PCAP_FILE" \
    '((tcp port 179 or tcp port 50051) or (udp port 3784 or udp port 4784)) and (net 10.0.0.0/8)' \
    > /dev/null 2>&1 &

TCPDUMP_PID=$!
echo "✅ tcpdump started (PID: $TCPDUMP_PID)"
echo "📁 Capturing to: $PCAP_FILE"

# Let tcpdump run for 20 seconds
echo "⏳ Waiting 20 seconds for route activity..."
sleep 30

# Stop tcpdump
echo "🛑 Stopping tcpdump..."
kill $TCPDUMP_PID 2>/dev/null
wait $TCPDUMP_PID 2>/dev/null

# Final route count (once)
echo "📊 Final route count (all routers):"
echo "mBGP Route Count Monitoring - $(date)" > "$ROUTES_FILE"
echo "======================================" >> "$ROUTES_FILE"

ALL_ROUTERS=(2 3 4 11 12 150 151 152 153 154 160 161 162 163 164 170 171)
for AS in "${ALL_ROUTERS[@]}"; do
    ROUTER="as${AS}r-router0-10.${AS}.0.254"
    if docker ps --format '{{.Names}}' | grep -q "$ROUTER"; then
        COUNT=$(docker exec "$ROUTER" birdc show route count 2>/dev/null | grep -o '[0-9]\+ of [0-9]\+' | awk '{print $3}' || echo "0")
        printf "AS%-3s: %s routes\n" "$AS" "$COUNT" | tee -a "$ROUTES_FILE"
    fi
done

# Quick packet analysis
echo ""
echo "📈 Capture Analysis:" | tee -a "$ROUTES_FILE"
echo "===================" >> "$ROUTES_FILE"
echo "   File: $PCAP_FILE"
echo "   Size: $(ls -lh $PCAP_FILE | awk '{print $5}')" | tee -a "$ROUTES_FILE"

BGP_UPDATES=$(tcpdump -r "$PCAP_FILE" 2>/dev/null | grep -c "BGP.*UPDATE" || echo "0")
GRPC_PACKETS=$(tcpdump -r "$PCAP_FILE" 2>/dev/null | grep -c "50051" || echo "0")
TOTAL_PACKETS=$(tcpdump -r "$PCAP_FILE" 2>/dev/null | wc -l)

echo "   BGP Updates: $BGP_UPDATES" | tee -a "$ROUTES_FILE"
echo "   gRPC packets: $GRPC_PACKETS" | tee -a "$ROUTES_FILE"
echo "   Total packets: $TOTAL_PACKETS" | tee -a "$ROUTES_FILE"

echo ""
echo "✅ Done! Results saved to:"
echo "   - Packet capture: $PCAP_FILE"
echo "   - Route counts: $ROUTES_FILE"
