#!/usr/bin/env python3
# encoding: utf-8

from seedemu.layers import Base, Routing, Ebgp, Mbgp, PeerRelationship
from seedemu.core import Emulator
from seedemu.compiler import Docker, Platform
import os, sys, subprocess

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
    
    emu     = Emulator()
    base    = Base()
    routing = Routing()
    ebgp    = Ebgp()
    mbgp    = Mbgp()
    ###############################################################################
    # Create Internet exchanges 

    ix100 = base.createInternetExchange(100)
    ix101 = base.createInternetExchange(101)
    ix102 = base.createInternetExchange(102)
    ix103 = base.createInternetExchange(103)
    ix104 = base.createInternetExchange(104)
    ix105 = base.createInternetExchange(105)
    ix106 = base.createInternetExchange(106)
    

    ###############################################################################
    # Create Autonomous Systems (ASes) and their networks

    as150 = base.createAutonomousSystem(150)
    as149 = base.createAutonomousSystem(149)
    as148 = base.createAutonomousSystem(148)
    as151 = base.createAutonomousSystem(151)
    as152 = base.createAutonomousSystem(152)
    as153 = base.createAutonomousSystem(153)
    as154 = base.createAutonomousSystem(154)
    as11872 = base.createAutonomousSystem(11872)

    # Create networks based on the diagram
    as150.createNetwork('net0')
    as149.createNetwork('net0')
    as148.createNetwork('net0')
    as151.createNetwork('net0')
    as152.createNetwork('net0')
    as153.createNetwork('net0')
    as154.createNetwork('net0')
    
    # Connect routers within AS150 following the provided topology
    as150.createRouter('r150').joinNetwork('net0').joinNetwork('ix100').joinNetwork('ix101').joinNetwork('ix102').joinNetwork('ix103')
    as149.createRouter('r149').joinNetwork('net0').joinNetwork('ix100')
    as148.createRouter('r148').joinNetwork('net0').joinNetwork('ix101')
    as151.createRouter('r151').joinNetwork('net0').joinNetwork('ix103').joinNetwork('ix104')
    as152.createRouter('r152').joinNetwork('net0').joinNetwork('ix104').joinNetwork('ix105').joinNetwork('ix106')
    as153.createRouter('r153').joinNetwork('net0').joinNetwork('ix105')
    as154.createRouter('r154').joinNetwork('net0').joinNetwork('ix106')
    as11872.createRealWorldRouter('rw').joinNetwork('ix102', '10.102.0.118')

    # Attach hosts to networks based on the diagram
    as149.createHost('host0').joinNetwork('net0')
    as148.createHost('host0').joinNetwork('net0')
    as151.createHost('host0').joinNetwork('net0')
    as152.createHost('host0').joinNetwork('net0')
    as153.createHost('host0').joinNetwork('net0')
    as154.createHost('host0').joinNetwork('net0')
    
    ###############################################################################
    # mBGP Peering for Internal AS Connections based on topology
    mbgp.addPrivatePeering(100, 150, 149, abRelationship = PeerRelationship.Unfiltered)
    mbgp.addPrivatePeering(101, 150, 148, abRelationship = PeerRelationship.Unfiltered)
    mbgp.addPrivatePeering(103, 150, 151, abRelationship = PeerRelationship.Unfiltered)
    mbgp.addPrivatePeering(104, 151, 152, abRelationship = PeerRelationship.Unfiltered)
    mbgp.addPrivatePeering(105, 152, 153, abRelationship = PeerRelationship.Unfiltered)
    mbgp.addPrivatePeering(106, 152, 154, abRelationship = PeerRelationship.Unfiltered)
    
    # eBGP Peering for AS11872
    ebgp.addPrivatePeering(102, 150, 11872, abRelationship = PeerRelationship.Unfiltered)
    
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
        subprocess.run(["./copy_bird_dir.sh"], check=True) 

if __name__ == "__main__":
    run()
