from __future__ import annotations
from .Routing import Router
from seedemu.core import Registry, ScopedRegistry, Network, Interface, Graphable, Emulator, Layer
from seedemu.core.enums import NodeRole
from typing import Tuple, List, Dict
from enum import Enum

MbgpFileTemplates: Dict[str, str] = {}

# Define the template for a Route Server (RS) peering in BIRD
MbgpFileTemplates["rs_mbgp_peer"] = """
    ipv4;
    rs client;
    local {localAddress} as {localAsn};
    neighbor {peerAddress} as {peerAsn};
    bfd yes;
"""

# Define the template for a standard BGP peer without filtering
MbgpFileTemplates["mbgp_peer"] = """
    ipv4;
    local {localAddress} as {localAsn};
    neighbor {peerAddress} as {peerAsn};
    bfd yes;
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

    def addPrivatePeering(self, ix: int, a: int, b: int, abRelationship: PeerRelationship = PeerRelationship.Unfiltered) -> Mbgp:
        """Setup private peering between two ASes in a simplified manner."""
        assert (ix, a, b) not in self.__peerings, '{} <-> {} already peered at IX{}'.format(a, b, ix)
        self.__peerings[(ix, a, b)] = abRelationship
        return self

    def __createPeer(self, nodeA: Router, nodeB: Router, addrA: str, addrB: str, rel: PeerRelationship) -> None:
        rsNode, routerA, routerB = None, None, None

        # Identify the types of nodes involved (Route Server or Router)
        for node in [nodeA, nodeB]:
            if node.getRole() == NodeRole.RouteServer:
                rsNode = node
            else:
                if routerA is None:
                    routerA = node
                else:
                    routerB = node         
            # since mbgp coded to use main RTB , we need to pipe the local nets to the main rotue - I'll change it later
            node.addTablePipe('t_direct', 'master4')


        # Route Server Peering: if there is an rsNode and only one routerNode (either routerA or routerB)
        if rsNode and routerA:
            # Configure RS peering between rsNode and routerA
            rsNode.addProtocol('mbgp', 'p_as{}'.format(routerA.getAsn()), MbgpFileTemplates["rs_mbgp_peer"].format(
                localAddress=addrA,
                localAsn=rsNode.getAsn(),
                peerAddress=addrB,
                peerAsn=routerA.getAsn()
            ))

            routerA.addProtocol('mbgp', 'p_rs{}'.format(rsNode.getAsn()), MbgpFileTemplates["rs_mbgp_peer"].format(
                localAddress=addrB,
                localAsn=routerA.getAsn(),
                peerAddress=addrA,
                peerAsn=rsNode.getAsn()
            ))

        # Private Peering: if there are two routers (routerA and routerB) and no rsNode
        elif routerA and routerB:
            # Configure private peering between routerA and routerB
            routerA.addProtocol('mbgp', 'x_as{}'.format(routerB.getAsn()), MbgpFileTemplates["mbgp_peer"].format(
                localAddress=addrA,
                localAsn=routerA.getAsn(),
                peerAddress=addrB,
                peerAsn=routerB.getAsn()
            ))

            routerB.addProtocol('mbgp', 'x_as{}'.format(routerA.getAsn()), MbgpFileTemplates["mbgp_peer"].format(
                localAddress=addrB,
                localAsn=routerB.getAsn(),
                peerAddress=addrA,
                peerAsn=routerA.getAsn()
            ))
        else:
            raise AssertionError("Invalid configuration: cannot determine Route Server or Router nodes correctly.")



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


    def getName(self) -> str:
        return "Mbgp"
        
    def render(self, emulator: Emulator) -> None:
        pass
