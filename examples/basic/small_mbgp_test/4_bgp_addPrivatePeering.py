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
    #mbgp    = Mbgp()

    ###############################################################################
   # Create an Internet Exchange
    base.createInternetExchange(102)
    
    ###############################################################################
    # Create AS-146

    as146 = base.createAutonomousSystem(146)
    as146.createNetwork('net0')
    as146.createRouter('router0').joinNetwork('net0').joinNetwork('ix102')
    ###############################################################################
    # Create AS-144

    as147 = base.createAutonomousSystem(147)
    as147.createNetwork('net0')
    as147.createRouter('router0').joinNetwork('net0').joinNetwork('ix102')
    ###############################################################################
    # Create AS-148

    as148 = base.createAutonomousSystem(148)
    as148.createNetwork('net0')
    as148.createRouter('router0').joinNetwork('net0').joinNetwork('ix102')
    
    ###############################################################################
    # Create AS-149

    as149 = base.createAutonomousSystem(149)
    as149.createNetwork('net0')
    as149.createRouter('router0').joinNetwork('net0').joinNetwork('ix102')

    
    ###############################################################################
    # Create a Real-World AS (Syracuse University's AS11872)

    #as11872 = base.createAutonomousSystem(11872)
    #as11872.createRealWorldRouter('rw').joinNetwork('ix109', '10.109.0.118')

    ###############################################################################
    # bgp Peering (Private Peering)
    #ebgp.addPrivatePeering(109, 146, 11872, abRelationship=PeerRelationship.Unfiltered)
    
    # Mbgp Peering (Private Peering)
    ebgp.addPrivatePeering(102, 146, 147, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(102, 147, 148, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(102, 148, 149, abRelationship=PeerRelationship.Unfiltered)
 
    ###############################################################################
    # Rendering 

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)
    #emu.addLayer(mbgp)
    


    if dumpfile is not None:
        emu.dump(dumpfile)
    else:
        emu.render()

        ###############################################################################
        # Compilation
        emu.compile(Docker(platform=platform), './output_4_bgp', override=True)
        # add /bird to each router dir for build.
        subprocess.run(["./copy_bird_dir.sh"], check=True) 

if __name__ == '__main__':
    run()
