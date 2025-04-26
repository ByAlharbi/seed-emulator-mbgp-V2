#!/usr/bin/env python3
import sys
from scapy.all import rdpcap, IP, TCP
from datetime import datetime
import struct
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict
import re

# BGP message types
BGP_OPEN = 1
BGP_UPDATE = 2
BGP_NOTIFICATION = 3
BGP_KEEPALIVE = 4

# BGP constants
BGP_MARKER = b'\xff' * 16
BGP_PORT = 179

def parse_bgp_header(data):
    """Parse BGP header from raw data."""
    if len(data) < 19:
        return None, None
    
    # Check for BGP marker
    if data[:16] != BGP_MARKER:
        return None, None
    
    # Get message length and type from header
    try:
        length = struct.unpack('!H', data[16:18])[0]
        msg_type = data[18]
        
        # Validate length
        if length < 19 or length > 4096:  # BGP messages shouldn't be larger than 4KB in most cases
            return None, None
            
        return length, msg_type
    except:
        return None, None

def parse_bgp_update(data):
    """Parse BGP UPDATE message and extract prefix information."""
    if len(data) < 23:  # Minimum BGP UPDATE size
        return None, None
    
    # Skip BGP header (19 bytes)
    update_data = data[19:]
    
    # Get withdrawn routes length
    withdrawn_length = struct.unpack('!H', update_data[0:2])[0]
    
    # Skip withdrawn routes
    offset = 2 + withdrawn_length
    
    # Check if we have enough data
    if len(update_data) < offset + 2:
        return None, None
    
    # Get path attributes length
    path_attr_length = struct.unpack('!H', update_data[offset:offset+2])[0]
    
    # Skip path attributes
    offset += 2 + path_attr_length
    
    # The rest is NLRI (Network Layer Reachability Information)
    nlri_data = update_data[offset:]
    
    prefixes = []
    nlri_offset = 0
    
    # Parse each prefix in NLRI
    while nlri_offset < len(nlri_data):
        if nlri_offset + 1 > len(nlri_data):
            break
            
        prefix_len = nlri_data[nlri_offset]
        nlri_offset += 1
        
        # Calculate bytes needed for this prefix
        bytes_needed = (prefix_len + 7) // 8
        
        if nlri_offset + bytes_needed > len(nlri_data):
            break
            
        # Extract prefix bytes
        prefix_bytes = nlri_data[nlri_offset:nlri_offset+bytes_needed]
        nlri_offset += bytes_needed
        
        # Convert to IP address format
        prefix_str = '.'.join(str(b) for b in prefix_bytes)
        while prefix_str.count('.') < 3:
            prefix_str += '.0'
            
        prefixes.append(f"{prefix_str}/{prefix_len}")
    
    # For withdrawals
    withdrawals = []
    if withdrawn_length > 0:
        withdrawal_data = update_data[2:2+withdrawn_length]
        w_offset = 0
        
        while w_offset < withdrawn_length:
            if w_offset + 1 > withdrawn_length:
                break
                
            prefix_len = withdrawal_data[w_offset]
            w_offset += 1
            
            bytes_needed = (prefix_len + 7) // 8
            
            if w_offset + bytes_needed > withdrawn_length:
                break
                
            prefix_bytes = withdrawal_data[w_offset:w_offset+bytes_needed]
            w_offset += bytes_needed
            
            prefix_str = '.'.join(str(b) for b in prefix_bytes)
            while prefix_str.count('.') < 3:
                prefix_str += '.0'
                
            withdrawals.append(f"{prefix_str}/{prefix_len}")
    
    return prefixes, withdrawals

def analyze_bgp_message_info(packet):
    """Extract BGP message info from Wireshark-captured packet."""
    try:
        # Check if this is a BGP packet by looking at the info field
        if hasattr(packet, 'load') and len(packet.load) > 0:
            if b'UPDATE Message' in packet.load:
                # Count number of UPDATE messages in the packet using regex
                update_count = packet.load.count(b'UPDATE Message')
                return 'UPDATE', update_count
            elif b'KEEPALIVE Message' in packet.load:
                return 'KEEPALIVE', 1
            elif b'OPEN Message' in packet.load:
                return 'OPEN', 1
            elif b'NOTIFICATION Message' in packet.load:
                return 'NOTIFICATION', 1
        return None, 0
    except:
        return None, 0

def analyze_bgp_convergence(pcap_file, *peer_ips):
    """
    Analyze BGP convergence between multiple peer IPs.
    
    Args:
        pcap_file (str): Path to the pcap file
        peer_ips: Variable number of IP addresses to analyze
    """
    if len(peer_ips) < 2:
        print("Error: You must specify at least two peer IPs to analyze.")
        return
        
    print(f"Analyzing BGP convergence between {peer_ips[0]} and peers {', '.join(peer_ips[1:])}")

    # Read the pcap file
    try:
        packets = rdpcap(pcap_file)
    except Exception as e:
        print(f"Error reading pcap file: {e}")
        return
    
    # Analyze each pair of peers
    for i in range(1, len(peer_ips)):
        print("\n" + "=" * 80)
        print(f"Analyzing peer connection: {peer_ips[0]} <-> {peer_ips[i]}")
        print("=" * 80)
        
        analyze_peer_connection(packets, peer_ips[0], peer_ips[i])

def analyze_peer_connection(packets, src_ip, dst_ip):
    """Analyze BGP convergence between two specific peers."""
    # Data structures to store BGP information
    updates = []
    updates_src_to_dst = []  # Updates from src_ip to dst_ip
    updates_dst_to_src = []  # Updates from dst_ip to src_ip
    prefix_updates = defaultdict(list)
    prefix_withdrawals = defaultdict(list)
    
    # New counter for multiple updates in a single packet
    total_update_messages = 0
    total_prefixes_announced = 0
    total_prefixes_withdrawn = 0
    
    # Process each packet
    for pkt_idx, pkt in enumerate(packets):
        if not (IP in pkt and TCP in pkt):
            continue
            
        ip_pkt = pkt[IP]
        tcp_pkt = pkt[TCP]
        
        # Check if this is BGP traffic between our target routers
        is_bgp_traffic = (
            (ip_pkt.src == src_ip and ip_pkt.dst == dst_ip) or 
            (ip_pkt.src == dst_ip and ip_pkt.dst == src_ip)
        ) and (tcp_pkt.sport == BGP_PORT or tcp_pkt.dport == BGP_PORT)
        
        if not is_bgp_traffic:
            continue

        timestamp = float(pkt.time)
        human_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S.%f')
        
        # Get TCP payload
        if not hasattr(tcp_pkt, 'payload') or len(bytes(tcp_pkt.payload)) == 0:
            continue
            
        payload = bytes(tcp_pkt.payload)
        
        # First try to parse BGP messages directly
        offset = 0
        bgp_update_count = 0
        
        # Process BGP messages in the TCP payload
        while offset < len(payload):
            length, msg_type = parse_bgp_header(payload[offset:])
            
            if length is None or offset + length > len(payload):
                break
                
            msg_data = payload[offset:offset+length]
            
            # Process UPDATE messages
            if msg_type == BGP_UPDATE:
                bgp_update_count += 1
                prefixes, withdrawals = parse_bgp_update(msg_data)
                
                if prefixes:
                    total_prefixes_announced += len(prefixes)
                    
                if withdrawals:
                    total_prefixes_withdrawn += len(withdrawals)
                
                if prefixes or withdrawals:
                    # Store update information
                    update_info = {
                        'timestamp': timestamp,
                        'human_time': human_time,
                        'src': ip_pkt.src,
                        'dst': ip_pkt.dst,
                        'prefixes': prefixes if prefixes else [],
                        'withdrawals': withdrawals if withdrawals else [],
                        'pkt_idx': pkt_idx
                    }
                    updates.append(update_info)
                    
                    # Separate updates by direction
                    if ip_pkt.src == src_ip and ip_pkt.dst == dst_ip:
                        updates_src_to_dst.append(update_info)
                    elif ip_pkt.src == dst_ip and ip_pkt.dst == src_ip:
                        updates_dst_to_src.append(update_info)
                    
                    # Track prefix updates and withdrawals
                    if prefixes:
                        for prefix in prefixes:
                            prefix_updates[prefix].append((timestamp, ip_pkt.src, ip_pkt.dst))
                    
                    if withdrawals:
                        for prefix in withdrawals:
                            prefix_withdrawals[prefix].append((timestamp, ip_pkt.src, ip_pkt.dst))
            
            offset += length
        
        # Alternative method: use packet info to extract update count
        if bgp_update_count == 0:
            # Try to extract from packet info (useful for Wireshark captured packets)
            bgp_type, count = analyze_bgp_message_info(tcp_pkt)
            if bgp_type == 'UPDATE':
                total_update_messages += count
    
    # Calculate convergence statistics
    print(f"Found {len(updates)} BGP UPDATE messages")
    print(f"  - {len(updates_src_to_dst)} updates from {src_ip} to {dst_ip}")
    print(f"  - {len(updates_dst_to_src)} updates from {dst_ip} to {src_ip}")
    
    # Report on potentially bundled updates not parsed directly
    if total_update_messages > len(updates):
        print(f"NOTE: Detected {total_update_messages} potential UPDATE messages in packets (vs {len(updates)} parsed directly)")
    
    print(f"Total prefixes announced: {total_prefixes_announced}")
    print(f"Total prefixes withdrawn: {total_prefixes_withdrawn}")
    
    if not updates:
        print("No BGP UPDATE messages found for analysis")
        return
    
    # Analysis for direction: src_ip to dst_ip
    print(f"\nDirection: {src_ip} → {dst_ip}")
    if updates_src_to_dst:
        # Sort updates by timestamp
        updates_src_to_dst.sort(key=lambda x: x['timestamp'])
        
        # Find first and last updates
        first_update = updates_src_to_dst[0]
        last_update = updates_src_to_dst[-1]
        
        # Calculate convergence time
        convergence_time = last_update['timestamp'] - first_update['timestamp']
        
        print(f"First UPDATE: {first_update['human_time']} from {first_update['src']} to {first_update['dst']}")
        print(f"Last UPDATE: {last_update['human_time']} from {last_update['src']} to {last_update['dst']}")
        print(f"Convergence time: {convergence_time:.4f} seconds")
    else:
        print("No updates found in this direction")
    
    # Analysis for direction: dst_ip to src_ip
    print(f"\nDirection: {dst_ip} → {src_ip}")
    if updates_dst_to_src:
        # Sort updates by timestamp
        updates_dst_to_src.sort(key=lambda x: x['timestamp'])
        
        # Find first and last updates
        first_update = updates_dst_to_src[0]
        last_update = updates_dst_to_src[-1]
        
        # Calculate convergence time
        convergence_time = last_update['timestamp'] - first_update['timestamp']
        
        print(f"First UPDATE: {first_update['human_time']} from {first_update['src']} to {first_update['dst']}")
        print(f"Last UPDATE: {last_update['human_time']} from {last_update['src']} to {last_update['dst']}")
        print(f"Convergence time: {convergence_time:.4f} seconds")
    else:
        print("No updates found in this direction")
    
    # Overall analysis (for all directions combined)
    print(f"\nOverall Convergence Analysis (Both Directions):")
    updates.sort(key=lambda x: x['timestamp'])
    first_update = updates[0]
    last_update = updates[-1]
    convergence_time = last_update['timestamp'] - first_update['timestamp']
    print(f"First UPDATE: {first_update['human_time']} from {first_update['src']} to {first_update['dst']}")
    print(f"Last UPDATE: {last_update['human_time']} from {last_update['src']} to {last_update['dst']}")
    print(f"Total convergence time: {convergence_time:.4f} seconds")
    
    # Analyze prefix activity
    active_prefixes = set()
    for update in updates:
        for prefix in update['prefixes']:
            active_prefixes.add(prefix)
        for prefix in update['withdrawals']:
            active_prefixes.add(prefix)
    
    print(f"\nTotal active prefixes: {len(active_prefixes)}")
    
    # Get top prefixes with most updates
    prefix_activity = {}
    for prefix in active_prefixes:
        update_count = len(prefix_updates.get(prefix, []))
        withdrawal_count = len(prefix_withdrawals.get(prefix, []))
        prefix_activity[prefix] = update_count + withdrawal_count
    
    top_prefixes = sorted(prefix_activity.items(), key=lambda x: x[1], reverse=True)[:10]
    
    print("\nTop 10 prefixes with most activity:")
    for prefix, count in top_prefixes:
        print(f"{prefix}: {count} events")

    # Save detailed update information to separate CSV files
    if updates_src_to_dst:
        df = pd.DataFrame(updates_src_to_dst)
        df['prefixes'] = df['prefixes'].apply(lambda x: ', '.join(x) if x else '')
        df['withdrawals'] = df['withdrawals'].apply(lambda x: ', '.join(x) if x else '')
        df.to_csv(f'bgp_updates_{src_ip}_to_{dst_ip}.csv', index=False)
        print(f"Detailed update information saved to bgp_updates_{src_ip}_to_{dst_ip}.csv")
    
    if updates_dst_to_src:
        df = pd.DataFrame(updates_dst_to_src)
        df['prefixes'] = df['prefixes'].apply(lambda x: ', '.join(x) if x else '')
        df['withdrawals'] = df['withdrawals'].apply(lambda x: ', '.join(x) if x else '')
        df.to_csv(f'bgp_updates_{dst_ip}_to_{src_ip}.csv', index=False)
        print(f"Detailed update information saved to bgp_updates_{dst_ip}_to_{src_ip}.csv")

def detect_wireshark_flags(pcap_file):
    """
    Detect if Wireshark has already marked packets with flags like 
    retransmission or out-of-order.
    
    Returns True if Wireshark-parsed flags are detected.
    """
    try:
        packets = rdpcap(pcap_file)
        for pkt in packets[:100]:  # Check first 100 packets
            if IP in pkt and TCP in pkt:
                # Look for Wireshark annotations in packet summaries if available
                if hasattr(pkt, 'summary'):
                    summary = pkt.summary()
                    if any(flag in summary for flag in ["Retransmission", "Out-Of-Order", "Dup ACK"]):
                        return True
        return False
    except Exception as e:
        print(f"Error checking for Wireshark flags: {e}")
        return False

def analyze_bgp_withdrawals(pcap_file, router_ip_down, neighbors):
    """
    Specially analyze withdrawal behavior after a router goes down
    
    Args:
        pcap_file: Path to pcap file
        router_ip_down: IP of router that was shut down
        neighbors: List of neighbor router IPs
    """
    print(f"\n\n{'=' * 80}")
    print(f"ANALYZING WITHDRAWAL BEHAVIOR AFTER ROUTER {router_ip_down} SHUTDOWN")
    print(f"{'=' * 80}")
    
    try:
        packets = rdpcap(pcap_file)
    except Exception as e:
        print(f"Error reading pcap file: {e}")
        return
    
    # Find packets related to the neighbors
    last_seen_time = None
    withdrawals_after_down = []
    
    # Find the last time we saw traffic from the downed router
    for pkt in packets:
        if IP in pkt and pkt[IP].src == router_ip_down:
            last_seen_time = float(pkt.time)
    
    if not last_seen_time:
        print(f"Could not find any packets from router {router_ip_down}")
        return
    
    shutdown_time = datetime.fromtimestamp(last_seen_time).strftime('%Y-%m-%d %H:%M:%S.%f')
    print(f"Last packet from router {router_ip_down} seen at {shutdown_time}")
    
    # Look for withdrawals after the router went down
    for pkt_idx, pkt in enumerate(packets):
        if not (IP in pkt and TCP in pkt):
            continue
            
        ip_pkt = pkt[IP]
        tcp_pkt = pkt[TCP]
        
        # Only look at packets after the router went down
        if float(pkt.time) < last_seen_time:
            continue
        
        # Check if this is BGP traffic between neighbor routers
        is_bgp_traffic = tcp_pkt.sport == BGP_PORT or tcp_pkt.dport == BGP_PORT
        if not is_bgp_traffic:
            continue
            
        # Get TCP payload
        if not hasattr(tcp_pkt, 'payload') or len(bytes(tcp_pkt.payload)) == 0:
            continue
            
        payload = bytes(tcp_pkt.payload)
        offset = 0
        
        # Process BGP messages in the TCP payload
        while offset < len(payload):
            length, msg_type = parse_bgp_header(payload[offset:])
            
            if length is None or offset + length > len(payload):
                break
                
            msg_data = payload[offset:offset+length]
            
            # Process UPDATE messages with withdrawals
            if msg_type == BGP_UPDATE:
                prefixes, withdrawals = parse_bgp_update(msg_data)
                
                if withdrawals:
                    timestamp = float(pkt.time)
                    human_time = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S.%f')
                    time_since_down = timestamp - last_seen_time
                    
                    withdrawal_info = {
                        'timestamp': timestamp,
                        'human_time': human_time,
                        'time_since_down': time_since_down,
                        'src': ip_pkt.src,
                        'dst': ip_pkt.dst,
                        'withdrawals': withdrawals,
                        'pkt_idx': pkt_idx
                    }
                    withdrawals_after_down.append(withdrawal_info)
            
            offset += length
    
    # Analyze withdrawals
    if withdrawals_after_down:
        print(f"\nFound {len(withdrawals_after_down)} withdrawal events after router {router_ip_down} went down")
        
        # Group by source
        by_source = defaultdict(list)
        for withdrawal in withdrawals_after_down:
            by_source[withdrawal['src']].append(withdrawal)
        
        for src, withdrawals in by_source.items():
            first = min(withdrawals, key=lambda x: x['timestamp'])
            last = max(withdrawals, key=lambda x: x['timestamp'])
            
            total_prefixes = sum(len(w['withdrawals']) for w in withdrawals)
            
            print(f"\n{src} sent {len(withdrawals)} withdrawal messages containing {total_prefixes} prefixes:")
            print(f"  First withdrawal: {first['time_since_down']:.4f} seconds after router down")
            print(f"  Last withdrawal: {last['time_since_down']:.4f} seconds after router down")
            print(f"  Duration of withdrawal process: {last['time_since_down'] - first['time_since_down']:.4f} seconds")
            
            # Show some example prefixes
            all_prefixes = []
            for w in withdrawals:
                all_prefixes.extend(w['withdrawals'])
            
            print(f"  Example withdrawn prefixes:")
            for prefix in list(set(all_prefixes))[:5]:
                print(f"    - {prefix}")
    else:
        print("\nNo withdrawal messages found after router shutdown!")
        print("This suggests potential BGP withdrawal messages were missed or not sent.")

def main():
    if len(sys.argv) < 3:
        print("Usage: python pcap_anlys.py <pcap_file> <source_ip> <destination_ip> [<additional_peer_ip> ...]")
        print("Example: python pcap_anlys.py all_bgp_routes.pcap 10.100.0.151 10.100.0.152 10.100.0.150")
        sys.exit(1)
    
    pcap_file = sys.argv[1]
    peer_ips = sys.argv[2:]
    
    # Warn about potential Wireshark flags
    if detect_wireshark_flags(pcap_file):
        print("WARNING: This pcap file appears to contain Wireshark annotations.")
        print("Some packet flags like retransmissions may not be correctly detected by scapy.")
    
    # Analyze convergence between the peers
    analyze_bgp_convergence(pcap_file, *peer_ips)
    
    # If we have a downed router to analyze (router 149 in your case)
    if len(peer_ips) >= 3:
        # Analyze withdrawal behavior - assuming peer_ips[2] is the router that was shut down (like 10.100.0.149)
        # You can adjust which IP represents the downed router if needed
        router_down_ip = "10.100.0.150"  # IP of Router 149
        analyze_bgp_withdrawals(pcap_file, router_down_ip, peer_ips)

if __name__ == "__main__":
    main()
