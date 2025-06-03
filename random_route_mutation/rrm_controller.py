from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.topology.api import get_switch, get_link
from ryu.topology import event
from ryu.lib.packet import packet, ethernet
import networkx as nx
import random
import threading
import time

# --- Globals ---
mymacs = {}         # MAC → (dpid, port)
adjacency = {}      # adjacency[s1][s2] = port from s1 to s2
paths = []          # List of candidate paths (each is a list of DPIDs)
datapaths = {}      # DPID → datapath object

# --- Dijkstra (shortest path) ---
def get_path(src, dst, src_port, dst_port):
    # Find path using precomputed NetworkX graph
    if src not in adjacency or dst not in adjacency:
        return []
    try:
        path = nx.shortest_path(nx_graph(), src, dst)
    except Exception:
        return []
    # Build list of (dpid, in_port, out_port) for each hop
    hoplist = []
    in_port = src_port
    for u, v in zip(path[:-1], path[1:]):
        out_port = adjacency[u][v]
        hoplist.append((u, in_port, out_port))
        in_port = adjacency[v][u]
    hoplist.append((dst, in_port, dst_port))
    return hoplist

def nx_graph():
    G = nx.Graph()
    for u in adjacency:
        for v in adjacency[u]:
            G.add_edge(u, v)
    return G

class PeriodicRRMController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    def __init__(self, *args, **kwargs):
        super(PeriodicRRMController, self).__init__(*args, **kwargs)
        self.topology_api_app = self
        threading.Thread(target=self.rrm_thread, daemon=True).start()

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        dp = ev.msg.datapath
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER)]
        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(datapath=dp, priority=0, match=match, instructions=inst)
        dp.send_msg(mod)
        datapaths[dp.id] = dp
        print(f"[DPI] Registered switch {dp.id}")

    @set_ev_cls(event.EventSwitchEnter)
    def topology_handler(self, ev):
        switch_list = get_switch(self.topology_api_app, None)
        switches = [s.dp.id for s in switch_list]
        link_list = get_link(self.topology_api_app, None)
        # Build adjacency
        adjacency.clear()
        for s in switches:
            adjacency[s] = {}
        for link in link_list:
            src = link.src.dpid
            dst = link.dst.dpid
            port = link.src.port_no
            adjacency[src][dst] = port
        print(f"[Topology] Nodes={switches} Links={[ (l.src.dpid, l.dst.dpid) for l in link_list ]}")

        # Precompute all simple paths from s1 (1) to s5 (5)
        try:
            G = nx_graph()
            k = 5
            global paths
            paths = list(nx.all_simple_paths(G, source=1, target=5))
            print(f"[Path] Precomputed {len(paths)} paths from s1 to s5")
        except Exception as e:
            print("[Path] Path computation error:", e)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        dpid = dp.id
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        in_port = msg.match['in_port']
        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        # Ignore LLDP
        if eth.ethertype == 35020 or eth.ethertype == 34525:
            return
        src = eth.src
        dst = eth.dst

        # Global MAC learning
        if src not in mymacs:
            mymacs[src] = (dpid, in_port)
            print(f"[MAC] Learned {src} at switch {dpid}, port {in_port}")
        # Always flood if unknown dst (including ARP at startup)
        if dst not in mymacs:
            out_port = ofp.OFPP_FLOOD
        else:
            # Install path immediately for this src/dst
            src_sw, src_port = mymacs[src]
            dst_sw, dst_port = mymacs[dst]
            hoplist = get_path(src_sw, dst_sw, src_port, dst_port)
            if hoplist:
                self.install_path(hoplist, src, dst)
                out_port = hoplist[0][2]
                print(f"[FLOW] Path installed {hoplist}")
            else:
                out_port = ofp.OFPP_FLOOD
        actions = [parser.OFPActionOutput(out_port)]
        data = msg.data if msg.buffer_id == ofp.OFP_NO_BUFFER else None
        out = parser.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id, in_port=in_port, actions=actions, data=data)
        dp.send_msg(out)

    def install_path(self, hoplist, src_mac, dst_mac):
        for dpid, in_port, out_port in hoplist:
            dp = datapaths.get(dpid)
            if dp is None:
                continue
            parser = dp.ofproto_parser
            ofp = dp.ofproto
            match = parser.OFPMatch(in_port=in_port, eth_src=src_mac, eth_dst=dst_mac)
            actions = [parser.OFPActionOutput(out_port)]
            inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
            mod = parser.OFPFlowMod(datapath=dp, priority=10, match=match, instructions=inst,
                                    idle_timeout=120, hard_timeout=0)
            dp.send_msg(mod)

    def rrm_thread(self):
        while True:
            time.sleep(120)  # 2 minutes
            src_mac = "00:00:00:00:00:01"
            dst_mac = "00:00:00:00:00:02"
            if src_mac not in mymacs or dst_mac not in mymacs:
                print("[RRM] Waiting for MACs to be learned.")
                continue
            src_sw, src_port = mymacs[src_mac]
            dst_sw, dst_port = mymacs[dst_mac]
            if not paths:
                print("[RRM] No paths to mutate!")
                continue
            path = random.choice(paths)
            print(f"[RRM] Random path selected: {path}")
            hoplist = []
            in_port = src_port
            for u, v in zip(path[:-1], path[1:]):
                out_port = adjacency[u][v]
                hoplist.append((u, in_port, out_port))
                in_port = adjacency[v][u]
            hoplist.append((dst_sw, in_port, dst_port))
            self.install_path(hoplist, src_mac, dst_mac)
            print(f"[RRM] Path mutated: {hoplist}")

