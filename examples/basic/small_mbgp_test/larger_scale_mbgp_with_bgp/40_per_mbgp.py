#!/usr/bin/env python3
# encoding: utf-8
# 40% MBGP deployment - approximately 40% of connections use MBGP

from seedemu.layers import Base, Routing, Ebgp, Mbgp, PeerRelationship
from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator
from seedemu.utilities import Makers
import os, sys, subprocess

def run(dumpfile=None, hosts_per_as=2): 
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
    mbgp  = Mbgp()  # Add MBGP layer
    base  = Base()
    
    ###############################################################################
    # Create internet exchanges
    ix100 = base.createInternetExchange(100)
    ix101 = base.createInternetExchange(101)
    ix102 = base.createInternetExchange(102)
    ix103 = base.createInternetExchange(103)
    ix104 = base.createInternetExchange(104)
    ix105 = base.createInternetExchange(105)
    
    # Customize names (for visualization purpose)
    ix100.getPeeringLan().setDisplayName('NYC-100')
    ix101.getPeeringLan().setDisplayName('San Jose-101')
    ix102.getPeeringLan().setDisplayName('Chicago-102')
    ix103.getPeeringLan().setDisplayName('Miami-103')
    ix104.getPeeringLan().setDisplayName('Boston-104')
    ix105.getPeeringLan().setDisplayName('Houston-105')
    
    
    ###############################################################################
    # Create Transit Autonomous Systems 
    # Modified to have only one router per AS (no internal routers)
    
    ## Tier 1 ASes - Modified to connect to multiple IXes with one router
    # AS2 connects to IX100, IX101, IX102, IX105
    as2 = base.createAutonomousSystem(2)
    as2.createNetwork('net0')
    as2.createRouter('router0').joinNetwork('net0').joinNetwork('ix100').joinNetwork('ix101').joinNetwork('ix102').joinNetwork('ix105')
    
    # AS3 connects to IX100, IX103, IX104, IX105
    as3 = base.createAutonomousSystem(3)
    as3.createNetwork('net0')
    as3.createRouter('router0').joinNetwork('net0').joinNetwork('ix100').joinNetwork('ix103').joinNetwork('ix104').joinNetwork('ix105')
    
    # AS4 connects to IX100, IX102, IX104
    as4 = base.createAutonomousSystem(4)
    as4.createNetwork('net0')
    as4.createRouter('router0').joinNetwork('net0').joinNetwork('ix100').joinNetwork('ix102').joinNetwork('ix104')
    
    ## Tier 2 ASes - Each with one router connecting to multiple IXes
    # AS11 connects to IX102, IX105
    as11 = base.createAutonomousSystem(11)
    as11.createNetwork('net0')
    as11.createRouter('router0').joinNetwork('net0').joinNetwork('ix102').joinNetwork('ix105')
    
    # AS12 connects to IX101, IX104
    as12 = base.createAutonomousSystem(12)
    as12.createNetwork('net0')
    as12.createRouter('router0').joinNetwork('net0').joinNetwork('ix101').joinNetwork('ix104')
    
    
    ###############################################################################
    # Create single-homed stub ASes
    # For 40% MBGP: AS150, AS151, AS152, AS160, AS161 use MBGP (5 out of 12 ≈ 42%)
    
    # MBGP stub ASes
    Makers.makeStubAsWithHostsMbgp(emu, base, 150, 100, hosts_per_as)
    Makers.makeStubAsWithHostsMbgp(emu, base, 151, 100, hosts_per_as)
    Makers.makeStubAsWithHostsMbgp(emu, base, 152, 101, hosts_per_as)
    Makers.makeStubAsWithHostsMbgp(emu, base, 160, 103, hosts_per_as)
    Makers.makeStubAsWithHostsMbgp(emu, base, 161, 103, hosts_per_as)
    
    # Regular BGP stub ASes
    Makers.makeStubAsWithHosts(emu, base, 153, 101, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 154, 102, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 162, 103, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 163, 104, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 164, 104, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 170, 105, hosts_per_as)
    Makers.makeStubAsWithHosts(emu, base, 171, 105, hosts_per_as)
    
    # An example to show how to add a host with customized IP address
    as154 = base.getAutonomousSystem(154)
    as154.createHost('host_new').joinNetwork('net0', address = '10.154.0.129')
    
    ###############################################################################
    # RS Peering - Mix of BGP and MBGP
    ebgp.addRsPeers(100, [2, 3, 4])
    mbgp.addRsPeers(102, [2, 4])  # MBGP RS
    ebgp.addRsPeers(104, [3, 4])
    mbgp.addRsPeers(105, [2, 3])  # MBGP RS
    
    # Private peering - Mix of BGP and MBGP (40% MBGP)
    # MBGP peerings
    mbgp.addPrivatePeerings(100, [2], [150, 151], PeerRelationship.Unfiltered)
    mbgp.addPrivatePeerings(100, [3], [150], PeerRelationship.Unfiltered)
    
    mbgp.addPrivatePeerings(101, [2], [12], PeerRelationship.Unfiltered)
    mbgp.addPrivatePeerings(101, [12], [152], PeerRelationship.Unfiltered)
    
    mbgp.addPrivatePeerings(103, [3], [160, 161], PeerRelationship.Unfiltered)
    
    # BGP peerings (60%)
    ebgp.addPrivatePeerings(101, [12], [153], PeerRelationship.Unfiltered)
    
    ebgp.addPrivatePeerings(102, [2, 4], [11, 154], PeerRelationship.Unfiltered)
    ebgp.addPrivatePeerings(102, [11], [154], PeerRelationship.Unfiltered)
    
    ebgp.addPrivatePeerings(103, [3], [162], PeerRelationship.Unfiltered)
    
    ebgp.addPrivatePeerings(104, [3, 4], [12], PeerRelationship.Unfiltered)
    ebgp.addPrivatePeerings(104, [4], [163], PeerRelationship.Unfiltered)
    ebgp.addPrivatePeerings(104, [12], [164], PeerRelationship.Unfiltered)
    
    ebgp.addPrivatePeerings(105, [3], [11, 170], PeerRelationship.Unfiltered)
    ebgp.addPrivatePeerings(105, [11], [171], PeerRelationship.Unfiltered)
    
    
    ###############################################################################
    # Add layers to the emulator
    emu.addLayer(base)
    emu.addLayer(Routing())
    emu.addLayer(ebgp)
    emu.addLayer(mbgp)  # Add MBGP layer

    if dumpfile is not None: 
        # Save it to a file, so it can be used by other emulators
        emu.dump(dumpfile)
    else: 
        emu.render()
        emu.compile(Docker(platform=platform), './output_40_mbgp', override=True)
        # Only copy bird directory if using MBGP
        subprocess.run(["./copy_bird_dir.sh", "./output_40_mbgp"], check=True)

if __name__ == "__main__":
    run()
