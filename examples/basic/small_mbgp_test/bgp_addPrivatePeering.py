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
    base.createInternetExchange(109)

    ###############################################################################
    # Create AS-141 to 141

    as141 = base.createAutonomousSystem(141)
    as141.createNetwork('net0')
    as141.createRouter('router0').joinNetwork('net0').joinNetwork('ix109')

    ###############################################################################
    # Create AS-142

    as142 = base.createAutonomousSystem(142)
    as142.createNetwork('net0')
    as142.createRouter('router0').joinNetwork('net0').joinNetwork('ix109')

    ###############################################################################
    # Create AS-143

    as143 = base.createAutonomousSystem(143)
    as143.createNetwork('net0')
    as143.createRouter('router0').joinNetwork('net0').joinNetwork('ix109')
    ###############################################################################
    # Create AS-144

    as143 = base.createAutonomousSystem(144)
    as143.createNetwork('net0')
    as143.createRouter('router0').joinNetwork('net0').joinNetwork('ix109')

    ###############################################################################
    # Create a Real-World AS (Syracuse University's AS11872)

    #as11872 = base.createAutonomousSystem(11872)
    #as11872.createRealWorldRouter('rw').joinNetwork('ix109', '10.109.0.118')

    ###############################################################################
    # bgp Peering (Private Peering)
    #ebgp.addPrivatePeering(109, 143, 11872, abRelationship=PeerRelationship.Unfiltered)
    
    # Mbgp Peering (Private Peering)
    ebgp.addPrivatePeering(109, 141, 142, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(109, 142, 143, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(109, 143, 144, abRelationship=PeerRelationship.Unfiltered)
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
        emu.compile(Docker(platform=platform), './output_bgp', override=True)
        # add /bird to each router dir for build.
        #subprocess.run(["./2_copy_bird_dir.sh"], check=True) 

if __name__ == '__main__':
    run()
