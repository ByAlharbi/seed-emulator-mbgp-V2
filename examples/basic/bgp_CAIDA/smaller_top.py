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
    # Create Internet Exchanges - minimal set

    # Main clique exchange
    ix100 = base.createInternetExchange(100)
    
    # Tier 1 exchanges for the ring topology
    ix101 = base.createInternetExchange(101)
    ix102 = base.createInternetExchange(102)
    ix103 = base.createInternetExchange(103)
    ix105 = base.createInternetExchange(105)
    ix106 = base.createInternetExchange(106)

    ###############################################################################
    # Create Autonomous Systems - Mini clique + 1 Tier 1 group

    # Create mini Tier 0 (Clique) - just 4 ASes for easier debugging
    clique_ases = [127, 128, 129, 130]
    for asn in clique_ases:
        current_as = base.createAutonomousSystem(asn)
        current_as.createNetwork('net0')
        router = current_as.createRouter('router0')
        router.joinNetwork('net0')
        router.joinNetwork('ix100')
        # AS130 also connects to ix106 like in original
        if asn == 130:
            router.joinNetwork('ix106')
        host = current_as.createHost('host0')
        host.joinNetwork('net0')

    # Create Tier 1 AS group - AS134 components (AS40-45) with ring topology
    tier1_connectivity = {
        40: ['ix100', 'ix101'],
        41: ['ix101', 'ix102'], 
        42: ['ix102', 'ix103'],
        43: ['ix103', 'ix105'],
        44: ['ix105', 'ix106'],
        45: ['ix106', 'ix100']
    }

    for asn, exchanges in tier1_connectivity.items():
        current_as = base.createAutonomousSystem(asn)
        current_as.createNetwork('net0')
        router = current_as.createRouter('router0')
        router.joinNetwork('net0')
        for exchange in exchanges:
            router.joinNetwork(exchange)
        host = current_as.createHost('host0')
        host.joinNetwork('net0')

    ###############################################################################
    # Create eBGP peering relationships

    # Mini clique peering @ IX100 - full mesh between 4 clique ASes
    clique_peerings = [
        (127, [128, 129, 130]),
        (128, [129, 130]),
        (129, [130])
    ]
    
    for provider, customers in clique_peerings:
        ebgp.addPrivatePeerings(100, [provider], customers, PeerRelationship.Peer)

    # Connect clique ASes to Tier 1 (AS40) as customers
    # All clique ASes are providers to the Tier 1 network
    ebgp.addPrivatePeerings(100, clique_ases, [40], PeerRelationship.Provider)

    # Connect Tier 1 components in a ring (AS40-45)
    tier1_ring_connections = [
        (100, 40, 45),  # Close the ring
        (101, 40, 41),
        (102, 41, 42), 
        (103, 42, 43),
        (105, 43, 44),
        (106, 44, 45)
    ]
    
    for ix, as1, as2 in tier1_ring_connections:
        ebgp.addPrivatePeering(ix, as1, as2, abRelationship=PeerRelationship.Unfiltered)

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