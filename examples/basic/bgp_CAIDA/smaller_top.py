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
    # Create Internet Exchanges - ONLY 2 IXs

    ix100 = base.createInternetExchange(100)
    ix101 = base.createInternetExchange(101)

    ###############################################################################
    # Create Autonomous Systems

    # Create AS40 - the router with 17 connections
    as40 = base.createAutonomousSystem(40)
    as40.createNetwork('net0')
    as40_router = as40.createRouter('router0')
    as40_router.joinNetwork('net0')
    as40_router.joinNetwork('ix100')
    as40_router.joinNetwork('ix101')
    as40_host = as40.createHost('host0')
    as40_host.joinNetwork('net0')

    # Create ASes for AS40 to connect to - distributed across IX100 and IX101
    # Group 1: IX100 connections (10 ASes)
    ix100_ases = [127, 128, 129, 130, 131, 132, 133, 60, 80, 90]
    for asn in ix100_ases:
        current_as = base.createAutonomousSystem(asn)
        current_as.createNetwork('net0')
        router = current_as.createRouter('router0')
        router.joinNetwork('net0')
        router.joinNetwork('ix100')
        host = current_as.createHost('host0')
        host.joinNetwork('net0')

    # Remove the extra ASes we don't need
    # Group 2: IX101 connections (5 ASes to make total 17 for AS40)
    ix101_ases = [41, 45, 148, 157, 180]
    for asn in ix101_ases:
        current_as = base.createAutonomousSystem(asn)
        current_as.createNetwork('net0')
        router = current_as.createRouter('router0')
        router.joinNetwork('net0')
        router.joinNetwork('ix101')
        host = current_as.createHost('host0')
        host.joinNetwork('net0')

    ###############################################################################
    # Create eBGP peering relationships - AS40 gets exactly 17 connections

    # AS40 connections at IX100 (10 connections)
    for peer_as in ix100_ases:
        ebgp.addPrivatePeering(100, 40, peer_as, abRelationship=PeerRelationship.Unfiltered)

    # AS40 connections at IX101 (7 connections)
    for peer_as in ix101_ases:
        ebgp.addPrivatePeering(101, 40, peer_as, abRelationship=PeerRelationship.Unfiltered)

    # Create some additional relationships between other ASes for realism
    # Clique peering at IX100
    ebgp.addPrivatePeering(100, 127, 128, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(100, 129, 130, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(100, 131, 132, abRelationship=PeerRelationship.Unfiltered)

    # Some IX101 relationships
    ebgp.addPrivatePeering(101, 41, 45, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(101, 148, 157, abRelationship=PeerRelationship.Unfiltered)

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
