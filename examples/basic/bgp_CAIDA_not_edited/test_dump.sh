#!/bin/bash
set -euo pipefail

# ---------- experiment id ----------
EXP_NUM=1
while [ -f "exp${EXP_NUM}.pcap" ]; do ((EXP_NUM++)); done
echo "Running Experiment ${EXP_NUM}"

# ---------- tcpdump ----------
echo "Starting tcpdump on IP 10.103.0.158 port 50051..."
tcpdump -i any -w "exp${EXP_NUM}.pcap" 'host 10.103.0.158 and port 179' > /dev/null 2>&1 &
TCPDUMP_PID=$!

# ---------- run window ----------
echo "Running tcpdump for 2 minutes..."
sleep 120

# ---------- stop ----------
echo "Stopping tcpdump..."
kill "$TCPDUMP_PID" 2>/dev/null || true

echo "Done. Capture saved to exp${EXP_NUM}.pcap"
