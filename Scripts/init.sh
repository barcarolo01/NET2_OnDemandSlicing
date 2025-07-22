#!/bin/bash

# Low priority routes: If a packet does not match any rule, it will be dropped
sudo ovs-ofctl -O OpenFlow13 add-flow s1 ip,priority=1,actions=DROP
sudo ovs-ofctl -O OpenFlow13 add-flow s2 ip,priority=1,actions=DROP
sudo ovs-ofctl -O OpenFlow13 add-flow s3 ip,priority=1,actions=DROP
sudo ovs-ofctl -O OpenFlow13 add-flow s4 ip,priority=1,actions=DROP
sudo ovs-ofctl -O OpenFlow13 add-flow s5 ip,priority=1,actions=DROP

# Internet connection to IT terminal
sudo ovs-ofctl -O OpenFlow13 add-flow s5 ip,priority=2,nw_src=172.64.20.2,actions=output:5
sudo ovs-ofctl -O OpenFlow13 add-flow s5 ip,priority=2,nw_dst=172.64.20.2,actions=output:2
sudo ovs-ofctl -O OpenFlow13 add-flow s1 ip,priority=2,nw_src=172.64.20.2,actions=output:3
sudo ovs-ofctl -O OpenFlow13 add-flow s1 ip,priority=2,nw_dst=172.64.20.2,actions=output:5

# NAT
sudo iptables -t nat -F
sudo iptables -F
sudo iptables -P FORWARD ACCEPT
sudo iptables -t nat -A POSTROUTING -o enp0s3 -j MASQUERADE

echo "Initialization script executed"