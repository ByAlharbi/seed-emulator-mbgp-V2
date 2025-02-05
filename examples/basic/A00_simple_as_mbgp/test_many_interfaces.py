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
   # Create an Internet Exchange
    base.createInternetExchange(100)
    base.createInternetExchange(101)

    ###############################################################################
    # Create AS-149

    as149 = base.createAutonomousSystem(149)
    as149.createNetwork('net0')
    as149.createRouter('router0').joinNetwork('net0').joinNetwork('ix100')

    ###############################################################################
    # Create AS-150

    as150 = base.createAutonomousSystem(150)
    as150.createNetwork('net0')
    as150.createRouter('router0').joinNetwork('net0').joinNetwork('ix100').joinNetwork('ix101')

    ###############################################################################
    # Create AS-151

    as151 = base.createAutonomousSystem(151)
    as151.createNetwork('net0')
    as151.createRouter('router0').joinNetwork('net0').joinNetwork('ix101')

    ###############################################################################
    # Create a Real-World AS (Syracuse University's AS11872)

    as11872 = base.createAutonomousSystem(11872)
    as11872.createRealWorldRouter('rw').joinNetwork('ix101', '10.101.0.118')

    ###############################################################################
    # bgp Peering (Private Peering)
    ebgp.addPrivatePeering(101, 151, 11872, abRelationship=PeerRelationship.Unfiltered)
    
    # Mbgp Peering (Private Peering)
    mbgp.addPrivatePeering(100, 149, 150, abRelationship=PeerRelationship.Unfiltered)
    mbgp.addPrivatePeering(101, 150, 151, abRelationship=PeerRelationship.Unfiltered)

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

