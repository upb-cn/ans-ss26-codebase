"""
 Copyright (c) 2026 Computer Networks Group @ UPB

 Permission is hereby granted, free of charge, to any person obtaining a copy of
 this software and associated documentation files (the "Software"), to deal in
 the Software without restriction, including without limitation the rights to
 use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
 the Software, and to permit persons to whom the Software is furnished to do so,
 subject to the following conditions:

 The above copyright notice and this permission notice shall be included in all
 copies or substantial portions of the Software.

 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
 COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
 IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 """

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet, ether_types, arp, ipv4

class LearningSwitch(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(LearningSwitch, self).__init__(*args, **kwargs)
        # Router port MACs assumed by the controller
        self.port_to_own_mac = {
            1: "00:00:00:00:01:01",
            2: "00:00:00:00:01:02",
            3: "00:00:00:00:01:03"
        }
        # Router port (gateways) IP addresses assumed by the controller
        self.port_to_own_ip = {
            1: "10.0.1.1",
            2: "10.0.2.1",
            3: "192.168.1.1"
        }
        self.arp_cache = {} # safe linking between: IP -> MAC

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        
        # ev.msg is the actual OpenFlow message object containing the switch data
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # empty match rule => match everything
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath, 0, match, actions)

    # Add a flow entry to the flow-table
    def add_flow(self, datapath, priority, match, actions, buffer_id=None):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # Construct flow_mod message and send it
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        if buffer_id:
            mod = parser.OFPFlowMod(datapath=datapath, buffer_id=buffer_id, 
                                priority=priority, match=match,
                                instructions=inst)
        else:
            mod = parser.OFPFlowMod(datapath=datapath, priority=priority,
                                    match=match, instructions=inst)
        # Sends the constructed message over the network to the switch
        datapath.send_msg(mod)

    # Listens for packets that the switch sends to the controller (table-misses)
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']

        # Identify which device sent this packet
        dpi = datapath.id

        #analyze the packet
        pkt = packet.Packer(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]

        if eth.ethertype == ether_types.ETH_TYPE_LLDP:
            #ignor lldp
            return

        arp_pkt = pkt.get_protocol(arp.arp)
        ipv4_pkt = pkt.get_protocol(ipv4.ipv4)

        if dpid == 3:
            if arp_pkt:
                self.handle_arp(datapath, in_port, eth, arp_pkt, parser, ofproto)
                return
    
            if ipv4_pkt:
                self.handle_ipv4(datapath, in_port, eth, ipv4_pkt, parser, ofproto, msg)
                return
        elif dpid in [1,2]:
            # TODO: add MAC learning and forwarding logic here PERSON 1 / ZAIN
            pass
    
    def handle_arp(self, datapath, in_port, eth, arp_pkt, parser, ofproto):
        # ip to mac => cache
        self.arp_cache[arp_pkt.src_ip] = arp_pkt.src_mac
        #validate arp requests
        if arp_pkt.opcode != arp.ARP_REQUEST:
            return

        target_ip = arp_pkt.dst_ip
        router_ip = self.port_to_own_ip.get(in_port)

        if target_ip == router_ip:
            router_mac = self.port_to_own_mac[in_port]
            
            reply_pkt = packet.Packet()

            # reply eth header
            eth_reply = ethernet.ethernet(
                dst=eth.src,
                src=router_mac,
                ethertype=ether_types.ETH_TYPE_ARP
            )
            reply_pkt.add_protocol(eth_reply)
            # reply ARP Header
            arp_reply = arp.arp(
                hwtype = 1,
                proto=0x0800,
                hlen=6,
                plen=4,
                opcode=arp.ARP_REPLY,
                src_mac=router_mac,
                src_ip=router_ip,
                dst_mac=arp_pkt.src_mac,
                dst_ip=arp_pkt.src_ip
            )
            reply_pkt.add_protocol(arp_reply)

            # transform the packet to a bytestream
            reply_pkt.serialize()

            actions = [parser.OFPActionOutput(in_port)]

            out = parser.OFPPacketOut(
                datapath=datapath,
                buffer_id=ofproto.OFP_NO_BUFFER,
                in_port=ofproto.OFPP_CONTROLLER,
                actions=actions,
                data=reply_pkt.data
            )
            datapath.send_msg(out)

    def handle_ipv4(self, datapath, in_port, eth, ipv4_pkt, parser, ofproto, msg): 
        dst_ip = ipv4_pkt.dst

        # catch if its directet towards the router
        if dst_ip in self.port_to_own_ip.values():
            #TODO: ICMP-Reply handling PERSON 3 / AMIN
            return

        #determine out-port
        out_port = None
        for port, ip in self.port_to_own_ip.items():
            if dst_ip.rsplit('.', 1)[0] == ip.rsplit('.', 1)[0]:
                out_port = port
                break
        
        if out_port is None:
            return 

        dst_mac = self.arp_cache.get(dst_ip)

        if not dst_mac:
            return
        #TODO: Check traffix beteween ext PERSON 3 / AMIN
        router_mac_out = self.port_to_own_mac[out_port]

        match = parser.OFPMatch(eth_type=0x0800, ipv4_dst=dst_ip)

        actions = [
            # source mac -> outport
            parser.OFPActionSetField(eth_src=router_mac_out),
            # destmac -> receiver
            parser.OFPActionSetField(eth_dst=dst_mac),
            parser.OFPActionDecNwTtl(),
            parser.OFPActionOutput(out_port)
        ]

        self.add_flow(datapath, 10, match, actions, msg.buffer_id)

        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            out = parser.OFPPacketOut(
                datapath=datapath,
                buffer_id=msg.buffer_id,
                in_port=in_port,
                actions=actions,
                data=msg.data
            )
        datapath.send_msg(out)
