#!/usr/bin/env python3
# encoding: utf-8
# Micro experiments for all MBGP deployment percentages
# 0% (pure BGP), 20%, 40%, 60%, 100% (pure MBGP)

from seedemu.layers import Base, Routing, Ebgp, Mbgp, PeerRelationship
from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator
from seedemu.utilities import Makers
import os, sys, subprocess

def run(dumpfile=None, mbgp_percentage=0): 
    ###############################################################################
    # Set the platform information
    if dumpfile is None:
        script_name = os.path.basename(__file__)

        if len(sys.argv) == 1:
            platform = Platform.AMD64
        elif len(sys.argv) == 2:
            if sys.argv[1].lower() == 'amd':
                platform = Platform.AMD64
            elif sys.argv[1].lower() == 'arm':
                platform = Platform.ARM64
            else:
                print(f"Usage:  {script_name} amd|arm")
                sys.exit(1)
        else:
            print(f"Usage:  {script_name} amd|arm")
            sys.exit(1)

    emu   = Emulator()
    ebgp  = Ebgp()
    mbgp  = Mbgp() if mbgp_percentage > 0 else None
    base  = Base()
    
    ###############################################################################
    # Create 3 internet exchanges for path diversity
    ix100 = base.createInternetExchange(100)
    ix101 = base.createInternetExchange(101)
    ix102 = base.createInternetExchange(102)
    
    ix100.getPeeringLan().setDisplayName('IX-Core')
    ix101.getPeeringLan().setDisplayName('IX-East')
    ix102.getPeeringLan().setDisplayName('IX-West')
    
    ###############################################################################
    # Create Transit ASes
    
    # AS2 - Main transit (connects all IXes)
    as2 = base.createAutonomousSystem(2)
    as2.createNetwork('net0')
    as2.createRouter('router0').joinNetwork('net0').joinNetwork('ix100').joinNetwork('ix101').joinNetwork('ix102')
    
    # AS3 - Secondary transit (IX100 and IX101)
    as3 = base.createAutonomousSystem(3)
    as3.createNetwork('net0')
    as3.createRouter('router0').joinNetwork('net0').joinNetwork('ix100').joinNetwork('ix101')
    
    # AS4 - Tertiary transit (IX100 and IX102)
    as4 = base.createAutonomousSystem(4)
    as4.createNetwork('net0')
    as4.createRouter('router0').joinNetwork('net0').joinNetwork('ix100').joinNetwork('ix102')
    
    ###############################################################################
    # Create stub ASes based on MBGP percentage
    # Total: 6 stub ASes (AS150, AS151, AS152, AS160, AS161, AS162)
    
    if mbgp_percentage == 0:
        # 0% - All BGP
        Makers.makeStubAsWithHosts(emu, base, 150, 100, 1)
        Makers.makeStubAsWithHosts(emu, base, 151, 100, 1)
        Makers.makeStubAsWithHosts(emu, base, 152, 101, 1)
        Makers.makeStubAsWithHosts(emu, base, 160, 102, 1)
        Makers.makeStubAsWithHosts(emu, base, 161, 101, 1)
        Makers.makeStubAsWithHosts(emu, base, 162, 102, 1)
        
    elif mbgp_percentage == 20:
        # 20% - 1-2 ASes use MBGP (AS150, AS160)
        Makers.makeStubAsWithHostsMbgp(emu, base, 150, 100, 1)
        Makers.makeStubAsWithHosts(emu, base, 151, 100, 1)
        Makers.makeStubAsWithHosts(emu, base, 152, 101, 1)
        Makers.makeStubAsWithHostsMbgp(emu, base, 160, 102, 1)
        Makers.makeStubAsWithHosts(emu, base, 161, 101, 1)
        Makers.makeStubAsWithHosts(emu, base, 162, 102, 1)
        
    elif mbgp_percentage == 40:
        # 40% - 2-3 ASes use MBGP (AS150, AS152, AS160)
        Makers.makeStubAsWithHostsMbgp(emu, base, 150, 100, 1)
        Makers.makeStubAsWithHosts(emu, base, 151, 100, 1)
        Makers.makeStubAsWithHostsMbgp(emu, base, 152, 101, 1)
        Makers.makeStubAsWithHostsMbgp(emu, base, 160, 102, 1)
        Makers.makeStubAsWithHosts(emu, base, 161, 101, 1)
        Makers.makeStubAsWithHosts(emu, base, 162, 102, 1)
        
    elif mbgp_percentage == 60:
        # 60% - 4 ASes use MBGP (AS150, AS151, AS152, AS160)
        Makers.makeStubAsWithHostsMbgp(emu, base, 150, 100, 1)
        Makers.makeStubAsWithHostsMbgp(emu, base, 151, 100, 1)
        Makers.makeStubAsWithHostsMbgp(emu, base, 152, 101, 1)
        Makers.makeStubAsWithHostsMbgp(emu, base, 160, 102, 1)
        Makers.makeStubAsWithHosts(emu, base, 161, 101, 1)
        Makers.makeStubAsWithHosts(emu, base, 162, 102, 1)
        
    elif mbgp_percentage == 90:
        # 90% - 5 ASes use MBGP (only AS162 remains BGP)
        Makers.makeStubAsWithHostsMbgp(emu, base, 150, 100, 1)
        Makers.makeStubAsWithHostsMbgp(emu, base, 151, 100, 1)
        Makers.makeStubAsWithHostsMbgp(emu, base, 152, 101, 1)
        Makers.makeStubAsWithHostsMbgp(emu, base, 160, 102, 1)
        Makers.makeStubAsWithHostsMbgp(emu, base, 161, 101, 1)
        Makers.makeStubAsWithHosts(emu, base, 162, 102, 1)
        
    elif mbgp_percentage == 100:
        # 100% - All MBGP
        Makers.makeStubAsWithHostsMbgp(emu, base, 150, 100, 1)
        Makers.makeStubAsWithHostsMbgp(emu, base, 151, 100, 1)
        Makers.makeStubAsWithHostsMbgp(emu, base, 152, 101, 1)
        Makers.makeStubAsWithHostsMbgp(emu, base, 160, 102, 1)
        Makers.makeStubAsWithHostsMbgp(emu, base, 161, 101, 1)
        Makers.makeStubAsWithHostsMbgp(emu, base, 162, 102, 1)
    
    ###############################################################################
    # Route server peering configuration based on percentage
    
    if mbgp_percentage == 0:
        # All BGP route servers
        ebgp.addRsPeers(100, [2, 3, 4])
        ebgp.addRsPeers(101, [2, 3])
        
    elif mbgp_percentage == 20:
        # Mostly BGP route servers
        ebgp.addRsPeers(100, [2, 3, 4])
        ebgp.addRsPeers(101, [2, 3])
        
    elif mbgp_percentage == 40:
        # Mixed route servers
        mbgp.addRsPeers(100, [2, 3, 4])  # Core IX uses MBGP
        ebgp.addRsPeers(101, [2, 3])     # East IX uses BGP
        
    elif mbgp_percentage == 60:
        # Mostly MBGP route servers
        mbgp.addRsPeers(100, [2, 3, 4])
        mbgp.addRsPeers(101, [2, 3])
        
    elif mbgp_percentage == 90:
        # Almost all MBGP route servers
        mbgp.addRsPeers(100, [2, 3, 4])
        mbgp.addRsPeers(101, [2, 3])
        
    elif mbgp_percentage == 100:
        # All MBGP route servers
        mbgp.addRsPeers(100, [2, 3, 4])
        mbgp.addRsPeers(101, [2, 3])
    
    ###############################################################################
    # Private peering configuration based on percentage
    
    if mbgp_percentage == 0:
        # All BGP peerings
        ebgp.addPrivatePeerings(100, [2], [150, 151], PeerRelationship.Unfiltered)
        ebgp.addPrivatePeerings(100, [3], [150], PeerRelationship.Unfiltered)
        ebgp.addPrivatePeerings(100, [4], [151], PeerRelationship.Unfiltered)
        ebgp.addPrivatePeerings(101, [2], [152], PeerRelationship.Unfiltered)
        ebgp.addPrivatePeerings(101, [3], [152, 161], PeerRelationship.Unfiltered)
        ebgp.addPrivatePeerings(102, [2], [160, 162], PeerRelationship.Unfiltered)
        ebgp.addPrivatePeerings(102, [4], [160, 162], PeerRelationship.Unfiltered)
        
    elif mbgp_percentage == 20:
        # 20% MBGP - AS150 and AS160 use MBGP
        mbgp.addPrivatePeerings(100, [2], [150], PeerRelationship.Unfiltered)
        ebgp.addPrivatePeerings(100, [2], [151], PeerRelationship.Unfiltered)
        mbgp.addPrivatePeerings(100, [3], [150], PeerRelationship.Unfiltered)
        ebgp.addPrivatePeerings(100, [4], [151], PeerRelationship.Unfiltered)
        ebgp.addPrivatePeerings(101, [2], [152], PeerRelationship.Unfiltered)
        ebgp.addPrivatePeerings(101, [3], [152, 161], PeerRelationship.Unfiltered)
        mbgp.addPrivatePeerings(102, [2], [160], PeerRelationship.Unfiltered)
        ebgp.addPrivatePeerings(102, [2], [162], PeerRelationship.Unfiltered)
        mbgp.addPrivatePeerings(102, [4], [160], PeerRelationship.Unfiltered)
        ebgp.addPrivatePeerings(102, [4], [162], PeerRelationship.Unfiltered)
        
    elif mbgp_percentage == 40:
        # 40% MBGP - AS150, AS152, AS160 use MBGP
        mbgp.addPrivatePeerings(100, [2], [150], PeerRelationship.Unfiltered)
        ebgp.addPrivatePeerings(100, [2], [151], PeerRelationship.Unfiltered)
        mbgp.addPrivatePeerings(100, [3], [150], PeerRelationship.Unfiltered)
        ebgp.addPrivatePeerings(100, [4], [151], PeerRelationship.Unfiltered)
        mbgp.addPrivatePeerings(101, [2], [152], PeerRelationship.Unfiltered)
        mbgp.addPrivatePeerings(101, [3], [152], PeerRelationship.Unfiltered)
        ebgp.addPrivatePeerings(101, [3], [161], PeerRelationship.Unfiltered)
        mbgp.addPrivatePeerings(102, [2], [160], PeerRelationship.Unfiltered)
        ebgp.addPrivatePeerings(102, [2], [162], PeerRelationship.Unfiltered)
        mbgp.addPrivatePeerings(102, [4], [160], PeerRelationship.Unfiltered)
        ebgp.addPrivatePeerings(102, [4], [162], PeerRelationship.Unfiltered)
        
    elif mbgp_percentage == 60:
        # 60% MBGP - AS150, AS151, AS152, AS160 use MBGP
        mbgp.addPrivatePeerings(100, [2], [150, 151], PeerRelationship.Unfiltered)
        mbgp.addPrivatePeerings(100, [3], [150], PeerRelationship.Unfiltered)
        mbgp.addPrivatePeerings(100, [4], [151], PeerRelationship.Unfiltered)
        mbgp.addPrivatePeerings(101, [2], [152], PeerRelationship.Unfiltered)
        mbgp.addPrivatePeerings(101, [3], [152], PeerRelationship.Unfiltered)
        ebgp.addPrivatePeerings(101, [3], [161], PeerRelationship.Unfiltered)
        mbgp.addPrivatePeerings(102, [2], [160], PeerRelationship.Unfiltered)
        ebgp.addPrivatePeerings(102, [2], [162], PeerRelationship.Unfiltered)
        mbgp.addPrivatePeerings(102, [4], [160], PeerRelationship.Unfiltered)
        ebgp.addPrivatePeerings(102, [4], [162], PeerRelationship.Unfiltered)
        
    elif mbgp_percentage == 90:
        # 90% MBGP - Only AS162 uses BGP
        mbgp.addPrivatePeerings(100, [2], [150, 151], PeerRelationship.Unfiltered)
        mbgp.addPrivatePeerings(100, [3], [150], PeerRelationship.Unfiltered)
        mbgp.addPrivatePeerings(100, [4], [151], PeerRelationship.Unfiltered)
        mbgp.addPrivatePeerings(101, [2], [152], PeerRelationship.Unfiltered)
        mbgp.addPrivatePeerings(101, [3], [152, 161], PeerRelationship.Unfiltered)
        mbgp.addPrivatePeerings(102, [2], [160], PeerRelationship.Unfiltered)
        ebgp.addPrivatePeerings(102, [2], [162], PeerRelationship.Unfiltered)
        mbgp.addPrivatePeerings(102, [4], [160], PeerRelationship.Unfiltered)
        ebgp.addPrivatePeerings(102, [4], [162], PeerRelationship.Unfiltered)
        
    elif mbgp_percentage == 100:
        # All MBGP peerings
        mbgp.addPrivatePeerings(100, [2], [150, 151], PeerRelationship.Unfiltered)
        mbgp.addPrivatePeerings(100, [3], [150], PeerRelationship.Unfiltered)
        mbgp.addPrivatePeerings(100, [4], [151], PeerRelationship.Unfiltered)
        mbgp.addPrivatePeerings(101, [2], [152], PeerRelationship.Unfiltered)
        mbgp.addPrivatePeerings(101, [3], [152, 161], PeerRelationship.Unfiltered)
        mbgp.addPrivatePeerings(102, [2], [160, 162], PeerRelationship.Unfiltered)
        mbgp.addPrivatePeerings(102, [4], [160, 162], PeerRelationship.Unfiltered)
    
    # Inter-transit peering
    if mbgp_percentage == 100:
        # Use MBGP for 100% deployment
        mbgp.addPrivatePeerings(100, [3], [4], PeerRelationship.Unfiltered)
    elif mbgp_percentage == 90:
        # Use MBGP for 90% deployment too
        mbgp.addPrivatePeerings(100, [3], [4], PeerRelationship.Unfiltered)
    else:
        # Use BGP for all other scenarios
        ebgp.addPrivatePeerings(100, [3], [4], PeerRelationship.Unfiltered)
    
    ###############################################################################
    # Add layers to emulator
    emu.addLayer(base)
    emu.addLayer(Routing())
    emu.addLayer(ebgp)
    if mbgp_percentage > 0:
        emu.addLayer(mbgp)

    if dumpfile is not None: 
        emu.dump(dumpfile)
    else: 
        output_dir = f'./output_micro_{mbgp_percentage}_mbgp'
        emu.render()
        emu.compile(Docker(platform=platform), output_dir, override=True)
        # Always copy bird directory for consistency
        subprocess.run(["./copy_bird_dir.sh", output_dir], check=True)
        
        print(f"\n{'='*60}")
        print(f"Micro experiment with {mbgp_percentage}% MBGP deployment completed!")
        print(f"Output directory: {output_dir}")
        print(f"{'='*60}\n")

if __name__ == "__main__":
    # Generate all scenarios
    scenarios = [0, 20, 40, 60, 90, 100]
    
    print("Choose which scenario to run:")
    print("1. Single scenario")
    print("2. All scenarios")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        print("\nAvailable percentages: 0, 20, 40, 60, 90, 100")
        percentage = int(input("Enter MBGP percentage: "))
        if percentage in scenarios:
            run(mbgp_percentage=percentage)
        else:
            print(f"Invalid percentage. Choose from: {scenarios}")
    elif choice == "2":
        print("\nGenerating all scenarios...")
        for percentage in scenarios:
            print(f"\n--- Generating {percentage}% MBGP scenario ---")
            run(mbgp_percentage=percentage)
        print("\nAll scenarios generated successfully!")
    else:
        print("Invalid choice. Running default 40% scenario.")
        run(mbgp_percentage=40)
