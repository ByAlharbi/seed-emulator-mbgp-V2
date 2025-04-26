#!/usr/bin/env python3
import random
import ipaddress
import sys
import os
import time

def is_valid_ip(ip):
    """Fast check if an IP is valid for routing"""
    # Check private ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16)
    first_octet = ip >> 24
    if first_octet == 10:
        return False
    if first_octet == 172 and (ip >> 16) & 0xF0 == 0x10:
        return False
    if first_octet == 192 and (ip >> 16) & 0xFF == 0xA8:
        return False
    
    # Check loopback (127.0.0.0/8)
    if first_octet == 127:
        return False
    
    # Check link local (169.254.0.0/16)
    if first_octet == 169 and (ip >> 16) & 0xFF == 254:
        return False
    
    # Check multicast (224.0.0.0/4)
    if (first_octet & 0xF0) == 0xE0:
        return False
    
    # Check reserved (240.0.0.0/4)
    if (first_octet & 0xF0) == 0xF0:
        return False
    
    # Check unspecified (0.0.0.0)
    if ip == 0:
        return False
    
    # Check CGNAT (100.64.0.0/10)
    if first_octet == 100 and (ip >> 16) & 0xC0 == 0x40:
        return False
    
    return True

def int_to_network_str(ip_int, prefix):
    """Convert integer to proper network address string with proper masking"""
    # Apply network mask to ensure we have a network address, not a host address
    # For a /24 prefix, we need to zero out the last octet
    mask = ~((1 << (32 - prefix)) - 1)
    network_int = ip_int & mask
    
    # Convert to string format
    return f"{(network_int >> 24) & 0xFF}.{(network_int >> 16) & 0xFF}.{(network_int >> 8) & 0xFF}.{network_int & 0xFF}/{prefix}"

def generate_routes(output_file, via_ip, routes_needed, seed_value):
    """
    Generate non-overlapping routes and save to file
    
    Args:
        output_file: File to write the routes to
        via_ip: Next hop IP address
        routes_needed: Number of routes to generate
        seed_value: Seed for random number generator
    
    Returns:
        set: Set of generated networks
    """
    start_time = time.time()
    networks = set()
    prefix = 24  # Using /24 networks
    
    with open(output_file, "w") as f:
        f.write("protocol static static_routes {\n")
        f.write("    ipv4 { import all; };\n")

        count = 0
        attempted = 0
        # Use seed for reproducibility but with new value
        random.seed(seed_value)
        
        # Generate a pool of random numbers upfront
        random_pool = [random.getrandbits(32) for _ in range(min(routes_needed * 2, 1000000))]
        pool_index = 0
        
        # Progress reporting variables
        progress_interval = max(1, routes_needed // 10)
        last_report = 0
        
        while count < routes_needed:
            # Get a random IP from our pool
            if pool_index >= len(random_pool):
                # Regenerate pool if needed
                random_pool = [random.getrandbits(32) for _ in range(min(routes_needed * 2, 1000000))]
                pool_index = 0
            
            ip_int = random_pool[pool_index]
            pool_index += 1
            attempted += 1
            
            # Fast validity check
            if not is_valid_ip(ip_int):
                continue
            
            # Convert to proper network address
            network_str = int_to_network_str(ip_int, prefix)
            
            # Add to our set - this automatically checks for duplicates
            if network_str in networks:
                continue
                
            networks.add(network_str)
            f.write(f"    route {network_str} via {via_ip};\n")
            count += 1
            
            # Print progress every 10%
            if count >= last_report + progress_interval:
                elapsed = time.time() - start_time
                print(f"  Generated {count}/{routes_needed} routes ({count/routes_needed*100:.1f}%) - {count/max(1, elapsed):.1f} routes/sec")
                last_report = count

        f.write("}\n")

    
    end_time = time.time()
    print(f"  ✓ Generated {count} routes in {end_time-start_time:.2f} seconds")
    return networks

def main():
    start_time = time.time()
    
    # Config for Router 149
    r149_via_ip = "10.149.0.150"
    r149_routes = 0
    r149_output = "route_149_static_routes.conf"
    
    # Config for Router 150
    r150_via_ip = "10.100.0.150"
    r150_routes = 5500
    r150_output = "route_150_static_routes.conf"
    
    # Use completely different seed values
    r149_seed = 987654
    r150_seed = 123459
    
    # Router 149: Generate routes using new seed
    print(f"Generating {r149_routes} routes for Router 149...")
    r149_networks = generate_routes(r149_output, r149_via_ip, r149_routes, r149_seed)
    
    # Router 150: Generate routes using new seed
    print(f"Generating {r150_routes} routes for Router 150...")
    r150_networks = generate_routes(r150_output, r150_via_ip, r150_routes, r150_seed)
    
    # Verify no overlap
    overlap = r149_networks.intersection(r150_networks)
    if overlap:
        print(f"⚠️ WARNING: Found {len(overlap)} overlapping networks between Router 149 and 150!")
        print("Example overlaps:")
        for net in list(overlap)[:5]:
            print(f"  - {net}")
    else:
        print("✅ No overlapping networks between Router 149 and 150")
    
    total_time = time.time() - start_time
    print(f"✅ Route generation completed in {total_time:.2f} seconds.")
    print(f"Output files created: {r149_output} and {r150_output}")

if __name__ == "__main__":
    main()
