#!/bin/bash

# === Start tcpdump for all Docker traffic including BFD ===
echo "📡 Starting tcpdump..."
TIMESTAMP=$(date +%s)
PCAP_FILE="mbgp_capture_${TIMESTAMP}.pcap"
ROUTES_FILE="routes_count_${TIMESTAMP}.txt"

# Capture BGP, gRPC, and BFD traffic on all Docker networks
tcpdump -i any -w "$PCAP_FILE" \
    '((tcp port 179 or tcp port 50051) or (udp port 3784 or udp port 4784)) and (net 10.0.0.0/8)' \
    > /dev/null 2>&1 &

TCPDUMP_PID=$!
echo "✅ tcpdump started (PID: $TCPDUMP_PID)"
echo "📁 Capturing to: $PCAP_FILE"
echo "📝 Route counts to: $ROUTES_FILE"

# === Initialize routes file ===
echo "mBGP Route Count Monitoring - $(date)" > "$ROUTES_FILE"
echo "========================================" >> "$ROUTES_FILE"
echo "" >> "$ROUTES_FILE"

# === Run your test here ===
echo ""
echo "⏳ Monitoring for 60 seconds..."
echo "   (Run your route injection in another terminal)"
echo ""

# === Check route counts on random stub ASes periodically ===
STUB_ASES=(150 151 152 153 154 160 161 162 163 164 170 171)
CHECK_INTERVAL=10  # Check every 10 seconds

for i in {1..6}; do  # Check 6 times (60 seconds total)
    CHECK_TIME=$(date '+%Y-%m-%d %H:%M:%S')
    echo "📊 Route check #$i ($CHECK_TIME):"
    echo "Check #$i - $CHECK_TIME" >> "$ROUTES_FILE"
    echo "------------------------" >> "$ROUTES_FILE"
    
    # Pick 3 random stub ASes
    RANDOM_ASES=($(printf '%s\n' "${STUB_ASES[@]}" | shuf -n 3))
    
    for AS in "${RANDOM_ASES[@]}"; do
        ROUTER="as${AS}r-router0-10.${AS}.0.254"
        if docker ps --format '{{.Names}}' | grep -q "$ROUTER"; then
            COUNT=$(docker exec $ROUTER birdc show route count 2>/dev/null | grep -o '[0-9]\+ of [0-9]\+' | awk '{print $3}' || echo "0")
            echo "   AS${AS}: $COUNT routes"
            echo "AS${AS}: $COUNT routes" >> "$ROUTES_FILE"
        fi
    done
    echo ""
    echo "" >> "$ROUTES_FILE"
    
    sleep $CHECK_INTERVAL
done

# === Final route count for ALL routers ===
echo "📊 Final route count (all routers):" | tee -a "$ROUTES_FILE"
echo "===================================" >> "$ROUTES_FILE"
for AS in 2 3 4 11 12 ${STUB_ASES[@]}; do
    ROUTER="as${AS}r-router0-10.${AS}.0.254"
    if docker ps --format '{{.Names}}' | grep -q "$ROUTER"; then
        COUNT=$(docker exec $ROUTER birdc show route count 2>/dev/null | grep -o '[0-9]\+ of [0-9]\+' | awk '{print $3}' || echo "0")
        printf "AS%-3s: %s routes\n" "$AS" "$COUNT" | tee -a "$ROUTES_FILE"
    fi
done

# === Stop tcpdump ===
echo ""
echo "🛑 Stopping tcpdump..."
kill $TCPDUMP_PID 2>/dev/null
wait $TCPDUMP_PID 2>/dev/null

# === Quick analysis ===
echo ""
echo "📈 Capture Analysis:" | tee -a "$ROUTES_FILE"
echo "===================" >> "$ROUTES_FILE"
echo "   File: $PCAP_FILE"
echo "   Size: $(ls -lh $PCAP_FILE | awk '{print $5}')"

# Only count BGP and gRPC packets
BGP_UPDATES=$(tcpdump -r $PCAP_FILE 2>/dev/null | grep -c "BGP.*UPDATE" || echo "0")
GRPC_PACKETS=$(tcpdump -r $PCAP_FILE 2>/dev/null | grep -c "50051" || echo "0")
TOTAL_PACKETS=$(tcpdump -r $PCAP_FILE 2>/dev/null | wc -l)

echo "   BGP Updates: $BGP_UPDATES" | tee -a "$ROUTES_FILE"
echo "   gRPC packets: $GRPC_PACKETS" | tee -a "$ROUTES_FILE"
echo "   Total packets: $TOTAL_PACKETS" | tee -a "$ROUTES_FILE"

echo ""
echo "✅ Done! Results saved to:"
echo "   - Packet capture: $PCAP_FILE"
echo "   - Route counts: $ROUTES_FILE"
