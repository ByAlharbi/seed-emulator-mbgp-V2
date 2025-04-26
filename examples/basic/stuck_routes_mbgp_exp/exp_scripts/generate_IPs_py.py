#!/usr/bin/env python3
import random
import ipaddress
import subprocess
import sys
import os

# === Config ===
container_name = "as150r-router0-10.150.0.254"
via_ip = "10.100.0.150"
routes_needed = 100000
output_file = "static_routes.conf"

# === Step 1: Get container ID ===
try:
    container_id = subprocess.check_output(
        ["docker", "ps", "-qf", f"name={container_name}"]
    ).decode().strip()
except subprocess.CalledProcessError:
    print(f"❌ Failed to find container: {container_name}")
    sys.exit(1)

if not container_id:
    print(f"❌ Container named '{container_name}' not found.")
    sys.exit(1)

# === Step 2: Generate valid static routes ===
networks = set()

with open(output_file, "w") as f:
    f.write("ipv4 table t_rw;\n")
    f.write("protocol static static_routes {\n")
    f.write("    ipv4 { table t_rw; import all; };\n")

    count = 0
    while count < routes_needed:
        ip = ipaddress.IPv4Address(random.getrandbits(32))

        # === Skip invalid/unroutable/reserved IPs ===
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

    # === Add pipe protocol to export to t_bgp ===
    f.write("protocol pipe {\n")
    f.write("    table t_rw;\n")
    f.write("    peer table t_bgp;\n")
    f.write("    import none;\n")
    f.write("    export all;\n")
    f.write("}\n")

print(f"✅ Generated {routes_needed} routes in {output_file}")

# === Step 3: Copy to container ===
subprocess.run(["docker", "cp", output_file, f"{container_id}:/tmp/{output_file}"], check=True)

# === Step 4: Append to bird.conf inside container ===
append_cmd = f"cat /tmp/{output_file} >> /etc/bird/bird.conf"
subprocess.run(["docker", "exec", container_id, "sh", "-c", append_cmd], check=True)

# Optional: Reload BIRD
# subprocess.run(["docker", "exec", container_id, "birdc", "configure"])

# === Cleanup ===
os.remove(output_file)

print(f"✅ Routes appended to bird.conf inside container '{container_name}'.")
