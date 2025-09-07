#!/usr/bin/env python3
# encoding: utf-8

from seedemu.layers import Base, Routing, Ebgp, PeerRelationship
from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator
import sys, os, subprocess

def run(dumpfile = None):
    ###############################################################################
    emu     = Emulator()
    base    = Base()
    routing = Routing()
    ebgp    = Ebgp()

    ###############################################################################
    # Create Internet Exchanges
    
    # Clique
    ix100 = base.createInternetExchange(100)

    # T1
    ix101 = base.createInternetExchange(101)
    ix102 = base.createInternetExchange(102)
    ix103 = base.createInternetExchange(103)
    ix104 = base.createInternetExchange(104)
    ix105 = base.createInternetExchange(105)
    ix106 = base.createInternetExchange(106)

    # T2
    ix107 = base.createInternetExchange(107)
    ix108 = base.createInternetExchange(108)
    ix109 = base.createInternetExchange(109)
    ix110 = base.createInternetExchange(110)
    ix111 = base.createInternetExchange(111)

    ###############################################################################
    # Create Autonomous Systems with single routers

    # Create Tier 0 (Clique) ASes
    clique_ases = [127, 128, 129, 130, 131, 132, 133]
    for asn in clique_ases:
        current_as = base.createAutonomousSystem(asn)
        current_as.createNetwork('net0')
        router = current_as.createRouter('router0')
        router.joinNetwork('net0')
        router.joinNetwork('ix100')
        # AS130 also connects to ix106
        if asn == 130:
            router.joinNetwork('ix106')
        host = current_as.createHost('host0')
        host.joinNetwork('net0')

    # Create stub ASes connected to ix100
    for asn in [140, 141, 142, 143, 144, 145]:
        current_as = base.createAutonomousSystem(asn)
        current_as.createNetwork('net0')
        router = current_as.createRouter('router0')
        router.joinNetwork('net0')
        router.joinNetwork('ix100')
        host = current_as.createHost('host0')
        host.joinNetwork('net0')

    # Create Tier 1 ASes as single routers (instead of decomposed approach)
    # AS134 - consolidate all connections from AS40-45 into one router
    as134 = base.createAutonomousSystem(134)
    as134.createNetwork('net0')
    as134_router = as134.createRouter('router0')
    as134_router.joinNetwork('net0')
    as134_router.joinNetwork('ix101')
    as134_router.joinNetwork('ix100')
    as134_router.joinNetwork('ix102')
    as134_router.joinNetwork('ix103')
    as134_router.joinNetwork('ix105')
    as134_router.joinNetwork('ix106')
    as134_host = as134.createHost('host0')
    as134_host.joinNetwork('net0')

    # AS135 - consolidate all connections from AS50-56 into one router
    as135 = base.createAutonomousSystem(135)
    as135.createNetwork('net0')
    as135_router = as135.createRouter('router0')
    as135_router.joinNetwork('net0')
    as135_router.joinNetwork('ix102')
    as135_router.joinNetwork('ix100')
    as135_router.joinNetwork('ix101')
    as135_router.joinNetwork('ix103')
    as135_router.joinNetwork('ix104')
    as135_router.joinNetwork('ix105')
    as135_router.joinNetwork('ix106')
    as135_host = as135.createHost('host0')
    as135_host.joinNetwork('net0')

    # AS136 - consolidate all connections from AS60-64 into one router
    as136 = base.createAutonomousSystem(136)
    as136.createNetwork('net0')
    as136_router = as136.createRouter('router0')
    as136_router.joinNetwork('net0')
    as136_router.joinNetwork('ix103')
    as136_router.joinNetwork('ix100')
    as136_router.joinNetwork('ix101')
    as136_router.joinNetwork('ix105')
    as136_router.joinNetwork('ix106')
    as136_host = as136.createHost('host0')
    as136_host.joinNetwork('net0')

    # AS137 - consolidate all connections from AS70-76 into one router
    as137 = base.createAutonomousSystem(137)
    as137.createNetwork('net0')
    as137_router = as137.createRouter('router0')
    as137_router.joinNetwork('net0')
    as137_router.joinNetwork('ix104')
    as137_router.joinNetwork('ix100')
    as137_router.joinNetwork('ix101')
    as137_router.joinNetwork('ix102')
    as137_router.joinNetwork('ix103')
    as137_router.joinNetwork('ix105')
    as137_router.joinNetwork('ix106')
    as137_host = as137.createHost('host0')
    as137_host.joinNetwork('net0')

    # AS138 - consolidate all connections from AS80-85 into one router
    as138 = base.createAutonomousSystem(138)
    as138.createNetwork('net0')
    as138_router = as138.createRouter('router0')
    as138_router.joinNetwork('net0')
    as138_router.joinNetwork('ix105')
    as138_router.joinNetwork('ix100')
    as138_router.joinNetwork('ix101')
    as138_router.joinNetwork('ix102')
    as138_router.joinNetwork('ix103')
    as138_router.joinNetwork('ix106')
    as138_host = as138.createHost('host0')
    as138_host.joinNetwork('net0')

    # AS139 - consolidate all connections from AS90-94 into one router
    as139 = base.createAutonomousSystem(139)
    as139.createNetwork('net0')
    as139_router = as139.createRouter('router0')
    as139_router.joinNetwork('net0')
    as139_router.joinNetwork('ix106')
    as139_router.joinNetwork('ix100')
    as139_router.joinNetwork('ix101')
    as139_router.joinNetwork('ix103')
    as139_router.joinNetwork('ix105')
    as139_host = as139.createHost('host0')
    as139_host.joinNetwork('net0')

    # Create Tier 2 Transit ASes as single routers
    tier2_ases = {
        176: ['ix100', 'ix101', 'ix102', 'ix103', 'ix104', 'ix105', 'ix106', 'ix107'],
        178: ['ix101', 'ix102', 'ix103', 'ix104', 'ix105'],
        179: ['ix101', 'ix102', 'ix103', 'ix104', 'ix106', 'ix108'],
        180: ['ix100', 'ix101', 'ix102', 'ix103', 'ix104', 'ix105', 'ix106', 'ix109'],
        181: ['ix101', 'ix104', 'ix105', 'ix106', 'ix110'],
        148: ['ix100', 'ix101'],
        152: ['ix100', 'ix102'],
        156: ['ix100', 'ix103'],
        157: ['ix100', 'ix101', 'ix102', 'ix103', 'ix104', 'ix105', 'ix106'],
        159: ['ix100', 'ix101', 'ix102', 'ix103', 'ix105', 'ix106'],
        151: ['ix100', 'ix101', 'ix102', 'ix103', 'ix104', 'ix105', 'ix106'],
        161: ['ix101', 'ix103', 'ix105', 'ix104'],
        165: ['ix101', 'ix102', 'ix104', 'ix106'],
        171: ['ix100', 'ix101', 'ix102', 'ix103', 'ix105', 'ix106'],
        172: ['ix100', 'ix101', 'ix102', 'ix103', 'ix105', 'ix106'],
        173: ['ix101', 'ix102', 'ix103', 'ix105', 'ix106'],
        166: ['ix101', 'ix102', 'ix103', 'ix105', 'ix106']
    }

    for asn, exchanges in tier2_ases.items():
        current_as = base.createAutonomousSystem(asn)
        current_as.createNetwork('net0')
        router = current_as.createRouter('router0')
        router.joinNetwork('net0')
        for exchange in exchanges:
            router.joinNetwork(exchange)
        host = current_as.createHost('host0')
        host.joinNetwork('net0')

    # Create stub ASes for other IXs
    # For IX101
    for asn in [146, 147, 149, 150]:
        current_as = base.createAutonomousSystem(asn)
        current_as.createNetwork('net0')
        router = current_as.createRouter('router0')
        router.joinNetwork('net0')
        router.joinNetwork('ix101')
        host = current_as.createHost('host0')
        host.joinNetwork('net0')

    # For IX102
    for asn in [153, 154, 155]:
        current_as = base.createAutonomousSystem(asn)
        current_as.createNetwork('net0')
        router = current_as.createRouter('router0')
        router.joinNetwork('net0')
        router.joinNetwork('ix102')
        host = current_as.createHost('host0')
        host.joinNetwork('net0')

    # For IX103
    as158 = base.createAutonomousSystem(158)
    as158.createNetwork('net0')
    as158_router = as158.createRouter('router0')
    as158_router.joinNetwork('net0')
    as158_router.joinNetwork('ix103')
    as158_host = as158.createHost('host0')
    as158_host.joinNetwork('net0')

    # For IX104
    for asn in [162, 163, 164]:
        current_as = base.createAutonomousSystem(asn)
        current_as.createNetwork('net0')
        router = current_as.createRouter('router0')
        router.joinNetwork('net0')
        router.joinNetwork('ix104')
        host = current_as.createHost('host0')
        host.joinNetwork('net0')

    # For IX105
    for asn in [167, 168, 169, 170]:
        current_as = base.createAutonomousSystem(asn)
        current_as.createNetwork('net0')
        router = current_as.createRouter('router0')
        router.joinNetwork('net0')
        router.joinNetwork('ix105')
        host = current_as.createHost('host0')
        host.joinNetwork('net0')

    # For IX106
    for asn in [175, 177]:
        current_as = base.createAutonomousSystem(asn)
        current_as.createNetwork('net0')
        router = current_as.createRouter('router0')
        router.joinNetwork('net0')
        router.joinNetwork('ix106')
        host = current_as.createHost('host0')
        host.joinNetwork('net0')

    ###############################################################################
    # Create eBGP peering relationships - Use original AS numbers (134-139)

    # Clique Peering @ IX100
    ebgp.addPrivatePeerings(100, [131], [132, 128, 129, 133, 130], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(100, [132], [128, 129, 133, 130], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(100, [127], [128, 129, 133], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(100, [128], [129, 133, 130], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(100, [129], [133, 130], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(100, [133], [130], PeerRelationship.Peer)

    # Clique-Stubs @ IX100
    ebgp.addPrivatePeering(100, 133, 140, abRelationship=PeerRelationship.Provider)
    ebgp.addPrivatePeering(100, 129, 141, abRelationship=PeerRelationship.Provider)
    ebgp.addPrivatePeering(100, 130, 142, abRelationship=PeerRelationship.Provider)
    ebgp.addPrivatePeering(100, 128, 143, abRelationship=PeerRelationship.Provider)
    ebgp.addPrivatePeering(100, 132, 144, abRelationship=PeerRelationship.Provider)
    ebgp.addPrivatePeering(100, 131, 145, abRelationship=PeerRelationship.Provider)

    # Clique->T1 @ IX100
    ebgp.addPrivatePeerings(100, [131, 133, 132, 128, 127, 130], [134], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(100, [131, 133, 132, 128, 127, 130, 129], [135], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(100, [131, 132, 128, 127, 130], [136], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(100, [131, 132, 129], [137], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(100, [131, 133, 132], [138], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(100, [131, 133, 129], [139], PeerRelationship.Provider)

    # T1->T2 @ T1 IX
    ebgp.addPrivatePeerings(101, [134], [148, 149, 150, 146, 147], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(103, [136], [156, 157, 158, 159, 151], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(102, [135], [151, 152, 153, 154, 155], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(104, [137], [161, 163, 162, 164, 165], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(105, [138], [166, 167, 168, 169, 170], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(106, [139], [171, 172, 173, 177, 175], PeerRelationship.Provider)

    # Provider to larger customer P2C Links
    ebgp.addPrivatePeering(103, 136, 134, abRelationship=PeerRelationship.Provider)
    ebgp.addPrivatePeering(103, 159, 134, abRelationship=PeerRelationship.Provider)
    ebgp.addPrivatePeering(103, 136, 135, abRelationship=PeerRelationship.Provider)
    ebgp.addPrivatePeering(101, 148, 157, abRelationship=PeerRelationship.Provider)
    ebgp.addPrivatePeering(102, 153, 152, abRelationship=PeerRelationship.Provider)
    ebgp.addPrivatePeering(105, 169, 157, abRelationship=PeerRelationship.Provider)

    # Provider-less Peering (Transit) T2 - 176
    ebgp.addPrivatePeerings(100, [176], [130], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(101, [176], [146, 147], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(101, [176], [150], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(102, [176], [135, 152], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(103, [176], [136, 159, 156, 157, 151], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(104, [176], [137], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(105, [176], [166], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(106, [176], [139], PeerRelationship.Peer)

    # Provider-less Peering (Transit) T2 - 179
    ebgp.addPrivatePeerings(101, [179], [149], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(102, [179], [135], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(103, [179], [157, 151], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(104, [179], [137], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(106, [179], [171, 173, 175], PeerRelationship.Peer)

    # Provider-less Peering (Transit) T2 - 180
    ebgp.addPrivatePeerings(100, [180], [130], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(101, [180], [134], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(102, [180], [152], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(103, [180], [156, 158, 151], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(104, [180], [165], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(105, [180], [170], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(106, [180], [139], PeerRelationship.Peer)

    # Provider-less Peering (Transit) T2 - 181
    ebgp.addPrivatePeerings(101, [181], [134], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(104, [181], [137], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(105, [181], [166], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(106, [181], [171, 173], PeerRelationship.Peer)

    # Provider-less Peering (Transit) T2 - 178
    ebgp.addPrivatePeerings(101, [178], [134], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(102, [178], [135], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(103, [178], [136], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(104, [178], [137], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(105, [178], [166], PeerRelationship.Peer)

    # Additional P2P Links
    ebgp.addPrivatePeerings(103, [134], [156, 158], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(102, [134], [152], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(105, [134], [170, 167, 168, 169], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(106, [134], [173], PeerRelationship.Peer)

    ebgp.addPrivatePeerings(101, [137], [134, 149], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(102, [137], [135, 152], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(103, [137], [151, 158, 156, 157, 136], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(105, [137], [170, 166, 167, 138, 168], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(106, [137], [172, 175, 139, 173, 171, 177], PeerRelationship.Peer)

    ebgp.addPrivatePeerings(100, [136], [133], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(101, [136], [149], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(105, [136], [138, 168, 167], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(106, [136], [175, 139, 173], PeerRelationship.Peer)

    ebgp.addPrivatePeerings(100, [139], [130, 128], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(101, [139], [148, 149, 134], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(103, [139], [158, 156], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(105, [139], [138, 168, 170, 167], PeerRelationship.Peer)

    ebgp.addPrivatePeerings(101, [135], [149, 134], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(103, [135], [156, 158], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(104, [135], [161], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(105, [135], [138, 168, 167, 170], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(106, [135], [171, 177, 175, 139, 172], PeerRelationship.Peer)

    ebgp.addPrivatePeerings(101, [138], [134, 149], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(102, [138], [152], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(103, [138], [156, 158], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(106, [138], [175, 173], PeerRelationship.Peer)

    ebgp.addPrivatePeerings(100, [157], [130], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(101, [157], [134], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(102, [157], [135], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(104, [157], [161], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(105, [157], [168, 138, 166], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(106, [157], [172, 139, 173, 171], PeerRelationship.Peer)

    ebgp.addPrivatePeerings(100, [159], [130], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(101, [159], [148, 149], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(102, [159], [152, 135, 151], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(103, [159], [158, 157], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(105, [159], [167, 170, 168, 138, 166], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(106, [159], [139, 172, 171, 173, 175], PeerRelationship.Peer)

    ebgp.addPrivatePeerings(100, [151], [129], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(101, [151], [134], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(104, [151], [161], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(105, [151], [168, 138], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(106, [151], [173, 139], PeerRelationship.Peer)

    ebgp.addPrivatePeerings(101, [161], [134], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(103, [161], [156, 158], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(104, [161], [163], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(105, [161], [170], PeerRelationship.Peer)

    ebgp.addPrivatePeerings(101, [165], [134], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(102, [165], [135], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(106, [165], [172, 139], PeerRelationship.Peer)

    ebgp.addPrivatePeerings(102, [155], [153], PeerRelationship.Peer)

    ebgp.addPrivatePeerings(100, [171], [129], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(101, [171], [134, 149, 148], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(102, [171], [152], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(103, [171], [151, 156, 136, 158], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(105, [171], [168, 138], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(106, [171], [173, 175, 172], PeerRelationship.Peer)

    ebgp.addPrivatePeerings(100, [172], [130, 133], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(101, [172], [134, 149, 148], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(102, [172], [152], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(103, [172], [151, 156, 136, 158], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(105, [172], [138, 168, 167], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(106, [172], [175, 173, 177], PeerRelationship.Peer)

    ebgp.addPrivatePeerings(101, [173], [149], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(103, [173], [158, 156], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(105, [173], [168, 170], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(106, [173], [175], PeerRelationship.Peer)

    ebgp.addPrivatePeerings(101, [166], [150, 134], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(102, [166], [152, 135], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(103, [166], [156, 151, 136, 158], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(105, [166], [170, 167], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(106, [166], [173, 171, 175, 139, 172], PeerRelationship.Peer)

    ebgp.addPrivatePeerings(105, [168], [170, 167], PeerRelationship.Peer)

    ebgp.addPrivatePeerings(105, [169], [167], PeerRelationship.Peer)

    ebgp.addPrivatePeerings(100, [156], [129, 128], PeerRelationship.Peer)

    ebgp.addPrivatePeerings(100, [152], [133], PeerRelationship.Peer)

    ebgp.addPrivatePeerings(100, [148], [128], PeerRelationship.Peer)

    ###############################################################################
    # Add layers to the emulator
    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)

    # Rendering and compilation
    if dumpfile is not None:
        emu.dump(dumpfile)
    else:
        # Set the platform information
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

        # Save it to a component file
        emu.dump('base-component.bin')
        
        # Render and compile
        emu.render()
        emu.compile(Docker(platform=platform), './bgp_output', override=True)

if __name__ == '__main__':
    run()
