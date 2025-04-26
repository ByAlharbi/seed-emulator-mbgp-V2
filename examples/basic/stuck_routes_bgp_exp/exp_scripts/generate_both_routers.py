#!/usr/bin/env python3
import random
import ipaddress
import subprocess
import sys
import os

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

def generate_routes(output_file, via_ip, routes_needed, network_range_start):
    """
    Generate non-overlapping routes
    
    Args:
        output_file: File to write the routes to
        via_ip: Next hop IP address
        routes_needed: Number of routes to generate
        network_range_start: Starting range for IP generation (to avoid overlap)
    
    Returns:
        set: Set of generated networks
    """
    networks = set()
    
    with open(output_file, "w") as f:
        f.write("ipv4 table t_rw;\n")
        f.write("protocol static static_routes {\n")
        f.write("    ipv4 { table t_rw; import all; };\n")

        count = 0
        seed_base = network_range_start
        
        while count < routes_needed:
            # Use different seed range for each router
            random.seed(count + seed_base)
            ip = ipaddress.IPv4Address(random.getrandbits(32))

            # Skip invalid/unroutable/reserved IPs
            if (
                ip.is_private               # 10.0.0.0/8, 192.168.0.0/16, etc.
                or ip.is_loopback           # 127.0.0.0/8
                or ip.is_link_local         # 169.254.0.0/16
                or ip.is_multicast          # 224.0.0.0/4 (incl. 232.x.x.x)
                or ip.is_reserved           # 240.0.0.0/4
                or ip.is_unspecified        # 0.0.0.0
                or ip in ipaddress.IPv4Network("100.64.0.0/10")  # CGNAT
            ):
                continue

            prefix = 24  # or 16/18/20/22 etc. if you want variety
            network = ipaddress.IPv4Network(f"{ip}/{prefix}", strict=False)

            if network in networks:
                continue

            networks.add(network)
            f.write(f"    route {network} via {via_ip};\n")
            count += 1

        f.write("}\n")

        # Add pipe protocol to export to t_bgp
        f.write("protocol pipe {\n")
        f.write("    table t_rw;\n")
        f.write("    peer table t_bgp;\n")
        f.write("    import none;\n")
        f.write("    export all;\n")
        f.write("}\n")
    
    return networks

def deploy_routes(container_id, output_file):
    """Deploy routes to the container"""
    if not container_id:
        return False
        
    # Copy to container
    subprocess.run(["docker", "cp", output_file, f"{container_id}:/tmp/{output_file}"], check=True)

    # Append to bird.conf inside container
    append_cmd = f"cat /tmp/{output_file} >> /etc/bird/bird.conf"
    subprocess.run(["docker", "exec", container_id, "sh", "-c", append_cmd], check=True)
    
    return True

def main():
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
    r149_id = get_container_id(r149_container)
    r150_id = get_container_id(r150_container)
    
    if not r149_id or not r150_id:
        print("❌ Cannot continue without both containers.")
        sys.exit(1)
    
    # Router 149: Generate routes using seed range 149000-149999
    print(f"Generating {r149_routes} routes for Router 149...")
    r149_networks = generate_routes(r149_output, r149_via_ip, r149_routes, 149000)
    print(f"✅ Generated {len(r149_networks)} routes in {r149_output}")
    
    # Router 150: Generate routes using seed range 150000+
    print(f"Generating {r150_routes} routes for Router 150...")
    r150_networks = generate_routes(r150_output, r150_via_ip, r150_routes, 150000)
    print(f"✅ Generated {len(r150_networks)} routes in {r150_output}")
    
    # Verify no overlap
    overlap = r149_networks.intersection(r150_networks)
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
    
    print("✅ Route generation and deployment completed.")

if __name__ == "__main__":
    main()
