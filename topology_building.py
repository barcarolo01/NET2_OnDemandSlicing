#!/usr/bin/env python3

from mininet.net import Mininet
from mininet.node import *
from mininet.nodelib import NAT
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.link import TCLink
import subprocess
import json

INTERNET_IFACE = 'enp0s3' #Internet interface for NAT

if __name__ == '__main__':
    subprocess.run(["clear"], check=True) #Cleaning the console

    # Uncomment for vebose log
    #setLogLevel('info') 
    
    # Reading hosts IP addresses from config file
    with open('config_files/hosts.json', 'r') as file:
        IPs = json.load(file)
    
    net = Mininet(
        controller=RemoteController,
        switch=OVSSwitch,
        link=TCLink,
        autoSetMacs=True,
        autoStaticArp=True
    )
    # ========== Remote controller ==========
    net.addController('c0',ip="127.0.0.1",port=6653) #Controller listening on port 6653

    # ========== Switches ==========
    s1 = net.addSwitch('s1',protocols="OpenFlow13")
    s2 = net.addSwitch('s2',protocols="OpenFlow13")
    s3 = net.addSwitch('s3',protocols="OpenFlow13")
    s4 = net.addSwitch('s4',protocols="OpenFlow13")
    s5 = net.addSwitch('s5',protocols="OpenFlow13")

    # ========== Hosts ==========
    # ------ Guest devices ------
    h1 = net.addHost('h1',ip=IPs['h1'])
    h2 = net.addHost('h2',ip=IPs['h2'])

    # ------ IoT medical devices ------
    IoTmed1 = net.addHost('h3',ip=IPs['h3'])
    IoTmed2 = net.addHost('h4',ip=IPs['h4'])
    

    # ------ Office A terminals ------
    office_1 = net.addHost('h6',ip=IPs['h6']) 
    office_2 = net.addHost('h7',ip=IPs['h7']) 

    # ------ Office B terminals ------
    LAB = net.addHost('h8',ip=IPs['h8']) 
    IT = net.addHost('h9',ip=IPs['h9']) 

    # ------ Datacenter ------
    dataCenter = net.addHost('h10',ip=IPs['h10'])
    monitor = net.addHost('h11',ip=IPs['h11']) 

    # ------ Remote surgery ------
    surgeon_workstation = net.addHost('h5',ip=IPs['h5'])
    patient = net.addHost('h12',ip=IPs['h12']) 

    # ------ Gateway (Internet) ------
    gateway=net.addHost('nat0', cls=NAT, ip='172.64.255.254', inNamespace=False)
    
    
    # ========== Links ==========
    # ------ Terminal-switch links ------
    net.addLink(h1, s1, port2=1)
    net.addLink(h2, s1, port2=2)

    net.addLink(IoTmed1, s2, port2=1)
    net.addLink(IoTmed2, s2, port2=2)
    
    net.addLink(surgeon_workstation, s2, port2=3)
    net.addLink(patient, s4, port2=5)
    
    net.addLink(office_1, s3, port2=1)
    net.addLink(office_2, s3, port2=2)
    net.addLink(LAB, s5, port2=1)
    net.addLink(IT, s5, port=2)
    
    net.addLink(dataCenter,s4, port2=1)
    net.addLink(monitor,s4, port2 = 2)
    net.addLink(gateway,s1, port2 = 3)
  

    # ------ Switch-switch links ------
    net.addLink(s1,s3, port1=4, port2=3)
    net.addLink(s2,s3, port1=4, port2=4)
    net.addLink(s2,s4, port1=5, port2=3)#, delay='1ms',bw=1000)
    net.addLink(s2,s5, port1=6, port2=3)
    net.addLink(s4,s5, port1=4, port2=4)
    net.addLink(s1,s5, port1=5, port2=5)
    
    net.start()
    gateway.cmd('sysctl -w net.ipv4.ip_forward=1')
    gateway.cmd(f'iptables -t nat -A POSTROUTING -o {INTERNET_IFACE} -j MASQUERADE')
        
    # Set default route and DNS on devices with access to Internet
    h1.cmd('ip route add default via 172.64.255.254')
    h1.cmd('echo "nameserver 8.8.8.8" > /etc/resolv.conf')
    h2.cmd('ip route add default via 172.64.255.254')
    h2.cmd('echo "nameserver 8.8.8.8" > /etc/resolv.conf')
    office_1.cmd('ip route add default via 172.64.255.254')
    office_1.cmd('echo "nameserver 8.8.8.8" > /etc/resolv.conf')
    office_2.cmd('ip route add default via 172.64.255.254')
    office_2.cmd('echo "nameserver 8.8.8.8" > /etc/resolv.conf')
    LAB.cmd('ip route add default via 172.64.255.254')
    LAB.cmd('echo "nameserver 8.8.8.8" > /etc/resolv.conf')
    IT.cmd('ip route add default via 172.64.255.254')
    IT.cmd('echo "nameserver 8.8.8.8" > /etc/resolv.conf')

    #Initialization script
    output=subprocess.run(['sudo', 'sh','Scripts/init_queues.sh'], capture_output=True, text=True, check=True)
    output=subprocess.run(['sudo', 'sh','Scripts/init.sh'], capture_output=True, text=True, check=True)
    
    print("========== START ==========")
    CLI(net)

    net.stop()
