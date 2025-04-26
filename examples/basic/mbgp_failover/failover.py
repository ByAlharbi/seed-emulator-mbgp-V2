#!/usr/bin/env python3
# encoding: utf-8

from seedemu.layers import Base, Routing, Ebgp, Mbgp, PeerRelationship
from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator
import sys, os, subprocess

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
    mbgp    = Mbgp()

    ###############################################################################
    # Create Internet Exchanges for network connectivity
    base.createInternetExchange(100)  # Main IX for R1-R2 and R1-R4
    base.createInternetExchange(101)  # IX for R2-R3 connection (primary path)
    base.createInternetExchange(102)  # IX for R4-R5 connection (backup path)
    base.createInternetExchange(103)  # IX for R5-R3 connection
    base.createInternetExchange(104)  # IX for R3-R6 connection

    ###############################################################################
    # Create AS-150 (Origin Router - R1)
    as150 = base.createAutonomousSystem(150)
    as150.createNetwork('net0')
    as150.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')
    as150.createHost('host0').joinNetwork('net0')
    
    ###############################################################################
    # Create AS-151 (Primary Path Router - R2)
    as151 = base.createAutonomousSystem(151)
    as151.createNetwork('net0')
    as151.createRouter('router0').joinNetwork('net0').joinNetwork('ix100').joinNetwork('ix101')
    
    ###############################################################################
    # Create AS-152 (Junction Router - R3)
    as152 = base.createAutonomousSystem(152)
    as152.createNetwork('net0')
    as152.createRouter('router0').joinNetwork('net0').joinNetwork('ix101').joinNetwork('ix103').joinNetwork('ix104')
    
    ###############################################################################
    # Create AS-153 (Backup Path Router - R4)
    as153 = base.createAutonomousSystem(153)
    as153.createNetwork('net0')
    as153.createRouter('router0').joinNetwork('net0').joinNetwork('ix100').joinNetwork('ix102')
    
    ###############################################################################
    # Create AS-154 (Backup Path Router - R5)
    as154 = base.createAutonomousSystem(154)
    as154.createNetwork('net0')
    as154.createRouter('router0').joinNetwork('net0').joinNetwork('ix102').joinNetwork('ix103')
    
    ###############################################################################
    # Create AS-155 (Destination Router - R6)
    as155 = base.createAutonomousSystem(155)
    as155.createNetwork('net0')
    as155.createRouter('router0').joinNetwork('net0').joinNetwork('ix104')
    as155.createHost('host0').joinNetwork('net0')

    ###############################################################################
    # Mbgp Peering (Private Peering with Unfiltered relationship)
    mbgp.addPrivatePeering(100, 150, 151, abRelationship=PeerRelationship.Unfiltered)
    mbgp.addPrivatePeering(101, 151, 152, abRelationship=PeerRelationship.Unfiltered)
    mbgp.addPrivatePeering(104, 152, 155, abRelationship=PeerRelationship.Unfiltered)
    
    mbgp.addPrivatePeering(100, 150, 153, abRelationship=PeerRelationship.Unfiltered)
    mbgp.addPrivatePeering(102, 153, 154, abRelationship=PeerRelationship.Unfiltered)
    mbgp.addPrivatePeering(103, 154, 152, abRelationship=PeerRelationship.Unfiltered)

    ###############################################################################
    # Rendering 
    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    emu.addLayer(mbgp)

    if dumpfile is not None:
        emu.dump(dumpfile)
    else:
        emu.render()

        ###############################################################################
        # Compilation
        emu.compile(Docker(platform=platform), './output', override=True)
        # add /bird to each router dir for build.
        subprocess.run(["./copy_bird_dir.sh"], check=True) 

if __name__ == '__main__':
    run()
