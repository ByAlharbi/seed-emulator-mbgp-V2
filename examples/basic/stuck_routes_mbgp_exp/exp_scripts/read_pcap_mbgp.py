#!/usr/bin/env python3
import sys
from scapy.all import rdpcap, IP, TCP
from collections import defaultdict
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
import argparse
import re

def analyze_grpc_traffic(pcap_file, src_ip=None, dst_ip=None, grpc_port=50051):
    """
    Analyze gRPC traffic to determine route exchange timing.
    
    Args:
        pcap_file (str): Path to the pcap file
        src_ip (str, optional): Filter by source IP
        dst_ip (str, optional): Filter by destination IP
        grpc_port (int, optional): gRPC port (default: 50051)
    
    Returns:
        dict: Statistics about route exchange timing
    """
    print(f"Analyzing gRPC traffic from {pcap_file}...")
    
    try:
        packets = rdpcap(pcap_file)
    except Exception as e:
        print(f"Error reading pcap file: {e}")
        return {}
    
    # Data structures to track traffic
    tcp_streams = defaultdict(list)
    tcp_stream_map = {}  # Maps (src_ip, src_port, dst_ip, dst_port) to stream ID
    next_stream_id = 0
    
    # Track traffic statistics
    stats = {
        'first_packet_time': None,
        'last_packet_time': None,
        'syn_time': None,
        'first_data_time': None,
        'last_data_time': None,
        'fin_time': None,
        'rst_time': None,
        'total_data_bytes': 0,
        'streams': {},
        'grpc_metadata': defaultdict(list),
        'packet_timeline': [],
    }
    
    # First pass: identify TCP streams
    for pkt_idx, pkt in enumerate(packets):
        timestamp = float(pkt.time)
        
        # Track overall first/last packet times
        if stats['first_packet_time'] is None or timestamp < stats['first_packet_time']:
            stats['first_packet_time'] = timestamp
        if stats['last_packet_time'] is None or timestamp > stats['last_packet_time']:
            stats['last_packet_time'] = timestamp
        
        if IP in pkt and TCP in pkt:
            ip_pkt = pkt[IP]
            tcp_pkt = pkt[TCP]
            
            # Apply source/dest filters if provided
            if src_ip and ip_pkt.src != src_ip and ip_pkt.dst != src_ip:
                continue
            if dst_ip and ip_pkt.src != dst_ip and ip_pkt.dst != dst_ip:
                continue
            
            # Check if this is gRPC traffic based on port
            is_grpc = tcp_pkt.dport == grpc_port or tcp_pkt.sport == grpc_port
            if not is_grpc:
                continue
                
            # Track this packet in timeline
            pkt_info = {
                'timestamp': timestamp,
                'src': ip_pkt.src,
                'dst': ip_pkt.dst,
                'src_port': tcp_pkt.sport,
                'dst_port': tcp_pkt.dport,
                'flags': get_tcp_flags(tcp_pkt),
                'seq': tcp_pkt.seq,
                'ack': tcp_pkt.ack if hasattr(tcp_pkt, 'ack') else None,
                'payload_len': len(bytes(tcp_pkt.payload)) if hasattr(tcp_pkt, 'payload') else 0,
                'is_retransmission': is_marked_retransmission(pkt),
                'idx': pkt_idx
            }
            stats['packet_timeline'].append(pkt_info)
            
            # Identify the TCP stream this packet belongs to
            stream_key = None
            if 'S' in pkt_info['flags'] and not 'A' in pkt_info['flags']:  # SYN packet
                # This is the start of a new stream
                stream_key = (ip_pkt.src, tcp_pkt.sport, ip_pkt.dst, tcp_pkt.dport)
                tcp_stream_map[stream_key] = next_stream_id
                reverse_key = (ip_pkt.dst, tcp_pkt.dport, ip_pkt.src, tcp_pkt.sport)
                tcp_stream_map[reverse_key] = next_stream_id
                next_stream_id += 1
                
                # Update SYN time if this is the first one
                if stats['syn_time'] is None or timestamp < stats['syn_time']:
                    stats['syn_time'] = timestamp
            else:
                # Try to find the stream for this packet
                forward_key = (ip_pkt.src, tcp_pkt.sport, ip_pkt.dst, tcp_pkt.dport)
                reverse_key = (ip_pkt.dst, tcp_pkt.dport, ip_pkt.src, tcp_pkt.sport)
                
                if forward_key in tcp_stream_map:
                    stream_key = forward_key
                elif reverse_key in tcp_stream_map:
                    stream_key = reverse_key
            
            if stream_key and stream_key in tcp_stream_map:
                stream_id = tcp_stream_map[stream_key]
                pkt_info['stream_id'] = stream_id
                tcp_streams[stream_id].append(pkt_info)
                
                # Check for data-carrying packets (excluding retransmissions)
                if pkt_info['payload_len'] > 0 and not pkt_info['is_retransmission']:
                    stats['total_data_bytes'] += pkt_info['payload_len']
                    
                    # Track first/last data times
                    if stats['first_data_time'] is None or timestamp < stats['first_data_time']:
                        stats['first_data_time'] = timestamp
                    if stats['last_data_time'] is None or timestamp > stats['last_data_time']:
                        stats['last_data_time'] = timestamp
                
                # Track FIN and RST packets
                if 'F' in pkt_info['flags']:
                    if stats['fin_time'] is None or timestamp < stats['fin_time']:
                        stats['fin_time'] = timestamp
                
                if 'R' in pkt_info['flags']:
                    if stats['rst_time'] is None or timestamp < stats['rst_time']:
                        stats['rst_time'] = timestamp
                
                # Extract gRPC metadata if possible
                if pkt_info['payload_len'] > 0:
                    payload = bytes(tcp_pkt.payload)
                    
                    # Look for HTTP/2 or gRPC headers
                    if b'HTTP/2' in payload or b'grpc' in payload:
                        stats['grpc_metadata'][stream_id].append({
                            'timestamp': timestamp,
                            'size': pkt_info['payload_len'],
                            'contains_http2_header': b'HTTP/2' in payload,
                            'contains_grpc_header': b'grpc' in payload,
                            'contains_path': b':path' in payload,
                            'contains_authority': b':authority' in payload
                        })
    
    # Process stream statistics
    for stream_id, packets in tcp_streams.items():
        if packets:
            # Sort packets by timestamp
            packets.sort(key=lambda x: x['timestamp'])
            
            # Calculate stream duration and data size
            first_pkt = packets[0]
            last_pkt = packets[-1]
            duration = last_pkt['timestamp'] - first_pkt['timestamp']
            
            # Count non-retransmitted data bytes
            data_bytes = sum(pkt['payload_len'] for pkt in packets if pkt['payload_len'] > 0 and not pkt['is_retransmission'])
            
            # Count retransmissions
            retransmissions = sum(1 for pkt in packets if pkt['is_retransmission'])
            
            # Track handshake packets
            syn_packets = [pkt for pkt in packets if 'S' in pkt['flags'] and not 'A' in pkt['flags']]
            synack_packets = [pkt for pkt in packets if 'S' in pkt['flags'] and 'A' in pkt['flags']]
            fin_packets = [pkt for pkt in packets if 'F' in pkt['flags']]
            rst_packets = [pkt for pkt in packets if 'R' in pkt['flags']]
            
            # Detect connection establishment time
            conn_establish_time = None
            if syn_packets and synack_packets:
                syn_time = syn_packets[0]['timestamp']
                for pkt in packets:
                    if 'A' in pkt['flags'] and pkt['timestamp'] > syn_time:
                        conn_establish_time = pkt['timestamp'] - syn_time
                        break
            
            # Store stream statistics
            stats['streams'][stream_id] = {
                'first_packet': first_pkt['timestamp'],
                'last_packet': last_pkt['timestamp'],
                'duration': duration,
                'data_bytes': data_bytes,
                'packet_count': len(packets),
                'retransmission_count': retransmissions,
                'connection_time': conn_establish_time,
                'has_syn': len(syn_packets) > 0,
                'has_fin': len(fin_packets) > 0,
                'has_rst': len(rst_packets) > 0,
                'source_ip': first_pkt['src'],
                'dest_ip': first_pkt['dst']
            }
    
    # Calculate overall durations
    if stats['first_data_time'] and stats['last_data_time']:
        stats['data_transfer_duration'] = stats['last_data_time'] - stats['first_data_time']
    else:
        stats['data_transfer_duration'] = 0
    
    if stats['first_packet_time'] and stats['last_packet_time']:
        stats['total_duration'] = stats['last_packet_time'] - stats['first_packet_time']
    else:
        stats['total_duration'] = 0
    
    # Estimate number of routes
    # Assuming average of ~40 bytes per route in gRPC representation
    bytes_per_route = 40  # Adjust based on your actual route size
    stats['estimated_routes'] = stats['total_data_bytes'] / bytes_per_route
    if stats['data_transfer_duration'] > 0:
        stats['routes_per_second'] = stats['estimated_routes'] / stats['data_transfer_duration']
    else:
        stats['routes_per_second'] = 0
    
    return stats

def get_tcp_flags(tcp_pkt):
    """Extract TCP flags as a string."""
    flags = ''
    
    if tcp_pkt.flags & 0x01:  # FIN
        flags += 'F'
    if tcp_pkt.flags & 0x02:  # SYN
        flags += 'S'
    if tcp_pkt.flags & 0x04:  # RST
        flags += 'R'
    if tcp_pkt.flags & 0x08:  # PSH
        flags += 'P'
    if tcp_pkt.flags & 0x10:  # ACK
        flags += 'A'
    if tcp_pkt.flags & 0x20:  # URG
        flags += 'U'
    if tcp_pkt.flags & 0x40:  # ECE
        flags += 'E'
    if tcp_pkt.flags & 0x80:  # CWR
        flags += 'C'
    
    return flags

def is_marked_retransmission(pkt):
    """Check if a packet is marked as a retransmission by Wireshark."""
    # Check common Wireshark annotations that might be stored in the packet
    retrans_indicators = ['retransmission', 'out-of-order', 'duplicate']
    
    # Check packet summary if available
    if hasattr(pkt, 'summary'):
        summary = pkt.summary().lower()
        for indicator in retrans_indicators:
            if indicator in summary:
                return True
    
    # Check for any retransmission attributes Wireshark might have added
    for indicator in retrans_indicators:
        if hasattr(pkt, indicator) or hasattr(pkt, f'tcp_{indicator}'):
            return True
    
    return False

def extract_capture_metadata(pcap_file):
    """Extract metadata about the capture file."""
    try:
        packets = rdpcap(pcap_file)
        first_timestamp = None
        last_timestamp = None
        packet_count = len(packets)
        
        if packet_count > 0:
            first_timestamp = float(packets[0].time)
            last_timestamp = float(packets[-1].time)
        
        return {
            'file': pcap_file,
            'packet_count': packet_count,
            'first_timestamp': first_timestamp,
            'last_timestamp': last_timestamp,
            'duration': last_timestamp - first_timestamp if first_timestamp and last_timestamp else 0
        }
    except Exception as e:
        print(f"Error extracting metadata: {e}")
        return {
            'file': pcap_file,
            'error': str(e)
        }

def scan_for_common_protocols(pcap_file):
    """Scan the pcap for common protocols and ports."""
    try:
        packets = rdpcap(pcap_file)
        protocols = defaultdict(int)
        tcp_ports = defaultdict(int)
        udp_ports = defaultdict(int)
        ip_pairs = defaultdict(int)
        
        for pkt in packets:
            if IP in pkt:
                ip_pkt = pkt[IP]
                protocols[ip_pkt.proto] += 1
                ip_pair = f"{ip_pkt.src} <-> {ip_pkt.dst}"
                ip_pairs[ip_pair] += 1
                
                if TCP in pkt:
                    tcp_pkt = pkt[TCP]
                    tcp_ports[tcp_pkt.sport] += 1
                    tcp_ports[tcp_pkt.dport] += 1
                elif UDP in pkt:
                    udp_pkt = pkt[UDP]
                    udp_ports[udp_pkt.sport] += 1
                    udp_ports[udp_pkt.dport] += 1
        
        # Convert protocol numbers to names
        protocol_names = {
            1: 'ICMP',
            6: 'TCP',
            17: 'UDP',
            47: 'GRE',
            50: 'ESP',
            89: 'OSPF',
            132: 'SCTP'
        }
        
        named_protocols = {protocol_names.get(proto, f"Proto {proto}"): count 
                          for proto, count in protocols.items()}
        
        # Find most common ports
        top_tcp_ports = sorted(tcp_ports.items(), key=lambda x: x[1], reverse=True)[:10]
        top_udp_ports = sorted(udp_ports.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Find most common IP pairs
        top_ip_pairs = sorted(ip_pairs.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            'protocols': named_protocols,
            'top_tcp_ports': top_tcp_ports,
            'top_udp_ports': top_udp_ports,
            'top_ip_pairs': top_ip_pairs
        }
    except Exception as e:
        print(f"Error scanning protocols: {e}")
        return {'error': str(e)}

def format_time(seconds):
    """Format seconds as a human-readable time string."""
    return datetime.fromtimestamp(seconds).strftime('%Y-%m-%d %H:%M:%S.%f')

def print_stats(stats):
    """Print formatted statistics."""
    print("\n=== gRPC ROUTE EXCHANGE ANALYSIS ===")
    
    # Basic statistics
    if 'first_packet_time' in stats and stats['first_packet_time']:
        print(f"\nCapture Timeframe:")
        print(f"  First packet: {format_time(stats['first_packet_time'])}")
        print(f"  Last packet: {format_time(stats['last_packet_time'])}")
        print(f"  Total capture duration: {stats['total_duration']:.6f} seconds")
    
    # Connection timing
    print("\nConnection Timeline:")
    if stats.get('syn_time'):
        print(f"  First SYN: {format_time(stats['syn_time'])}")
    if stats.get('first_data_time'):
        print(f"  First data packet: {format_time(stats['first_data_time'])}")
    if stats.get('last_data_time'):
        print(f"  Last data packet: {format_time(stats['last_data_time'])}")
    if stats.get('fin_time'):
        print(f"  First FIN: {format_time(stats['fin_time'])}")
    if stats.get('rst_time'):
        print(f"  First RST: {format_time(stats['rst_time'])}")
    
    if stats.get('data_transfer_duration'):
        print(f"\nData Transfer:")
        print(f"  Duration: {stats['data_transfer_duration']:.6f} seconds")
        print(f"  Total data bytes: {stats['total_data_bytes']} bytes")
        print(f"  Estimated routes: {stats['estimated_routes']:.0f}")
        print(f"  Routes per second: {stats['routes_per_second']:.2f}")
    
    # Stream details
    print(f"\nTCP Streams: {len(stats.get('streams', {}))}")
    for stream_id, stream_data in stats.get('streams', {}).items():
        print(f"\n  Stream {stream_id} ({stream_data['source_ip']} -> {stream_data['dest_ip']}):")
        print(f"    Duration: {stream_data['duration']:.6f} seconds")
        print(f"    Data bytes: {stream_data['data_bytes']} bytes")
        print(f"    Packet count: {stream_data['packet_count']}")
        print(f"    Retransmissions: {stream_data['retransmission_count']}")
        if stream_data.get('connection_time'):
            print(f"    Connection establishment time: {stream_data['connection_time'] * 1000:.2f} ms")

def plot_timeline(stats, output_file=None):
    """Create a visualization of the gRPC traffic timeline."""
    if not stats or 'packet_timeline' not in stats or not stats['packet_timeline']:
        print("No packet timeline data available for plotting")
        return
    
    # Extract timeline data
    timeline_data = stats['packet_timeline']
    min_time = min(pkt['timestamp'] for pkt in timeline_data)
    
    # Create pandas DataFrame for plotting
    df = pd.DataFrame([{
        'time_offset': pkt['timestamp'] - min_time,
        'size': pkt['payload_len'],
        'src': pkt['src'],
        'dst': pkt['dst'],
        'flags': pkt['flags'],
        'retransmission': pkt['is_retransmission']
    } for pkt in timeline_data])
    
    # Create the plot
    plt.figure(figsize=(14, 10))
    
    # Plot packet sizes over time
    ax1 = plt.subplot(2, 1, 1)
    df_clean = df[~df['retransmission']]  # Exclude retransmissions
    df_retrans = df[df['retransmission']]  # Only retransmissions
    
    # Regular packets
    ax1.scatter(df_clean['time_offset'], df_clean['size'], 
              alpha=0.7, s=30, marker='o', label='Normal Packets')
    
    # Retransmissions
    if not df_retrans.empty:
        ax1.scatter(df_retrans['time_offset'], df_retrans['size'], 
                  alpha=0.7, s=30, marker='x', color='red', label='Retransmissions')
    
    # Add special markers for SYN, FIN, RST
    syn_packets = df[df['flags'].str.contains('S') & ~df['flags'].str.contains('A')]
    synack_packets = df[df['flags'].str.contains('S') & df['flags'].str.contains('A')]
    fin_packets = df[df['flags'].str.contains('F')]
    rst_packets = df[df['flags'].str.contains('R')]
    
    if not syn_packets.empty:
        ax1.scatter(syn_packets['time_offset'], syn_packets['size'], 
                  s=120, marker='^', color='green', label='SYN')
    
    if not synack_packets.empty:
        ax1.scatter(synack_packets['time_offset'], synack_packets['size'], 
                  s=120, marker='v', color='blue', label='SYN-ACK')
    
    if not fin_packets.empty:
        ax1.scatter(fin_packets['time_offset'], fin_packets['size'], 
                  s=120, marker='s', color='orange', label='FIN')
    
    if not rst_packets.empty:
        ax1.scatter(rst_packets['time_offset'], rst_packets['size'], 
                  s=120, marker='X', color='red', label='RST')
    
    # Add key time markers
    if stats.get('first_data_time') and stats.get('last_data_time'):
        data_start = stats['first_data_time'] - min_time
        data_end = stats['last_data_time'] - min_time
        ax1.axvline(x=data_start, color='green', linestyle='--', 
                   label='Data Transfer Start')
        ax1.axvline(x=data_end, color='red', linestyle='--', 
                   label='Data Transfer End')
        
        # Add annotation for data transfer duration
        duration = stats['last_data_time'] - stats['first_data_time']
        mid_point = data_start + (data_end - data_start) / 2
        ax1.text(mid_point, ax1.get_ylim()[1] * 0.9, 
               f'Data Transfer: {duration:.4f}s',
               horizontalalignment='center',
               bbox=dict(facecolor='white', alpha=0.8))
    
    ax1.set_xlabel('Time (seconds from start)')
    ax1.set_ylabel('Packet Size (bytes)')
    ax1.set_title('gRPC Traffic Timeline')
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper right')
    
    # Plot cumulative data transfer
    ax2 = plt.subplot(2, 1, 2)
    # Sort by time and filter out retransmissions for cumulative data
    sorted_df = df_clean.sort_values('time_offset')
    cumulative_data = sorted_df['size'].cumsum()
    
    ax2.plot(sorted_df['time_offset'], cumulative_data, '-', linewidth=2, label='Cumulative Data')
    
    # Add the route count estimation on a second y-axis
    if stats.get('estimated_routes') > 0:
        bytes_per_route = stats['total_data_bytes'] / stats['estimated_routes']
        ax3 = ax2.twinx()
        ax3.plot(sorted_df['time_offset'], cumulative_data / bytes_per_route, 
               '--', color='green', linewidth=1.5, label='Estimated Routes')
        ax3.set_ylabel('Estimated Routes')
        ax3.legend(loc='upper left')
    
    ax2.set_xlabel('Time (seconds from start)')
    ax2.set_ylabel('Cumulative Data (bytes)')
    ax2.set_title('Cumulative Data Transfer')
    ax2.grid(True, alpha=0.3)
    ax2.legend(loc='upper left')
    
    plt.tight_layout()
    
    # Save the plot if an output file is specified
    if output_file:
        plt.savefig(output_file)
        print(f"Timeline visualization saved to {output_file}")
    else:
        plt.show()

def main():
    parser = argparse.ArgumentParser(description='Analyze gRPC route exchange timing from pcap files')
    parser.add_argument('pcap_file', help='Path to the pcap file')
    parser.add_argument('-s', '--src', help='Filter by source IP address')
    parser.add_argument('-d', '--dst', help='Filter by destination IP address')
    parser.add_argument('-p', '--port', type=int, default=50051, help='gRPC port (default: 50051)')
    parser.add_argument('-o', '--output', help='Output file for timeline visualization')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('--scan', action='store_true', help='Scan the pcap file for protocols and ports')
    args = parser.parse_args()
    
    # Extract basic metadata
    metadata = extract_capture_metadata(args.pcap_file)
    print(f"Analyzing {args.pcap_file} ({metadata['packet_count']} packets, {metadata['duration']:.2f} seconds)")
    
    # Scan for protocols if requested
    if args.scan:
        print("\nScanning protocols and ports...")
        scan_results = scan_for_common_protocols(args.pcap_file)
        
        if 'error' not in scan_results:
            print("\nProtocols detected:")
            for proto, count in scan_results['protocols'].items():
                print(f"  {proto}: {count} packets")
            
            print("\nTop TCP ports:")
            for port, count in scan_results['top_tcp_ports']:
                service = get_well_known_port(port)
                service_str = f" ({service})" if service else ""
                print(f"  Port {port}{service_str}: {count} packets")
            
            print("\nTop IP pairs:")
            for pair, count in scan_results['top_ip_pairs']:
                print(f"  {pair}: {count} packets")
    
    # Analyze the gRPC traffic
    stats = analyze_grpc_traffic(args.pcap_file, args.src, args.dst, args.port)
    
    # Print the results
    print_stats(stats)
    
    # Create a visualization
    if stats and stats.get('packet_timeline'):
        plot_timeline(stats, args.output)

def get_well_known_port(port):
    """Return service name for well-known ports."""
    well_known = {
        20: 'FTP-data',
        21: 'FTP',
        22: 'SSH',
        23: 'Telnet',
        25: 'SMTP',
        53: 'DNS',
        80: 'HTTP',
        110: 'POP3',
        143: 'IMAP',
        179: 'BGP',
        443: 'HTTPS',
        3784: 'BFD',
        8080: 'HTTP-alt',
        8888: 'HTTP-alt',
        50051: 'gRPC'
    }
    return well_known.get(port)

if __name__ == "__main__":
    main()
