
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

    # Create Tier 1 AS groups - All 6 groups to match original
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
        56: ['ix106', 'ix100'],
        
        # AS136 components (AS60-64) - 5 components forming a ring
        60: ['ix100', 'ix103'],
        61: ['ix103', 'ix101'],
        62: ['ix101', 'ix105'],
        63: ['ix105', 'ix106'],
        64: ['ix106', 'ix100'],
        
        # AS137 components (AS70-76) - 7 components forming a ring
        70: ['ix100', 'ix104'],
        71: ['ix104', 'ix101'],
        72: ['ix101', 'ix102'],
        73: ['ix102', 'ix103'],
        74: ['ix103', 'ix105'],
        75: ['ix105', 'ix106'],
        76: ['ix106', 'ix100'],
        
        # AS138 components (AS80-85) - 6 components forming a ring
        80: ['ix100', 'ix105'],
        81: ['ix105', 'ix101'],
        82: ['ix101', 'ix102'],
        83: ['ix102', 'ix103'],
        84: ['ix103', 'ix106'],
        85: ['ix106', 'ix100'],
        
        # AS139 components (AS90-94) - 5 components forming a ring
        90: ['ix100', 'ix106'],
        91: ['ix106', 'ix101'],
        92: ['ix101', 'ix103'],
        93: ['ix103', 'ix105'],
        94: ['ix105', 'ix100']
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

    # Connect clique ASes to all Tier 1 groups as customers
    # Use only the 4 clique ASes that actually exist: 127, 128, 129, 130
    ebgp.addPrivatePeerings(100, [127, 128, 129, 130], [40], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(100, [127, 128, 129, 130], [50], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(100, [127, 128, 129, 130], [60], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(100, [127, 128, 129, 130], [70], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(100, [127, 128, 129, 130], [80], PeerRelationship.Provider)
    ebgp.addPrivatePeerings(100, [127, 128, 129, 130], [90], PeerRelationship.Provider)

    # Connect Tier 1 components in rings
    # AS134 ring (AS40-45)
    ebgp.addPrivatePeering(100, 40, 45, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(101, 40, 41, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(102, 41, 42, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(103, 42, 43, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(105, 43, 44, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(106, 44, 45, abRelationship=PeerRelationship.Unfiltered)
        
    # AS135 ring (AS50-56)
    ebgp.addPrivatePeering(100, 50, 56, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(102, 50, 51, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(101, 51, 52, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(103, 52, 53, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(104, 53, 54, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(105, 54, 55, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(106, 55, 56, abRelationship=PeerRelationship.Unfiltered)

    # AS136 ring (AS60-64)
    ebgp.addPrivatePeering(100, 60, 64, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(103, 60, 61, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(101, 61, 62, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(105, 62, 63, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(106, 63, 64, abRelationship=PeerRelationship.Unfiltered)

    # AS137 ring (AS70-76)
    ebgp.addPrivatePeering(100, 70, 76, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(104, 70, 71, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(101, 71, 72, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(102, 72, 73, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(103, 73, 74, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(105, 74, 75, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(106, 75, 76, abRelationship=PeerRelationship.Unfiltered)

    # AS138 ring (AS80-85)
    ebgp.addPrivatePeering(100, 80, 85, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(105, 80, 81, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(101, 81, 82, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(102, 82, 83, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(103, 83, 84, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(106, 84, 85, abRelationship=PeerRelationship.Unfiltered)

    # AS139 ring (AS90-94)
    ebgp.addPrivatePeering(100, 90, 94, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(106, 90, 91, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(101, 91, 92, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(103, 92, 93, abRelationship=PeerRelationship.Unfiltered)
    ebgp.addPrivatePeering(105, 93, 94, abRelationship=PeerRelationship.Unfiltered)

    # Tier 1 to Tier 1 peering relationships - potential loop source!
    # Each Tier 1 AS group peers with others at IX100
    tier1_representatives = [40, 50, 60, 70, 80, 90]
    for i in range(len(tier1_representatives)):
        for j in range(i+1, len(tier1_representatives)):
            ebgp.addPrivatePeering(100, tier1_representatives[i], tier1_representatives[j], 
                                 abRelationship=PeerRelationship.Peer)

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
