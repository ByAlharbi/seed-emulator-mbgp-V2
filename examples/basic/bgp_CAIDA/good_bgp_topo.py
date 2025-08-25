#!/usr/bin/env python3
# encoding: utf-8

from seedemu.layers import Base, Routing, Ebgp, PeerRelationship
from seedemu.compiler import Docker, Platform
from seedemu.core import Emulator
import sys, os, subprocess

def run(dumpfile = None):
    emu     = Emulator()
    base    = Base()
    routing = Routing()
    ebgp    = Ebgp()

    ###############################################################################
    # Create Internet Exchanges - all the same IXs as the original topology

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
    # Create Autonomous Systems with proper IX connectivity

    # Create Tier 0 (Clique) ASes
    as127 = base.createAutonomousSystem(127)
    as127.createNetwork('net0')
    as127_router = as127.createRouter('router0')
    as127_router.joinNetwork('net0')
    as127_router.joinNetwork('ix100')
    as127_host = as127.createHost('host0')
    as127_host.joinNetwork('net0')

    as128 = base.createAutonomousSystem(128)
    as128.createNetwork('net0')
    as128_router = as128.createRouter('router0')
    as128_router.joinNetwork('net0')
    as128_router.joinNetwork('ix100')
    as128_host = as128.createHost('host0')
    as128_host.joinNetwork('net0')

    as129 = base.createAutonomousSystem(129)
    as129.createNetwork('net0')
    as129_router = as129.createRouter('router0')
    as129_router.joinNetwork('net0')
    as129_router.joinNetwork('ix100')
    as129_host = as129.createHost('host0')
    as129_host.joinNetwork('net0')

    as130 = base.createAutonomousSystem(130)
    as130.createNetwork('net0')
    as130_router = as130.createRouter('router0')
    as130_router.joinNetwork('net0')
    as130_router.joinNetwork('ix100')
    as130_router.joinNetwork('ix106')
    as130_host = as130.createHost('host0')
    as130_host.joinNetwork('net0')

    as131 = base.createAutonomousSystem(131)
    as131.createNetwork('net0')
    as131_router = as131.createRouter('router0')
    as131_router.joinNetwork('net0')
    as131_router.joinNetwork('ix100')
    as131_host = as131.createHost('host0')
    as131_host.joinNetwork('net0')

    as132 = base.createAutonomousSystem(132)
    as132.createNetwork('net0')
    as132_router = as132.createRouter('router0')
    as132_router.joinNetwork('net0')
    as132_router.joinNetwork('ix100')
    as132_host = as132.createHost('host0')
    as132_host.joinNetwork('net0')

    as133 = base.createAutonomousSystem(133)
    as133.createNetwork('net0')
    as133_router = as133.createRouter('router0')
    as133_router.joinNetwork('net0')
    as133_router.joinNetwork('ix100')
    as133_host = as133.createHost('host0')
    as133_host.joinNetwork('net0')

    # Create stub ASes connected to ix100
    for asn in [140, 141, 142, 143, 144, 145]:
        current_as = base.createAutonomousSystem(asn)
        current_as.createNetwork('net0')
        router = current_as.createRouter('router0')
        router.joinNetwork('net0')
        router.joinNetwork('ix100')
        host = current_as.createHost('host0')
        host.joinNetwork('net0')

    # Create Tier 1 ASes with proper connectivity
    # Define all AS connectivity
    as_connectivity = {
        # AS134 components (replaced by 40-45)
        40: ['ix100', 'ix101'],
        41: ['ix101', 'ix102'],
        42: ['ix102', 'ix103'],
        43: ['ix103', 'ix105'],
        44: ['ix105', 'ix106'],
        45: ['ix106', 'ix100'],

        # AS135 components (replaced by 50-56)
        50: ['ix100', 'ix102'],
        51: ['ix102', 'ix101'],
        52: ['ix101', 'ix103'],
        53: ['ix103', 'ix104'],
        54: ['ix104', 'ix105'],
        55: ['ix105', 'ix106'],
        56: ['ix106', 'ix100'],

        # AS136 components (replaced by 60-64)
        60: ['ix100', 'ix103'],
        61: ['ix103', 'ix101'],
        62: ['ix101', 'ix105'],
        63: ['ix105', 'ix106'],
        64: ['ix106', 'ix100'],

        # AS137 components (replaced by 70-76)
        70: ['ix100', 'ix104'],
        71: ['ix104', 'ix101'],
        72: ['ix101', 'ix102'],
        73: ['ix102', 'ix103'],
        74: ['ix103', 'ix105'],
        75: ['ix105', 'ix106'],
        76: ['ix106', 'ix100'],

        # AS138 components (replaced by 80-85)
        80: ['ix100', 'ix105'],
        81: ['ix105', 'ix101'],
        82: ['ix101', 'ix102'],
        83: ['ix102', 'ix103'],
        84: ['ix103', 'ix106'],
        85: ['ix106', 'ix100'],

        # AS139 components (replaced by 90-94)
        90: ['ix100', 'ix106'],
        91: ['ix106', 'ix101'],
        92: ['ix101', 'ix103'],
        93: ['ix103', 'ix105'],
        94: ['ix105', 'ix100'],

        # Tier 2 Transit ASes
        148: ['ix100', 'ix101'],
        152: ['ix100', 'ix102'],
        156: ['ix100', 'ix103'],
        151: ['ix102', 'ix103'],
        157: ['ix100', 'ix101', 'ix102', 'ix103', 'ix104', 'ix105', 'ix106'],
        159: ['ix100', 'ix101', 'ix102', 'ix103', 'ix105', 'ix106'],
        161: ['ix101', 'ix103', 'ix104', 'ix105'],
        165: ['ix101', 'ix102', 'ix104', 'ix106'],
        171: ['ix100', 'ix101', 'ix102', 'ix103', 'ix105', 'ix106'],
        172: ['ix100', 'ix101', 'ix102', 'ix103', 'ix105', 'ix106'],
        166: ['ix101', 'ix102', 'ix103', 'ix105', 'ix106'],
        173: ['ix101', 'ix102', 'ix103', 'ix105', 'ix106'],
        176: ['ix100', 'ix101', 'ix102', 'ix103', 'ix104', 'ix105', 'ix106', 'ix107'],
        178: ['ix101', 'ix102', 'ix103', 'ix104', 'ix105'],
        179: ['ix101', 'ix102', 'ix103', 'ix104', 'ix106', 'ix108'],
        180: ['ix100', 'ix101', 'ix102', 'ix103', 'ix104', 'ix105', 'ix106', 'ix109'],
        181: ['ix101', 'ix104', 'ix105', 'ix106', 'ix110']
    }

    # Create all ASes with their proper IX connections
    for asn, exchanges in as_connectivity.items():
        current_as = base.createAutonomousSystem(asn)
        current_as.createNetwork('net0')
        router = current_as.createRouter('router0')
        router.joinNetwork('net0')
        for exchange in exchanges:
            router.joinNetwork(exchange)
        host = current_as.createHost('host0')
        host.joinNetwork('net0')

    # Create the stub ASes for other internet exchanges
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
    # Create eBGP peering relationships between ASes - CAREFULLY AVOIDING DUPLICATES

    # Clique Peering @ IX100
    ebgp.addPrivatePeerings(100, [131], [132, 128, 129, 133, 130], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(100, [132], [128, 129, 133, 130], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(100, [127], [128, 129, 133], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(100, [128], [129, 133, 130], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(100, [129], [133, 130], PeerRelationship.Peer)
    ebgp.addPrivatePeerings(100, [133], [130], PeerRelationship.Peer)

    # Clique-Stubs @ IX100
    ebgp.addPrivatePeering(100, 133, 140, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(100, 129, 141, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(100, 130, 142, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(100, 128, 143, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(100, 132, 144, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(100, 131, 145, abRelationship=PeerRelationship.Unfiltered)

    # Connect clique ASes to Tier 1 representatives at IX100
    # Connections to AS134 (now AS40)
    ebgp.addPrivatePeerings(100, [131, 133, 132, 128, 127, 130], [40], PeerRelationship.Provider)
    # Connections to AS135 (now AS50)
    ebgp.addPrivatePeerings(100, [131, 133, 132, 128, 127, 130, 129], [50], PeerRelationship.Provider)
    # Connections to AS136 (now AS60)
    ebgp.addPrivatePeerings(100, [131, 132, 128, 127, 130], [60], PeerRelationship.Provider)
    # Connections to AS137 (now AS70)
    ebgp.addPrivatePeerings(100, [131, 132, 129], [70], PeerRelationship.Provider)
    # Connections to AS138 (now AS80)
    ebgp.addPrivatePeerings(100, [131, 133, 132], [80], PeerRelationship.Provider)
    # Connections to AS139 (now AS90)
    ebgp.addPrivatePeerings(100, [131, 133, 129], [90], PeerRelationship.Provider)

    # Connect the Tier 1 systems (previously part of the same AS) with peering sessions
    # AS134 components (AS40-45)
    ebgp.addPrivatePeering(100, 40, 45, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(101, 40, 41, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(102, 41, 42, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(103, 42, 43, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(105, 43, 44, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(106, 44, 45, abRelationship=PeerRelationship.Unfiltered)

    # AS135 components (AS50-56)
    ebgp.addPrivatePeering(100, 50, 56, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(102, 50, 51, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(101, 51, 52, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(103, 52, 53, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(104, 53, 54, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(105, 54, 55, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(106, 55, 56, abRelationship=PeerRelationship.Unfiltered)

    # AS136 components (AS60-64)
    ebgp.addPrivatePeering(100, 60, 64, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(103, 60, 61, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(101, 61, 62, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(105, 62, 63, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(106, 63, 64, abRelationship=PeerRelationship.Unfiltered)

    # AS137 components (AS70-76)
    ebgp.addPrivatePeering(100, 70, 76, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(104, 70, 71, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(101, 71, 72, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(102, 72, 73, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(103, 73, 74, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(105, 74, 75, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(106, 75, 76, abRelationship=PeerRelationship.Unfiltered)

    # AS138 components (AS80-85)
    ebgp.addPrivatePeering(100, 80, 85, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(105, 80, 81, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(101, 81, 82, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(102, 82, 83, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(103, 83, 84, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(106, 84, 85, abRelationship=PeerRelationship.Unfiltered)

    # AS139 components (AS90-94)
    ebgp.addPrivatePeering(100, 90, 94, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(106, 90, 91, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(101, 91, 92, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(103, 92, 93, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(105, 93, 94, abRelationship=PeerRelationship.Unfiltered)

    # Peer relationships between Tier 1 ASes at IX100
    tier1_as_groups = [[40, 45], [50, 56], [60, 64], [70, 76], [80, 85], [90, 94]]
    for i in range(len(tier1_as_groups)):
        for j in range(i+1, len(tier1_as_groups)):
            ebgp.addPrivatePeering(100, tier1_as_groups[i][0], tier1_as_groups[j][0], abRelationship=PeerRelationship.Unfiltered)

    # Connect Tier 1 components to stubs at various IXs
    # IX101 stubs
    for stub_as in [146, 147, 149, 150]:
        ebgp.addPrivatePeering(101, 41, stub_as, abRelationship=PeerRelationship.Unfiltered)

    # IX102 stubs
    for stub_as in [153, 154, 155]:
        ebgp.addPrivatePeering(102, 51, stub_as, abRelationship=PeerRelationship.Unfiltered)

    # IX103 stub
    ebgp.addPrivatePeering(103, 61, 158, abRelationship=PeerRelationship.Unfiltered)

    # IX104 stubs
    for stub_as in [162, 163, 164]:
        ebgp.addPrivatePeering(104, 71, stub_as, abRelationship=PeerRelationship.Unfiltered)

    # IX105 stubs
    for stub_as in [167, 168, 169, 170]:
        ebgp.addPrivatePeering(105, 81, stub_as, abRelationship=PeerRelationship.Unfiltered)

    # IX106 stubs
    for stub_as in [175, 177]:
        ebgp.addPrivatePeering(106, 91, stub_as, abRelationship=PeerRelationship.Unfiltered)

    # Connect transit ASes to appropriate Tier 1 ASes - BASIC ESSENTIAL CONNECTIONS ONLY
    # IX100 connections
    ebgp.addPrivatePeering(100, 40, 148, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(100, 50, 152, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(100, 60, 156, abRelationship=PeerRelationship.Unfiltered)

    # Additional basic transit connections
    ebgp.addPrivatePeering(102, 51, 151, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(103, 61, 157, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(103, 61, 159, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(104, 71, 161, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(104, 71, 165, abRelationship=PeerRelationship.Unfiltered)

    # P2C relationships from the original topology
    ebgp.addPrivatePeering(103, 61, 43, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(103, 159, 43, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(103, 61, 53, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(102, 153, 152, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(105, 169, 157, abRelationship=PeerRelationship.Unfiltered)

    # A minimal set of additional connections to ensure connectivity
    # Careful: only add what's necessary and avoid duplicates
    ebgp.addPrivatePeering(100, 176, 130, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(101, 176, 41, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(101, 178, 41, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(101, 179, 41, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(102, 178, 51, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(103, 179, 61, abRelationship=PeerRelationship.Unfiltered)

    # Core connectivity - AS91 to key T2 peers at IX106 (avoiding duplicates)
    ebgp.addPrivatePeering(106, 91, 159, abRelationship=PeerRelationship.Unfiltered)
    # NOT added: ebgp.addPrivatePeering(106, 91, 171, abRelationship=PeerRelationship.Unfiltered)
    # NOT added: ebgp.addPrivatePeering(106, 91, 172, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(106, 91, 173, abRelationship=PeerRelationship.Unfiltered)

    # Essential connectivity from Tier 1 to Tier 2 to ensure end-to-end paths
    ebgp.addPrivatePeering(100, 40, 157, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(100, 50, 159, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(103, 61, 151, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(105, 81, 166, abRelationship=PeerRelationship.Unfiltered)

    # Create a few strategic T2-T2 relationships to ensure connectivity
    ebgp.addPrivatePeering(106, 171, 172, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(106, 171, 173, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(100, 157, 159, abRelationship=PeerRelationship.Unfiltered)

    # Add peering for AS180 and AS181 to ensure full connectivity
    ebgp.addPrivatePeering(101, 41, 181, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(104, 71, 181, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(105, 81, 181, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(106, 91, 181, abRelationship=PeerRelationship.Unfiltered)

    ebgp.addPrivatePeering(100, 40, 180, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(103, 61, 180, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(105, 81, 180, abRelationship=PeerRelationship.Unfiltered)

    ###############################################################################
    # Rendering

    emu.addLayer(base)
    emu.addLayer(routing)
    emu.addLayer(ebgp)

    # Save or compile
    if dumpfile is not None:
        emu.dump(dumpfile)
    else:
        emu.render()
        emu.compile(Docker(), './output', override=True)

if __name__ == '__main__':
    run()

