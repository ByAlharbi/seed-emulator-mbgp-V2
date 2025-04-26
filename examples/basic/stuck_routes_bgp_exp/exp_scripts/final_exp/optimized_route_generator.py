#!/usr/bin/env python3
import random
import ipaddress
import subprocess
import sys
import os
import time

def get_container_id(container_name):
    """Get docker container ID from container name"""
    try:
        container_id = subprocess.check_output(
            ["docker", "ps", "-qf", f"name={container_name}"]
        ).decode().strip()
    except subprocess.CalledProcessError:
        print(f"❌ Failed to find container: {container_name}")
        return None

    if not container_id:
        print(f"❌ Container named '{container_name}' not found.")
        return None
        
    return container_id

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

def generate_routes(output_file, via_ip, routes_needed, network_range_start):
    """
    Generate non-overlapping routes much faster
    
    Args:
        output_file: File to write the routes to
        via_ip: Next hop IP address
        routes_needed: Number of routes to generate
        network_range_start: Starting range for IP generation (to avoid overlap)
    
    Returns:
        set: Set of generated networks
    """
    start_time = time.time()
    networks = set()
    prefix = 24  # Using /24 networks
    
    with open(output_file, "w") as f:
        f.write("ipv4 table t_rw;\n")
        f.write("protocol static static_routes {\n")
        f.write("    ipv4 { table t_rw; import all; };\n")

        count = 0
        attempted = 0
        # Use different seed for each router to avoid overlaps
        random.seed(network_range_start)
        
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

        # Add pipe protocol to export to t_bgp
        f.write("protocol pipe {\n")
        f.write("    table t_rw;\n")
        f.write("    peer table t_bgp;\n")
        f.write("    import none;\n")
        f.write("    export all;\n")
        f.write("}\n")
    
    end_time = time.time()
    print(f"  ✓ Generated {count} routes in {end_time-start_time:.2f} seconds")
    return networks

def deploy_routes(container_id, output_file):
    """Deploy routes to the container"""
    if not container_id:
        return False
        
    # Copy to container
    print(f"  Copying {output_file} to container...")
    subprocess.run(["docker", "cp", output_file, f"{container_id}:/tmp/{output_file}"], check=True)

    # Append to bird.conf inside container
    print(f"  Appending routes to bird.conf...")
    append_cmd = f"cat /tmp/{output_file} >> /etc/bird/bird.conf"
    subprocess.run(["docker", "exec", container_id, "sh", "-c", append_cmd], check=True)
    
    return True

def main():
    start_time = time.time()
    
    # Config for Router 149
    r149_container = "as149r-router0-10.149.0.254"
    r149_via_ip = "10.149.0.150"
    r149_routes = 100
    r149_output = "static_routes_149.conf"
    
    # Config for Router 150
    r150_container = "as150r-router0-10.150.0.254" 
    r150_via_ip = "10.100.0.150"
    r150_routes = 100000
    r150_output = "static_routes_150.conf"
    
    # Get container IDs
    print(f"Looking up container IDs...")
    r149_id = get_container_id(r149_container)
    r150_id = get_container_id(r150_container)
    
    if not r149_id or not r150_id:
        print("❌ Cannot continue without both containers.")
        sys.exit(1)
    
    # Router 149: Generate routes using seed range 149000
    print(f"Generating {r149_routes} routes for Router 149...")
    r149_networks = generate_routes(r149_output, r149_via_ip, r149_routes, 149000)
    
    # Router 150: Generate routes using seed range 150000
    print(f"Generating {r150_routes} routes for Router 150...")
    r150_networks = generate_routes(r150_output, r150_via_ip, r150_routes, 150000)
    
    # Verify no overlap - convert to set of strings if needed
    if isinstance(next(iter(r149_networks), None), str) and isinstance(next(iter(r150_networks), None), str):
        overlap = r149_networks.intersection(r150_networks)
    else:
        overlap = set()
        
    if overlap:
        print(f"⚠️ WARNING: Found {len(overlap)} overlapping networks between Router 149 and 150!")
        print("Example overlaps:")
        for net in list(overlap)[:5]:
            print(f"  - {net}")
    else:
        print("✅ No overlapping networks between Router 149 and 150")
    
    # Deploy routes to containers
    print(f"Deploying routes to Router 149 ({r149_container})...")
    if deploy_routes(r149_id, r149_output):
        print(f"✅ Routes deployed to Router 149.")
    else:
        print(f"❌ Failed to deploy routes to Router 149.")
    
    print(f"Deploying routes to Router 150 ({r150_container})...")
    if deploy_routes(r150_id, r150_output):
        print(f"✅ Routes deployed to Router 150.")
    else:
        print(f"❌ Failed to deploy routes to Router 150.")
    
    # Cleanup
    os.remove(r149_output)
    os.remove(r150_output)
    
    total_time = time.time() - start_time
    print(f"✅ Route generation and deployment completed in {total_time:.2f} seconds.")

if __name__ == "__main__":
    main()
