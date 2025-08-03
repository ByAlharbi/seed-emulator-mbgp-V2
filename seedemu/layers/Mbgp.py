from __future__ import annotations
from .Routing import Router
from seedemu.core import Registry, ScopedRegistry, Network, Interface, Graphable, Emulator, Layer
from seedemu.core.enums import NodeRole
from typing import Tuple, List, Dict
from enum import Enum

MbgpFileTemplates: Dict[str, str] = {}

# Template for Route Server side (with rs client)
MbgpFileTemplates["rs_mbgp_peer"] = """
    ipv4;
    rs client;
    local {localAddress} as {localAsn};
    neighbor {peerAddress} as {peerAsn};
    bfd yes;
"""

# Template for regular AS peering with RS (without rs client)
MbgpFileTemplates["client_mbgp_peer"] = """
    ipv4;
    local {localAddress} as {localAsn};
    neighbor {peerAddress} as {peerAsn};
    bfd yes;
"""

# Template for standard BGP peer without filtering
MbgpFileTemplates["mbgp_peer"] = """
    ipv4;
    local {localAddress} as {localAsn};
    neighbor {peerAddress} as {peerAsn};
    bfd yes;
"""

# Template for BFD configuration
MbgpFileTemplates["bfd_mbgp_peer"] = """
    interface "{interface_name}" {{
        min rx interval 50 ms;
        min tx interval 50 ms;
        multiplier 3;
    }};
"""


class PeerRelationship(Enum):
    Provider = "Provider"
    Peer = "Peer"
    Unfiltered = "Unfiltered"

class Mbgp(Layer, Graphable):
    def __init__(self):
        super().__init__()
        self.__peerings = {}
        self.__rs_peers = []
        self.addDependency('Routing', False, False)

    def addRsPeer(self, ix: int, peer: int) -> Mbgp:
        """Setup RS peering for a single AS in a simplified configuration."""
        assert (ix, peer) not in self.__rs_peers, '{} already peered with RS at IX{}'.format(peer, ix)
        self.__rs_peers.append((ix, peer))
        return self
    
    def addRsPeers(self, ix: int, peers: List[int]) -> Mbgp:
        """
        Setup RS peering for multiple ASes at once.
        
        @param ix IXP id.
        @param peers List of participant ASNs.
        
        @throws AssertionError if some peering already exist.
        
        @returns self, for chaining API calls.
        """
        for peer in peers:
            self.addRsPeer(ix, peer)
        return self

    def addPrivatePeering(self, ix: int, a: int, b: int, abRelationship: PeerRelationship = PeerRelationship.Unfiltered) -> Mbgp:
        """Setup private peering between two ASes in a simplified manner."""
        assert (ix, a, b) not in self.__peerings, '{} <-> {} already peered at IX{}'.format(a, b, ix)
        self.__peerings[(ix, a, b)] = abRelationship
        return self
        
    def addPrivatePeerings(self, ix: int, a_asns: List[int], b_asns: List[int], abRelationship: PeerRelationship = PeerRelationship.Peer) -> Mbgp:
        """!
        @brief Setup private peering between two sets of ASes in IX.

        @param ix IXP id.
        @param a_asns First set of ASNs.
        @param b_asns Second set of ASNs.
        @param abRelationship (optional) A and B's relationship. If set to
        PeerRelationship.Provider, A will export everything to B, if set to
        PeerRelationship.Peer, A will only export own and customer prefixes to
        B. Default to Peer.

        @throws AssertionError if peering already exist.

        @returns self, for chaining API calls.
        """
        for a in a_asns:
            for b in b_asns:
                self.addPrivatePeering(ix, a, b, abRelationship)

        return self

    def getPrivatePeerings(self) -> Dict[Tuple[int, int, int], PeerRelationship]:
        """!
        @brief Get private peerings.

        @returns dict, where key is tuple of (ix, asnA, asnB) and value is peering relationship.
        """
        return self.__peerings
        
    def setupInternalPeering(self, emulator: Emulator) -> None:
        """
        Set up internal MBGP peering (similar to iBGP) between routers within the same AS.
        Creates a full mesh of MBGP connections using loopback addresses.
        """
        reg = emulator.getRegistry()
        base = reg.get('seedemu', 'layer', 'Base')
        
        # Get list of ASes to configure internal MBGP for
        asns = base.getAsns()
        masked_asns = getattr(self, '_Mbgp__masked', set())
        
        for asn in asns:
            if asn in masked_asns:
                continue
                
            self._log(f'Setting up internal MBGP peering for AS{asn}...')
            routers = ScopedRegistry(str(asn), reg).getByType('rnode')
            
            # For each router, set up connections to all other routers
            for local_router in routers:
                self._log(f'Setting up internal MBGP on AS{asn}/{local_router.getName()}...')
                
                for remote_router in routers:
                    if local_router == remote_router:
                        continue
                    
                    local_addr = local_router.getLoopbackAddress()
                    remote_addr = remote_router.getLoopbackAddress()
                    
                    if not local_addr or not remote_addr:
                        self._log(f'Warning: Missing loopback address for AS{asn}')
                        continue
                    
                    # Add the internal MBGP peering configuration
                    local_router.addProtocol('mbgp', f'internal_{remote_router.getName()}', """\n    ipv4;\n    local {local_addr} as {asn}; \n    neighbor {remote_addr} as {asn}; \n    bfd yes; \n""".format(local_addr=local_addr, remote_addr=remote_addr, asn=asn))
                    
                    self._log(f'Added internal MBGP peering: {local_addr} <-> {remote_addr} (AS{asn})')

    def maskAsn(self, asn: int) -> Mbgp:
        """
        Mask an AS to exclude it from internal MBGP peering.
        
        @param asn AS to mask.
        @returns self, for chaining API calls.
        """
        if not hasattr(self, '_Mbgp__masked'):
            self._Mbgp__masked = set()
        
        self._Mbgp__masked.add(asn)
        return self
        
    def __createPeer(self, nodeA: Router, nodeB: Router, addrA: str, addrB: str, rel: PeerRelationship) -> None:
        rsNode: Router = None
        routerA: Router = None
        routerB: Router = None
        interfaceA: str = None
        interfaceB: str = None
        rsInterface: str = None

        # Identify the types of nodes involved (Route Server or Router)
        for node in [nodeA, nodeB]:
            if node.getRole() == NodeRole.RouteServer:
                rsNode = node
                continue
            
            if routerA is None:
                routerA = node
            elif routerB is None:
                routerB = node        

            node.addTablePipe('t_direct', 'master4')

        assert routerA is not None, 'Both nodes are RS nodes. Cannot setup peering.'
        
        # For RS peering, we only have routerA (routerB will be None)
        if rsNode is not None:
            # RS peering case
            assert routerB is None, 'RS peering should only have one router'
            
            # Find interface for routerA
            for iface in routerA.getInterfaces():
                if iface.getAddress() == addrB:  # Note: addrB is routerA's address when RS peering
                    interfaceA = iface.getNet().getName()
                    break
            
            # Find interface for RS
            for iface in rsNode.getInterfaces():
                if iface.getAddress() == addrA:  # addrA is RS's address
                    rsInterface = iface.getNet().getName()
                    break
            
            assert interfaceA is not None, 'Unable to determine interface name for router.'
            assert rsInterface is not None, 'Unable to determine interface name for RS.'
            
            # Maintain BFD interfaces set for both RS and client
            if not hasattr(routerA, "_bfd_interfaces"):
                routerA._bfd_interfaces = set()
            if not hasattr(rsNode, "_bfd_interfaces"):
                rsNode._bfd_interfaces = set()
                
            routerA._bfd_interfaces.add(interfaceA)
            rsNode._bfd_interfaces.add(rsInterface)
            
            # Print debug info
            print(f"RS Peering - Router (ASN {routerA.getAsn()}) - Interface: {interfaceA} - RS: {addrA}")
            print(f"RS (ASN {rsNode.getAsn()}) - Interface: {rsInterface}")
            
            # Add RS peering protocols
            # RS side uses rs_mbgp_peer template (with rs client)
            rsNode.addProtocol('mbgp', f'p_as{routerA.getAsn()}', MbgpFileTemplates["rs_mbgp_peer"].format(
                localAddress=addrA,
                localAsn=rsNode.getAsn(),
                peerAddress=addrB,
                peerAsn=routerA.getAsn()
            ))

            # Client side uses client_mbgp_peer template (without rs client)
            routerA.addProtocol('mbgp', f'p_rs{rsNode.getAsn()}', MbgpFileTemplates["client_mbgp_peer"].format(
                localAddress=addrB,
                localAsn=routerA.getAsn(),
                peerAddress=addrA,
                peerAsn=rsNode.getAsn()
            ))
            
        else:
            # Private peering case
            assert routerB is not None, 'Private peering requires two routers'
            assert routerA != routerB, 'Cannot peer with oneself.'
            
            # Extract interface names for both routers
            for iface in routerA.getInterfaces():
                if iface.getAddress() == addrA:
                    interfaceA = iface.getNet().getName()
                    break

            for iface in routerB.getInterfaces():
                if iface.getAddress() == addrB:
                    interfaceB = iface.getNet().getName()
                    break

            assert interfaceA is not None and interfaceB is not None, 'Unable to determine interface names.'

            # Print debug info
            print(f"Router A (ASN {routerA.getAsn()}) - Interface: {interfaceA} - Peer: {addrB}")
            print(f"Router B (ASN {routerB.getAsn()}) - Interface: {interfaceB} - Peer: {addrA}")

            # Maintain BFD interfaces sets
            if not hasattr(routerA, "_bfd_interfaces"):
                routerA._bfd_interfaces = set()
            if not hasattr(routerB, "_bfd_interfaces"):
                routerB._bfd_interfaces = set()

            routerA._bfd_interfaces.add(interfaceA)
            routerB._bfd_interfaces.add(interfaceB)

            # Add private peering protocols
            routerA.addProtocol('mbgp', f'x_as{routerB.getAsn()}', MbgpFileTemplates["mbgp_peer"].format(
                localAddress=addrA,
                localAsn=routerA.getAsn(),
                peerAddress=addrB,
                peerAsn=routerB.getAsn()
            ))

            routerB.addProtocol('mbgp', f'x_as{routerA.getAsn()}', MbgpFileTemplates["mbgp_peer"].format(
                localAddress=addrB,
                localAsn=routerB.getAsn(),
                peerAddress=addrA,
                peerAsn=routerA.getAsn()
            ))
            
    def configure(self, emulator: Emulator) -> None:
        reg = emulator.getRegistry()

        # Configure RS peerings
        for (ix, peer) in self.__rs_peers:
            ix_reg = ScopedRegistry('ix', reg)
            p_reg = ScopedRegistry(str(peer), reg)

            ix_net: Network = ix_reg.get('net', f'ix{ix}')
            ix_rs: Router = ix_reg.get('rs', f'ix{ix}')
            rs_ifs = ix_rs.getInterfaces()
            assert len(rs_ifs) == 1, f"IX{ix} RS has {len(rs_ifs)} interfaces, expected 1."
            rs_if = rs_ifs[0]

            p_rnodes: List[Router] = p_reg.getByType('rnode')
            p_ixnode: Router = None
            p_ixif: Interface = None

            for node in p_rnodes:
                if p_ixnode:
                    break
                for iface in node.getInterfaces():
                    if iface.getNet() == ix_net:
                        p_ixnode = node
                        p_ixif = iface
                        break

            assert p_ixnode, f"Cannot resolve peering: AS{peer} not in IX{ix}."
            self._log(f"Adding RS peering: {rs_if.getAddress()} as {ix} (RS) <-> {p_ixif.getAddress()} as {peer}")

            self.__createPeer(ix_rs, p_ixnode, rs_if.getAddress(), p_ixif.getAddress(), PeerRelationship.Peer)

        # Configure private peerings
        for (ix, a, b), rel in self.__peerings.items():
            ix_reg = ScopedRegistry('ix', reg)
            a_reg = ScopedRegistry(str(a), reg)
            b_reg = ScopedRegistry(str(b), reg)

            ix_net: Network = ix_reg.get('net', f'ix{ix}')

            a_ixnode: Router = None
            b_ixnode: Router = None
            a_addr: str = None
            b_addr: str = None

            # Find router and interface for AS A
            for node in a_reg.getByType('rnode'):
                for iface in node.getInterfaces():
                    if iface.getNet() == ix_net:
                        a_ixnode = node
                        a_addr = iface.getAddress()
                        break
                if a_ixnode:
                    break

            # Find router and interface for AS B
            for node in b_reg.getByType('rnode'):
                for iface in node.getInterfaces():
                    if iface.getNet() == ix_net:
                        b_ixnode = node
                        b_addr = iface.getAddress()
                        break
                if b_ixnode:
                    break

            assert a_ixnode and b_ixnode, f"Cannot resolve private peering: AS{a} <-> AS{b} at IX{ix}."
            self._log(f"Adding private peering: {a_addr} as {a} <-({rel})-> {b_addr} as {b}")

            self.__createPeer(a_ixnode, b_ixnode, a_addr, b_addr, rel)
            
        self.setupInternalPeering(emulator)
        
        # Now, generate a single BFD configuration per router (including RS nodes)
        for ((scope, type, name), obj) in reg.getAll().items():
            if type in ["rnode", "rs"] and isinstance(obj, Router):  # Include both router nodes and RS nodes
                router = obj
                if hasattr(router, "_bfd_interfaces") and router._bfd_interfaces:
                    interfaces_config = "\n".join(
                        MbgpFileTemplates["bfd_mbgp_peer"].format(interface_name=iface)
                        for iface in router._bfd_interfaces
                    )

                    router.addProtocol("bfd", "", interfaces_config)

    def getName(self) -> str:
        return "Mbgp"
        
    def render(self, emulator: Emulator) -> None:
        pass