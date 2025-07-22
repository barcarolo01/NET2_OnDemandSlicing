#!/usr/bin/env python3

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.app.wsgi import WSGIApplication
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER, set_ev_cls
from rest_api import *
import subprocess


# ============================== Global variables ============================== #

ASSISTANCE_PRIORITY = 1234
installed_flows_for_assistance = []
INSTANCE_NAME = 'slicing_controller'    # Expose this instance to REST api controller

# ============================== Controller ============================== #
class SlicesController(app_manager.RyuApp):
    IPs={}
    is_link_down=False

    OFP_VERSION = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {
        'wsgi': WSGIApplication
    }

    # Constructor
    def __init__(self, *args, **kwargs):
        super(SlicesController, self).__init__(*args, **kwargs)
        wsgi = kwargs['wsgi']
        wsgi.register(RestController, {INSTANCE_NAME: self})
        self.datapaths = {}
        self.port_states = {
            (2, 5): True,  # s2-eth5
            (4, 3): True   # s4-eth3
        }
        self.link_down_logged = False

        # Reading hosts IP addresses from config file
        with open('config_files/hosts.json', 'r') as file:
            self.IPs = json.load(file)

    # Add Flow Method
    def add_flow(self, dp, priority, match, actions):
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(
            datapath=dp,
            priority=priority,
            match=match,
            instructions=inst
        )
        dp.send_msg(mod)

        if priority == ASSISTANCE_PRIORITY:
            installed_flows_for_assistance.append((dp, priority, match))


    # Remove Flow Method
    def delete_flow(self, dp, match, priority = None):
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        kwargs = {
            'datapath': dp,
            'command': ofp.OFPFC_DELETE,
            'out_port': ofp.OFPP_ANY,
            'out_group': ofp.OFPG_ANY,
            'match': match
        }

        mod = parser.OFPFlowMod(**kwargs)
        dp.send_msg(mod)


    # This method is called every time a switch is connected to the ryu controller
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        dp = ev.msg.datapath
        self.datapaths[dp.id] = dp
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        req = parser.OFPPortDescStatsRequest(dp, 0)
        self.logger.info("Switch connected: s%d", dp.id)

    # This method is called when a link fails / is recovered
    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def port_status_handler(self, ev):
        msg = ev.msg
        dpid = msg.datapath.id
        port_no = msg.desc.port_no
        state = msg.desc.state
        ofproto = msg.datapath.ofproto

        link_down = bool(state & ofproto.OFPPS_LINK_DOWN)

        # If s2-eth5 <--> s4-eth3 is down
        if (dpid == 2 and port_no == 5) or (dpid == 4 and port_no == 3):
            if link_down and not self.link_down_logged:
                self.logger.info("s2-eth5 <--> s4-eth3 LINK DOWN")
                self.is_link_down = True
                self.link_down_logged = True
                if Slices["Telesurgery"]:
                    self.remove_Telesurgery_slice() # Remove the old slice
                    self.add_Telesurgery_slice()
            elif not link_down and self.link_down_logged:
                self.logger.info("s2-eth5 <--> s4-eth3 LINK UP")
                self.is_link_down = False
                self.link_down_logged = False
                if Slices["Telesurgery"]:
                    self.remove_Telesurgery_slice() # Remove the old slice
                    self.add_Telesurgery_slice()


# ============================== ACTIVATION / DEACTIVATION Methods ============================== #

# -------------------- GUEST --------------------
    def add_Guest_slice(self):
        #subprocess.run(["sudo", "./scripts/add_guest_queue.sh"], check=True)
        for dpid, dp in self.datapaths.items():
            parser = dp.ofproto_parser
            if dpid == 1:
                for ip_guest, (port_guest, queue_nr) in {
                    self.IPs['h1']: (1,1),
                    self.IPs['h2']: (2,2)
                }.items():
                    # Allowing traffic from/to Internet
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip_guest)
                    self.add_flow(dp, 2, match, [parser.OFPActionSetQueue(queue_nr),parser.OFPActionOutput(3)])
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_dst=ip_guest)
                    self.add_flow(dp, 2, match, [parser.OFPActionSetQueue(queue_nr),parser.OFPActionOutput(port_guest)])

                    # Allowing communication with nat0
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip_guest,ipv4_dst='172.64.255.254')
                    self.add_flow(dp, 4, match, [parser.OFPActionSetQueue(queue_nr),parser.OFPActionOutput(3)])

                    # Explicitely drop traffic from guest slice to other devices of network
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip_guest,ipv4_dst='172.64.0.0/16')
                    self.add_flow(dp, 3, match, [])

        Slices["Guest"] = True
        self.logger.info("Guest slice ENABLED")

    def remove_Guest_slice(self):
        for dpid, dp in self.datapaths.items():
            parser = dp.ofproto_parser
            if dpid == 1:
                for ip_guest in {"172.64.100.1", "172.64.100.2"}:
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_dst=ip_guest)
                    self.delete_flow(dp, match)
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip_guest)
                    self.delete_flow(dp, match)

        Slices["Guest"] = False
        self.logger.info("Guest slice DISABLED")

# -------------------- IoT --------------------
    def add_IoT_slice(self):        
        for dpid, dp in self.datapaths.items():
            parser = dp.ofproto_parser
            iot_hosts = {
                self.IPs['h3']: (1,1),
                self.IPs['h4']: (2,2)
            }
            if dpid == 2:  # s2
                # Allowing communication between IoT devices
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h3'],ipv4_dst=self.IPs['h4'])
                self.add_flow(dp, 90, match, [parser.OFPActionSetQueue(2),parser.OFPActionOutput(2)])
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h4'],ipv4_dst=self.IPs['h3'])
                self.add_flow(dp, 90, match, [parser.OFPActionSetQueue(1),parser.OFPActionOutput(1)])

                for ip, (port, queue_nr) in iot_hosts.items():
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip,ipv4_dst=self.IPs['h10'])
                    self.add_flow(dp, 90, match, [parser.OFPActionSetQueue(queue_nr),parser.OFPActionOutput(6)])

                    match_rev = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h10'],ipv4_dst=ip)
                    #self.add_flow(dp, 90, match_rev, [parser.OFPActionSetQueue(100+queue_nr),parser.OFPActionOutput(port)])
                    self.add_flow(dp, 90, match_rev, [parser.OFPActionOutput(port)])

            elif dpid == 5: # s5
                for ip, (port, queue_nr) in iot_hosts.items():
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip, ipv4_dst=self.IPs['h10'])
                    self.add_flow(dp, 90, match, [parser.OFPActionOutput(4)])

                    match_rev = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h10'], ipv4_dst=ip)
                    self.add_flow(dp, 90, match_rev, [parser.OFPActionOutput(3)])


            elif dpid == 4:  # s4
                # From IoT hosts to h7 via s2 port 4
                for ip, (port, queue_nr) in iot_hosts.items():
                    # Forward from s2 (port 3) to h11 (port 1) via queue
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip, ipv4_dst=self.IPs['h10'])
                    self.add_flow(dp, 90, match, [parser.OFPActionOutput(1)])

                    # Reverse path: from h11 to IoT host, no need for queues
                    match_rev = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h10'], ipv4_dst=ip)
                    self.add_flow(dp, 90, match_rev, [parser.OFPActionSetQueue(100+queue_nr),parser.OFPActionOutput(4)])

        Slices["IoT"]  = True
        self.logger.info("IoT slice ENABLED")
            
    def remove_IoT_slice(self):
        self.logger.info("Removing IoT slice")
        for dpid, dp in self.datapaths.items():
            parser = dp.ofproto_parser
            iot_hosts = {
                self.IPs['h3']: 1,
                self.IPs['h4']: 2
            }
            if dpid == 2:  # s2
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h3'],ipv4_dst=self.IPs['h4'])
                self.delete_flow(dp, match)
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h4'],ipv4_dst=self.IPs['h3'])
                self.delete_flow(dp, match)

                for ip, port in iot_hosts.items():
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip,ipv4_dst=self.IPs['h10'])
                    self.delete_flow(dp, match)

                    match_rev = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h10'],ipv4_dst=ip)
                    self.delete_flow(dp, match_rev)

            elif dpid == 5: # s5
                for ip, queue_id in iot_hosts.items():

                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip, ipv4_dst=self.IPs['h10'])
                    self.delete_flow(dp, match)
                    match_rev = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h10'], ipv4_dst=ip)
                    self.delete_flow(dp, match_rev)


            elif dpid == 4:  # s4
                for ip, queue_id in iot_hosts.items():
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip, ipv4_dst=self.IPs['h10'])
                    self.delete_flow(dp, match)
                    match_rev = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h10'], ipv4_dst=ip)
                    self.delete_flow(dp, match_rev)

        Slices["IoT"]  = False
        self.logger.info("IoT slice DISABLED")
    
# -------------------- Office --------------------
    def add_Office_slice(self):
        for dpid, dp in self.datapaths.items():
            parser = dp.ofproto_parser
            if dpid == 3: # s3
                # Office <--> Office traffic                    
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h6'],ipv4_dst=self.IPs['h7'])
                self.add_flow(dp, 4, match, [parser.OFPActionSetQueue(2),parser.OFPActionOutput(2)])
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h7'],ipv4_dst=self.IPs['h6'])
                self.add_flow(dp, 4, match, [parser.OFPActionSetQueue(1),parser.OFPActionOutput(1)])

                for ip_office, (port_office,queue_nr) in {
                    self.IPs['h6']: (1,1),
                    self.IPs['h7']: (2,2)
                }.items():
                    # Internet -> Office traffic                    
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_dst=ip_office)
                    self.add_flow(dp, 2, match, [parser.OFPActionOutput(port_office)])

                    # Office -> Internet traffic
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip_office)
                    self.add_flow(dp, 2, match, [parser.OFPActionSetQueue(queue_nr),parser.OFPActionOutput(3)])

            
            elif dpid == 1: # s1
                for ip_office, (port_office,queue_nr) in {
                    self.IPs['h6']: (1,1),
                    self.IPs['h7']: (2,2)
                }.items():
                    # Office -> Internet traffic
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip_office)
                    self.add_flow(dp, 2, match, [parser.OFPActionOutput(3)])

                # Internet -> Office traffic
                match = parser.OFPMatch(eth_type=0x0800,ipv4_dst=self.IPs['h6'])
                self.add_flow(dp, 2, match, [parser.OFPActionSetQueue(6),parser.OFPActionOutput(4)])
                match = parser.OFPMatch(eth_type=0x0800,ipv4_dst=self.IPs['h7'])
                self.add_flow(dp, 2, match, [parser.OFPActionSetQueue(7),parser.OFPActionOutput(4)])

        Slices["Office"] = True
        self.logger.info("Office slice ENABLED")
                  
    def remove_Office_slice(self):
        for dpid, dp in self.datapaths.items():
            parser = dp.ofproto_parser
            if dpid == 3: # s3
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h6'],ipv4_dst=self.IPs['h7'])
                self.delete_flow(dp, match)
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h7'],ipv4_dst=self.IPs['h6'])
                self.delete_flow(dp, match)
                for ip_office, port_office in {
                    self.IPs['h6']: 1,
                    self.IPs['h7']: 2
                }.items():
                    # Office -> Internet traffic
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_dst=ip_office)
                    self.delete_flow(dp, match)

                    # Internet -> Office traffic
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip_office)
                    self.delete_flow(dp, match)

                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip_office,ipv4_dst='172.64.255.254')
                    self.delete_flow(dp, match)
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip_office,ipv4_dst='172.64.0.0/16')
                    self.delete_flow(dp, match)
            
            elif dpid == 1: # s1
                for ip_office, port_office in {
                    self.IPs['h6']: 1,
                    self.IPs['h7']: 2
                }.items():
                    # Office -> Internet traffic
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip_office)
                    self.delete_flow(dp, match)
                    
                    # Internet -> Office traffic
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_dst=ip_office)
                    self.delete_flow(dp, match)
        Slices["Office"] = False
        self.logger.info("Office slice DISABLED")

# -------------------- Assistance --------------------
    def add_Assistance_slice(self,body):
        ip_IT = self.IPs['h9']
        global ASSISTANCE_PRIORITY
        for dpid, dp in self.datapaths.items():
            parser = dp.ofproto_parser
            # Allowing communication IT <--> h3
            if "h3" in body:
                if dpid == 5:
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip_IT,ipv4_dst=self.IPs['h3'])
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionSetQueue(903),parser.OFPActionOutput(3)])
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h3'],ipv4_dst=ip_IT)
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionOutput(2)])
                if dpid == 2:
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip_IT,ipv4_dst=self.IPs['h3'])
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionOutput(1)])
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h3'],ipv4_dst=ip_IT)
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionSetQueue(903),parser.OFPActionOutput(6)])

            # Allowing communication IT <--> h4
            if "h4" in body:
                if dpid == 5:
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip_IT,ipv4_dst=self.IPs['h4'])
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionSetQueue(904),parser.OFPActionOutput(3)])
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h4'],ipv4_dst=ip_IT)
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionOutput(2)])
                if dpid == 2:
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip_IT,ipv4_dst=self.IPs['h4'])
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionOutput(2)])
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h4'],ipv4_dst=ip_IT)
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionSetQueue(904),parser.OFPActionOutput(6)])

            # Allowing communication IT <--> h5
            if "h5" in body:
                if dpid == 5:
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip_IT,ipv4_dst=self.IPs['h5'])
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionSetQueue(905),parser.OFPActionOutput(3)])
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h5'],ipv4_dst=ip_IT)
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionOutput(2)])
                if dpid == 2:
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip_IT,ipv4_dst=self.IPs['h5'])
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionOutput(3)])
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h5'],ipv4_dst=ip_IT)
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionSetQueue(905),parser.OFPActionOutput(6)])

            # Allowing communication IT <--> h6
            if "h6" in body:
                if dpid == 5:
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip_IT,ipv4_dst=self.IPs['h6'])
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionSetQueue(906),parser.OFPActionOutput(3)])
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h6'],ipv4_dst=ip_IT)
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionOutput(2)])
                if dpid == 2:
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip_IT,ipv4_dst=self.IPs['h6'])
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionOutput(4)])
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h6'],ipv4_dst=ip_IT)
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionOutput(6)])
                if dpid == 3:
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip_IT,ipv4_dst=self.IPs['h6'])
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionOutput(1)])
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h6'],ipv4_dst=ip_IT)
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionSetQueue(906),parser.OFPActionOutput(4)])

            # Allowing communication IT <--> h7
            if "h7" in body:
                if dpid == 5:
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip_IT,ipv4_dst=self.IPs['h7'])
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionSetQueue(907),parser.OFPActionOutput(3)])
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h7'],ipv4_dst=ip_IT)
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionOutput(2)])
                if dpid == 2:
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip_IT,ipv4_dst=self.IPs['h7'])
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionOutput(4)])
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h7'],ipv4_dst=ip_IT)
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionOutput(6)])
                if dpid == 3:
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip_IT,ipv4_dst=self.IPs['h7'])
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionOutput(2)])
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h7'],ipv4_dst=ip_IT)
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionSetQueue(907),parser.OFPActionOutput(4)])

            # Allowing communication IT <--> h8
            if "h8" in body:
                if dpid == 5:
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip_IT,ipv4_dst=self.IPs['h8'])
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionSetQueue(908),parser.OFPActionOutput(1)])
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h8'],ipv4_dst=ip_IT)
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionSetQueue(908),parser.OFPActionOutput(2)])

            # Allowing communication IT <--> Datacenter (h10)
            if "h10" in body:
                if dpid == 5:
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip_IT,ipv4_dst=self.IPs['h10'])
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionSetQueue(910),parser.OFPActionOutput(4)])
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h10'],ipv4_dst=ip_IT)
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionOutput(2)])
                if dpid == 4:
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip_IT,ipv4_dst=self.IPs['h10'])
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionOutput(1)])
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h10'],ipv4_dst=ip_IT)
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionSetQueue(910),parser.OFPActionOutput(4)])

            # Allowing communication IT <--> Patient (h12)
            if "h12" in body:
                if dpid == 5:
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip_IT,ipv4_dst=self.IPs['h12'])
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionSetQueue(912),parser.OFPActionOutput(4)])
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h12'],ipv4_dst=ip_IT)
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionOutput(2)])
                if dpid == 4:
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=ip_IT,ipv4_dst=self.IPs['h12'])
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionOutput(5)])
                    match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h12'],ipv4_dst=ip_IT)
                    self.add_flow(dp, ASSISTANCE_PRIORITY,match,[parser.OFPActionSetQueue(912),parser.OFPActionOutput(4)])

        Slices["Assistance"]=True
        self.logger.info("Assistance slice ENABLED. Targeted devices: "+body)
    
    def remove_Assistance_slice(self):
        # This method removes the rules with priority "ASSISTANCE_PRIORITY" from all switches (regardless of their content) 
        global ASSISTANCE_PRIORITY
        for dp, p, match in installed_flows_for_assistance:
            if p == ASSISTANCE_PRIORITY:
                self.delete_flow(dp, match)

        Slices["Assistance"]=False
        self.logger.info("Assistance slice DISABLED")


# -------------------- IDS --------------------
    def add_IDS_slice(self):
        subprocess.run(['sudo','sh','Scripts/add_IDS.sh'], check=True)
        Slices["IDS"]=True
        self.logger.info("Intrusion Detection System (IDS) slice ENABLED")

    def remove_IDS_slice(self):
        subprocess.run(["sudo", "ovs-vsctl", "clear", "Bridge", "s4", "mirrors"], check=True)
        Slices["IDS"]=False
        self.logger.info("Intrusion Detection System (IDS) slice DISABLED")

        
# -------------------- Laboratory --------------------
    def add_Laboratory_slice(self):
        for dpid, dp in self.datapaths.items():
            parser = dp.ofproto_parser
            if dpid == 5:
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h8'],ipv4_dst=self.IPs['h10'])
                self.add_flow(dp, 10,match,[parser.OFPActionSetQueue(1),parser.OFPActionOutput(4)])
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h10'],ipv4_dst=self.IPs['h8'])
                self.add_flow(dp, 10,match,[parser.OFPActionOutput(1)])
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h8'])
                self.add_flow(dp, 2,match,[parser.OFPActionSetQueue(1),parser.OFPActionOutput(5)])
                match = parser.OFPMatch(eth_type=0x0800,ipv4_dst=self.IPs['h8'])
                self.add_flow(dp, 2,match,[parser.OFPActionOutput(1)])

            if dpid == 4:
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h8'],ipv4_dst=self.IPs['h10'])
                self.add_flow(dp, 10,match,[parser.OFPActionOutput(1)])
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h10'],ipv4_dst=self.IPs['h8'])
                self.add_flow(dp, 10,match,[parser.OFPActionSetQueue(103),parser.OFPActionOutput(4)])

            if dpid == 1:
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h8'])
                self.add_flow(dp, 2,match,[parser.OFPActionOutput(3)])
                match = parser.OFPMatch(eth_type=0x0800,ipv4_dst=self.IPs['h8'])
                self.add_flow(dp, 2,match,[parser.OFPActionSetQueue(8),parser.OFPActionOutput(5)])

        Slices["Laboratory"] = True
        self.logger.info("Laboratory slice ENABLED")

    def remove_Laboratory_slice(self):
        for dpid, dp in self.datapaths.items():
            parser = dp.ofproto_parser
            if dpid == 5:
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h8'],ipv4_dst=self.IPs['h10'])
                self.delete_flow(dp, match)
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h10'],ipv4_dst=self.IPs['h8'])
                self.delete_flow(dp, match)
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h8'])
                self.delete_flow(dp,match)
                match = parser.OFPMatch(eth_type=0x0800,ipv4_dst=self.IPs['h8'])
                self.delete_flow(dp,match)

            if dpid == 4:
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h8'],ipv4_dst=self.IPs['h10'])
                self.delete_flow(dp, match)
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h10'],ipv4_dst=self.IPs['h8'])
                self.delete_flow(dp, match)

            if dpid == 1:
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h8'])
                self.delete_flow(dp,match)
                match = parser.OFPMatch(eth_type=0x0800,ipv4_dst=self.IPs['h8'])
                self.delete_flow(dp,match)
        Slices["Laboratory"] = False
        self.logger.info("Laboratory slice DISABLED")

# -------------------- Telesurgery --------------------
    def add_Telesurgery_slice(self):
        if self.is_link_down:
            self.add_Telesurgery_slice_backup()        
        else:
            self.add_Telesurgery_slice_primary()

    def add_Telesurgery_slice_primary(self):
        subprocess.run(["sudo","./Scripts/increase_IoT_bandwidth.sh"])
        for dpid, dp in self.datapaths.items():
            parser = dp.ofproto_parser
            if dpid == 2:
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h5'],ipv4_dst=self.IPs['h12'])
                self.add_flow(dp,65535,match,[parser.OFPActionSetQueue(200),parser.OFPActionOutput(5)])
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h12'],ipv4_dst=self.IPs['h5'])
                self.add_flow(dp,65535,match,[parser.OFPActionOutput(3)])
            elif dpid == 4:
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h5'],ipv4_dst=self.IPs['h12'])
                self.add_flow(dp,65535,match,[parser.OFPActionOutput(5)])
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h12'],ipv4_dst=self.IPs['h5'])
                self.add_flow(dp,65535,match,[parser.OFPActionSetQueue(200),parser.OFPActionOutput(3)])
        Slices["Telesurgery"] = True
        self.logger.info("Telesurgery slice ENABLED (Primary)")

    def add_Telesurgery_slice_backup(self):
        subprocess.run(["sudo","./Scripts/reduce_IoT_bandwidth.sh"])
        for dpid, dp in self.datapaths.items():
            parser = dp.ofproto_parser
            if dpid == 2: # s2
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h5'],ipv4_dst=self.IPs['h12'])
                self.add_flow(dp,65534,match,[parser.OFPActionSetQueue(300),parser.OFPActionOutput(6)])
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h12'],ipv4_dst=self.IPs['h5'])
                self.add_flow(dp,65534,match,[parser.OFPActionOutput(3)])

            elif dpid == 5: # s5
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h5'],ipv4_dst=self.IPs['h12'])
                self.add_flow(dp,65534,match,[parser.OFPActionOutput(4)])
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h12'],ipv4_dst=self.IPs['h5'])
                self.add_flow(dp,65534,match,[parser.OFPActionOutput(3)])

            elif dpid == 4: # s4
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h5'],ipv4_dst=self.IPs['h12'])
                self.add_flow(dp,65534,match,[parser.OFPActionOutput(5)])
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h12'],ipv4_dst=self.IPs['h5'])
                self.add_flow(dp,65534,match,[parser.OFPActionSetQueue(300),parser.OFPActionOutput(4)])
        Slices["Telesurgery"] = True
        self.logger.info("Telesurgery slice ENABLED (Backup)")

    def remove_Telesurgery_slice(self):
        # This method removes the Telesurgery slices (both primary and backup)
        subprocess.run(["sudo","./Scripts/increase_IoT_bandwidth.sh"])
        for dpid, dp in self.datapaths.items():
            parser = dp.ofproto_parser
            if dpid == 2: # s2
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h5'],ipv4_dst=self.IPs['h12'])
                self.delete_flow(dp,match)
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h12'],ipv4_dst=self.IPs['h5'])
                self.delete_flow(dp,match)

            elif dpid == 5: # s5
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h5'],ipv4_dst=self.IPs['h12'])
                self.delete_flow(dp,match)
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h12'],ipv4_dst=self.IPs['h5'])
                self.delete_flow(dp,match)

            elif dpid == 4: # s4
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h5'],ipv4_dst=self.IPs['h12'])
                self.delete_flow(dp,match)
                match = parser.OFPMatch(eth_type=0x0800,ipv4_src=self.IPs['h12'],ipv4_dst=self.IPs['h5'])
                self.delete_flow(dp,match)
        Slices["Telesurgery"] = False
        self.logger.info("Telesurgery slice DISABLED")
