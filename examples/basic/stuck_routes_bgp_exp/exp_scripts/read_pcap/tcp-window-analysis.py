#!/usr/bin/env python3
import sys
import os
from collections import defaultdict
from scapy.all import rdpcap, IP, TCP, Raw
from datetime import datetime
import argparse
import statistics
import struct

# Router IPs
ROUTER149_IP = "10.100.0.149"
ROUTER150_IP = "10.100.0.150"
ROUTER151_IP = "10.100.0.151"
ROUTER152_IP = "10.100.0.152"

# BGP port
BGP_PORT = 179

# BGP message types
BGP_OPEN = 1
BGP_UPDATE = 2
BGP_NOTIFICATION = 3
BGP_KEEPALIVE = 4

# BGP marker (16 bytes of 0xFF)
BGP_MARKER = b'\xff' * 16

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

def analyze_tcp_windows_for_timing(pcap_file):
    """Analyze TCP window behavior to determine optimal shutdown timing."""
    print(f"\n[*] Analyzing {pcap_file} for TCP window patterns...")
    
    try:
        packets = rdpcap(pcap_file)
        print(f"  -> Read {len(packets)} packets successfully")
    except Exception as e:
        print(f"  -> Error reading pcap file: {e}")
        return None

    # Data structures
    r150_to_r151_update_times = []  # When router 150 sends BGP UPDATE to router 151
    r151_zero_window_times = []     # When router 151 sends TCP zero window
    r151_window_sizes = []          # Track window size changes from router 151
    r151_bgp_sessions = set()       # Track BGP sessions involving router 151
    
    # Connection tracking for determining BGP session establishment
    connections = {}
    
    # Track when the experiment started (first packet)
    exp_start_time = packets[0].time if packets else None
    
    # First pass: find BGP connections and updates
    print("  -> Looking for BGP connections and updates from 150 to 151...")
    for i, pkt in enumerate(packets):
        if IP in pkt and TCP in pkt:
            ip_pkt = pkt[IP]
            tcp_pkt = pkt[TCP]
            
            # Record relative timestamp
            rel_time = float(pkt.time) - exp_start_time if exp_start_time else 0
            
            # Check if this is traffic between router 150 and 151
            is_r150_to_r151 = (ip_pkt.src == ROUTER150_IP and ip_pkt.dst == ROUTER151_IP)
            is_r151_to_r150 = (ip_pkt.src == ROUTER151_IP and ip_pkt.dst == ROUTER150_IP)
            
            # Check if this is BGP traffic
            is_bgp = (tcp_pkt.sport == BGP_PORT or tcp_pkt.dport == BGP_PORT)
            
            # Track BGP sessions involving router 151
            if is_bgp and (ROUTER151_IP in ip_pkt.src or ROUTER151_IP in ip_pkt.dst):
                if ip_pkt.src < ip_pkt.dst:
                    session_key = f"{ip_pkt.src}-{ip_pkt.dst}"
                else:
                    session_key = f"{ip_pkt.dst}-{ip_pkt.src}"
                r151_bgp_sessions.add(session_key)
            
            # Track TCP window sizes from router 151
            if is_r151_to_r150:
                window_size = tcp_pkt.window
                r151_window_sizes.append((rel_time, window_size))
                
                # Detect zero windows
                if window_size == 0:
                    r151_zero_window_times.append(rel_time)
                    print(f"  -> Zero window detected at {rel_time:.2f}s from router 151 to 150")
            
            # Detect BGP UPDATE messages from router 150 to 151
            if is_r150_to_r151 and is_bgp and Raw in pkt:
                payload = bytes(pkt[Raw])
                
                # Parse BGP header
                length, msg_type = parse_bgp_header(payload)
                
                if msg_type == BGP_UPDATE:
                    r150_to_r151_update_times.append(rel_time)
                    print(f"  -> BGP UPDATE detected at {rel_time:.2f}s from router 150 to 151")
                    
                    # Check if this is a response to router 149 shutdown (withdrawal)
                    if "withdraw" in pkt.summary().lower() or "withdrawal" in pkt.summary().lower():
                        print(f"  -> Likely withdrawal message at {rel_time:.2f}s (router 149 failure propagation)")
    
    # Print summary of BGP activity
    print(f"  -> Found {len(r150_to_r151_update_times)} BGP UPDATE messages from router 150 to 151")
    print(f"  -> Found {len(r151_zero_window_times)} TCP zero window events from router 151")
    print(f"  -> Found {len(r151_bgp_sessions)} BGP sessions involving router 151")
    
    # Calculate window size decrease events
    window_decreases = []
    if len(r151_window_sizes) > 1:
        for i in range(1, len(r151_window_sizes)):
            prev_time, prev_window = r151_window_sizes[i-1]
            curr_time, curr_window = r151_window_sizes[i]
            
            # Check for significant window size decrease
            if prev_window > curr_window and prev_window > 0:
                decrease_pct = (prev_window - curr_window) / prev_window * 100
                if decrease_pct > 50:  # More than 50% decrease
                    window_decreases.append(curr_time)
                    if decrease_pct > 90:  # Very significant decrease
                        print(f"  -> Major window decrease ({decrease_pct:.1f}%) at {curr_time:.2f}s from router 151")
    
    # Now analyze the timing relationship between BGP UPDATEs from 150 to 151 and zero windows
    recommendations = {}
    
    # Find time between router 150 UPDATE messages and router 151 zero windows
    if r150_to_r151_update_times and r151_zero_window_times:
        print("\n[+] Analyzing timing between BGP UPDATEs and TCP zero windows...")
        update_to_zero_delays = []
        
        for zw_time in r151_zero_window_times:
            # Find the closest preceding UPDATE message
            preceding_updates = [t for t in r150_to_r151_update_times if t <= zw_time]
            if preceding_updates:
                closest_update_time = max(preceding_updates)
                delay = zw_time - closest_update_time
                update_to_zero_delays.append(delay)
                print(f"  -> Zero window at {zw_time:.2f}s occurred {delay:.2f}s after UPDATE at {closest_update_time:.2f}s")
        
        if update_to_zero_delays:
            avg_delay = statistics.mean(update_to_zero_delays)
            recommendations['update_to_zero_timing'] = avg_delay
            print(f"\n[+] Zero windows typically occur {avg_delay:.2f}s after BGP UPDATE messages from 150 to 151")
    
    # Find time between significant window decreases and complete zero windows
    if window_decreases and r151_zero_window_times:
        decrease_to_zero_delays = []
        
        for zw_time in r151_zero_window_times:
            # Find the closest preceding window decrease
            preceding_decreases = [t for t in window_decreases if t <= zw_time]
            if preceding_decreases:
                closest_decrease_time = max(preceding_decreases)
                delay = zw_time - closest_decrease_time
                decrease_to_zero_delays.append(delay)
        
        if decrease_to_zero_delays:
            avg_delay = statistics.mean(decrease_to_zero_delays)
            recommendations['decrease_to_zero_timing'] = avg_delay
            print(f"[+] Zero windows typically occur {avg_delay:.2f}s after significant window size decreases")
            
    # Look for withdrawal-specific patterns
    withdrawal_times = []
    for i, pkt in enumerate(packets):
        if IP in pkt and TCP in pkt and Raw in pkt:
            ip_pkt = pkt[IP]
            tcp_pkt = pkt[TCP]
            
            # Check if this is BGP traffic from 150 to 151
            if (ip_pkt.src == ROUTER150_IP and ip_pkt.dst == ROUTER151_IP and
                (tcp_pkt.sport == BGP_PORT or tcp_pkt.dport == BGP_PORT)):
                
                # Check if this packet is after 149 should be shut down (30+ seconds into capture)
                rel_time = float(pkt.time) - exp_start_time if exp_start_time else 0
                if rel_time > 30:  # Focus on later part of capture when 149 shutdown should happen
                    payload = bytes(pkt[Raw])
                    length, msg_type = parse_bgp_header(payload)
                    
                    if msg_type == BGP_UPDATE:
                        # Check for withdrawal indicators in packet summary
                        if "withdraw" in pkt.summary().lower() or "withdrawal" in pkt.summary().lower():
                            withdrawal_times.append(rel_time)
                            print(f"  -> BGP withdrawal detected at {rel_time:.2f}s from router 150 to 151")
    
    # Find time between withdrawals and zero windows
    if withdrawal_times and r151_zero_window_times:
        withdrawal_to_zero_delays = []
        
        for zw_time in r151_zero_window_times:
            # Find withdrawals that precede this zero window
            preceding_withdrawals = [t for t in withdrawal_times if t <= zw_time]
            if preceding_withdrawals:
                closest_withdrawal_time = max(preceding_withdrawals)
                delay = zw_time - closest_withdrawal_time
                withdrawal_to_zero_delays.append(delay)
                print(f"  -> Zero window at {zw_time:.2f}s occurred {delay:.2f}s after withdrawal at {closest_withdrawal_time:.2f}s")
        
        if withdrawal_to_zero_delays:
            avg_delay = statistics.mean(withdrawal_to_zero_delays)
            recommendations['withdrawal_to_zero_timing'] = avg_delay
            print(f"\n[+] Zero windows typically occur {avg_delay:.2f}s after BGP withdrawals from 150 to 151")
    
    # Calculate optimal shutdown timing
    if recommendations:
        print("\n[*] Calculating optimal shutdown timing...")
        
        # Determine the best timing for your scenario
        # First priority: Use update_to_zero_timing if available (most direct relationship)
        if 'update_to_zero_timing' in recommendations:
            update_to_zero = recommendations['update_to_zero_timing']
            print(f"  -> Based on time between UPDATEs and zero windows: {update_to_zero:.2f}s")
            
            # Shutdown should happen *before* the zero window, to cause the problem during withdrawal
            # So we subtract a small buffer time (1-2 seconds) from when zero windows typically appear
            optimal_timing = max(1, update_to_zero - 1.5)
            recommendations['optimal_timing'] = optimal_timing
            
            print(f"\n[*] RECOMMENDED TIMING: Shut down router 149 approximately {optimal_timing:.2f}s after router 150 sends BGP UPDATEs to 151")
            print(f"[*] This should place the withdrawal messages during a period of TCP zero window vulnerability")
            
            # Map this to your script's timing parameter
            current_offset = 3  # Current value from your script
            print(f"[*] Consider changing SHUTDOWN_OFFSET from {current_offset} to {optimal_timing:.0f} in your script")
            
        # Second priority: Use withdrawal_to_zero_timing if available
        elif 'withdrawal_to_zero_timing' in recommendations:
            withdrawal_to_zero = recommendations['withdrawal_to_zero_timing']
            print(f"  -> Based on time between withdrawals and zero windows: {withdrawal_to_zero:.2f}s")
            
            optimal_timing = max(1, withdrawal_to_zero - 1)
            recommendations['optimal_timing'] = optimal_timing
            
            print(f"\n[*] RECOMMENDED TIMING: Shut down router 149 when router 150 is about to send withdrawals to 151")
            print(f"[*] Time the shutdown {optimal_timing:.2f}s before TCP zero windows typically appear")
            print(f"[*] Consider changing SHUTDOWN_OFFSET from 3 to match this timing")
            
        # Third priority: Use decrease_to_zero_timing
        elif 'decrease_to_zero_timing' in recommendations:
            decrease_to_zero = recommendations['decrease_to_zero_timing']
            print(f"  -> Based on time between window decreases and zero windows: {decrease_to_zero:.2f}s")
            
            optimal_timing = max(1, decrease_to_zero - 1)
            recommendations['optimal_timing'] = optimal_timing
            
            print(f"\n[*] RECOMMENDED TIMING: Shut down router 149 when router 151's TCP window is starting to decrease")
            print(f"[*] This should be approximately {optimal_timing:.2f}s before zero windows occur")
            print(f"[*] Consider changing SHUTDOWN_OFFSET in your script accordingly")
    else:
        print("\n[!] Insufficient data to provide timing recommendation")
        print("[!] No TCP zero windows or BGP UPDATEs detected between router 150 and 151")
    
    # Add more diagnostic information if zero windows were found
    if r151_zero_window_times:
        print("\n[*] TCP Zero Window Events Details:")
        for i, zw_time in enumerate(sorted(r151_zero_window_times)):
            print(f"  -> Zero Window #{i+1}: {zw_time:.2f}s into the capture")
        
        # Calculate average duration of zero window condition if possible
        if len(r151_window_sizes) > 1:
            zero_window_durations = []
            in_zero_window = False
            zero_start = 0
            
            for time, size in sorted(r151_window_sizes):
                if not in_zero_window and size == 0:
                    # Start of zero window
                    in_zero_window = True
                    zero_start = time
                elif in_zero_window and size > 0:
                    # End of zero window
                    duration = time - zero_start
                    zero_window_durations.append(duration)
                    in_zero_window = False
            
            if zero_window_durations:
                avg_duration = statistics.mean(zero_window_durations)
                print(f"\n[*] Average duration of TCP zero window conditions: {avg_duration:.2f}s")
                print(f"[*] This suggests router 151 is experiencing congestion for {avg_duration:.2f}s on average")
    
    # Return recommendations
    return recommendations

def analyze_multiple_pcaps(pcap_files):
    """Analyze multiple pcap files and provide consolidated recommendation."""
    all_recommendations = []
    successful_experiments = []
    
    # Check for TCP zero windows in each pcap
    for pcap_file in pcap_files:
        if not os.path.exists(pcap_file):
            print(f"[!] Error: PCAP file {pcap_file} not found")
            continue
        
        exp_num = os.path.basename(pcap_file).split('_')[0]
        print(f"\n[*] === Analyzing Experiment {exp_num} ===")
        
        try:
            recommendations = analyze_tcp_windows_for_timing(pcap_file)
            if recommendations and any(key in recommendations for key in ['update_to_zero_timing', 'withdrawal_to_zero_timing']):
                all_recommendations.append(recommendations)
                successful_experiments.append(exp_num)
        except Exception as e:
            import traceback
            print(f"[!] Error analyzing {pcap_file}: {e}")
            traceback.print_exc()
    
    # Consolidate recommendations
    if all_recommendations:
        print("\n[*] === Consolidated Analysis ===")
        print(f"[*] Found {len(successful_experiments)} experiments with useful data for timing analysis")
        print(f"[*] Successful experiments: {', '.join(successful_experiments)}")
        
        # Extract timing values for each category
        update_to_zero_timings = [r.get('update_to_zero_timing') for r in all_recommendations if 'update_to_zero_timing' in r]
        withdrawal_to_zero_timings = [r.get('withdrawal_to_zero_timing') for r in all_recommendations if 'withdrawal_to_zero_timing' in r]
        decrease_to_zero_timings = [r.get('decrease_to_zero_timing') for r in all_recommendations if 'decrease_to_zero_timing' in r]
        optimal_timings = [r.get('optimal_timing') for r in all_recommendations if 'optimal_timing' in r]
        
        # Calculate consolidated recommendations
        consolidated = {}
        
        if update_to_zero_timings:
            avg_update_to_zero = statistics.mean(update_to_zero_timings)
            consolidated['update_to_zero_timing'] = avg_update_to_zero
            print(f"[+] Average time from BGP UPDATEs to zero windows: {avg_update_to_zero:.2f}s")
        
        if withdrawal_to_zero_timings:
            avg_withdrawal_to_zero = statistics.mean(withdrawal_to_zero_timings)
            consolidated['withdrawal_to_zero_timing'] = avg_withdrawal_to_zero
            print(f"[+] Average time from withdrawals to zero windows: {avg_withdrawal_to_zero:.2f}s")
        
        if decrease_to_zero_timings:
            avg_decrease_to_zero = statistics.mean(decrease_to_zero_timings)
            consolidated['decrease_to_zero_timing'] = avg_decrease_to_zero
            print(f"[+] Average time from window decreases to zero windows: {avg_decrease_to_zero:.2f}s")
        
        if optimal_timings:
            avg_optimal_timing = statistics.mean(optimal_timings)
            consolidated['optimal_timing'] = avg_optimal_timing
            
            # Calculate variance to determine confidence level
            if len(optimal_timings) > 1:
                variance = statistics.variance(optimal_timings)
                std_dev = statistics.stdev(optimal_timings)
                print(f"[+] Timing consistency (standard deviation): {std_dev:.2f}s")
                
                confidence = "high" if std_dev < 1 else "medium" if std_dev < 2 else "low"
                print(f"[+] Confidence level in recommendation: {confidence}")
            
            print(f"\n[*] FINAL RECOMMENDATION: Shut down router 149 approximately {avg_optimal_timing:.2f}s after router 150 starts sending BGP updates to router 151")
            print(f"[*] Consider changing SHUTDOWN_OFFSET from 3 to {avg_optimal_timing:.0f} in your script")
            
            # Additional insights for causing stuck routes
            print(f"\n[*] To maximize likelihood of stuck routes:")
            print(f"[*] 1. Ensure router 149 shutdown occurs when router 150 is actively sending")
            print(f"[*]    updates/withdrawals to router 151")
            print(f"[*] 2. The shutdown should happen just before router 151 experiences TCP zero")
            print(f"[*]    window conditions (typically {update_to_zero_timings[0] if update_to_zero_timings else 'several'}s after updates start)")
            print(f"[*] 3. This timing will ensure withdrawals arrive when router 151 cannot process them")
        else:
            print("\n[!] Insufficient data to provide optimal timing recommendation")
            
            # Fallback recommendation based on available data
            if consolidated:
                if 'update_to_zero_timing' in consolidated:
                    fallback_timing = max(1, consolidated['update_to_zero_timing'] - 1)
                    print(f"[*] FALLBACK RECOMMENDATION: Try {fallback_timing:.0f}s after observing BGP updates from 150 to 151")
                elif 'decrease_to_zero_timing' in consolidated:
                    fallback_timing = max(1, consolidated['decrease_to_zero_timing'] - 1)
                    print(f"[*] FALLBACK RECOMMENDATION: Try {fallback_timing:.0f}s after observing TCP window decreases from 151")
    else:
        print("\n[!] No useful timing data found in any of the pcap files")
        print("[!] Suggestions:")
        print("[!] 1. Check that your pcap capture includes BGP traffic between routers 150 and 151")
        print("[!] 2. Ensure TCP flow control issues (zero windows) are occurring in router 151")
        print("[!] 3. Try running more experiments with different timing values")


def main():
    parser = argparse.ArgumentParser(description='Analyze TCP window behavior to determine optimal 149 shutdown timing')
    parser.add_argument('pcap_files', nargs='+', help='PCAP files to analyze (wildcards supported)')
    args = parser.parse_args()
    
    analyze_multiple_pcaps(args.pcap_files)

if __name__ == "__main__":
    main()
