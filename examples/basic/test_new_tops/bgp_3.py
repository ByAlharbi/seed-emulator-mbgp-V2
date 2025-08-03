#!/usr/bin/env python3
# encoding: utf-8

from seedemu.layers import Base, Routing, Ebgp, Ibgp, Ospf, PeerRelationship
from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator
import sys, os

def run(dumpfile = None):
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
    
    # Initialize the emulator and layers
    emu     = Emulator()
    base    = Base()
    routing = Routing()
    ebgp    = Ebgp()
    ibgp    = Ibgp()
    ospf    = Ospf()
    
    ###############################################################################
    # Create Internet Exchanges
    base.createInternetExchange(101)
    base.createInternetExchange(102)
    
    ###############################################################################
    # Create AS-153 (Stub AS 1)
    as153 = base.createAutonomousSystem(153)
    
    # Simple stub AS with one network
    as153.createNetwork('net0')
    as153.createRouter('router0').joinNetwork('net0').joinNetwork('ix101')
    as153.createHost('host0').joinNetwork('net0')
    as153.createHost('host1').joinNetwork('net0')
    
    ###############################################################################
    # Create AS-154 (Transit AS with iBGP)
    as154 = base.createAutonomousSystem(154)
    
    # Create internal networks for the transit AS
    as154.createNetwork('net0')
    as154.createNetwork('net1')
    as154.createNetwork('net2')
    
    # Create edge routers and internal router
    # r1 connects to IX101
    as154.createRouter('r1').joinNetwork('net0').joinNetwork('ix101')
    # r2 is internal router
    as154.createRouter('r2').joinNetwork('net0').joinNetwork('net1')
    # r3 connects to IX102
    as154.createRouter('r3').joinNetwork('net1').joinNetwork('net2').joinNetwork('ix102')
    
    # Add a host in the transit AS (optional)
    as154.createHost('host0').joinNetwork('net2')
    
    ###############################################################################
    # Create AS-155 (Stub AS 2)
    as155 = base.createAutonomousSystem(155)
    
    # Simple stub AS with one network
    as155.createNetwork('net0')
    as155.createRouter('router0').joinNetwork('net0').joinNetwork('ix102')
    as155.createHost('host0').joinNetwork('net0')
    as155.createHost('host1').joinNetwork('net0')
    
    ###############################################################################
    # Set up BGP peering
    # AS-154 (transit) provides service to AS-153 and AS-155
    ebgp.addPrivatePeering(101, 154, 153, abRelationship = PeerRelationship.Provider)
    ebgp.addPrivatePeering(102, 154, 155, abRelationship = PeerRelationship.Provider)
    
    ###############################################################################
    # Add layers to the emulator
    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    emu.addLayer(ibgp)
    emu.addLayer(ospf)
    
    ###############################################################################
    # Render and compile
    if dumpfile is not None:
        emu.dump(dumpfile)
    else:
        emu.render()
        emu.compile(Docker(platform=platform), './output', override=True)

if __name__ == '__main__':
    run()
