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
    ix104 = base.createInternetExchange(104)  # Needed for AS135's ring
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

    # Create Tier 1 AS groups - 2 groups for debugging
    tier1_connectivity = {
        # AS134 components (AS40-45) - 6 components forming a ring
        40: ['ix100', 'ix101'],
        41: ['ix101', 'ix102'],
        42: ['ix102', 'ix103'],
        43: ['ix103', 'ix105'],
        44: ['ix105', 'ix106'],
        45: ['ix106', 'ix100'],
        
        # AS135 components (AS50-56) - 7 components forming a ring  
        50: ['ix100', 'ix102'],
        51: ['ix102', 'ix101'],
        52: ['ix101', 'ix103'],
        53: ['ix103', 'ix104'],
        54: ['ix104', 'ix105'],
        55: ['ix105', 'ix106'],
        56: ['ix106', 'ix100']
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

    # Connect clique ASes to both Tier 1 groups as customers
    ebgp.addPrivatePeerings(100, clique_ases, [40], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(100, clique_ases, [50], PeerRelationship.Provider)

    # Connect Tier 1 components in rings
    # AS134 ring (AS40-45)
    tier1_as134_connections = [
        (100, 40, 45),  # Close the ring
        (101, 40, 41),
        (102, 41, 42), 
        (103, 42, 43),
        (105, 43, 44),
        (106, 44, 45)
    ]
    
    for ix, as1, as2 in tier1_as134_connections:
        ebgp.addPrivatePeering(ix, as1, as2, abRelationship=PeerRelationship.Unfiltered)
        
    # AS135 ring (AS50-56)
    tier1_as135_connections = [
        (100, 50, 56),  # Close the ring
        (102, 50, 51),
        (101, 51, 52),
        (103, 52, 53),
        (104, 53, 54),
        (105, 54, 55),
        (106, 55, 56)
    ]
    
    for ix, as1, as2 in tier1_as135_connections:
        ebgp.addPrivatePeering(ix, as1, as2, abRelationship=PeerRelationship.Unfiltered)

    # Tier 1 to Tier 1 peering - this might be where loops form!
    ebgp.addPrivatePeering(100, 40, 50, abRelationship=PeerRelationship.Peer)

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