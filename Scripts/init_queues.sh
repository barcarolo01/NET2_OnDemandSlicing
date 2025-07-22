#!/bin/bash

default_max_bw=1000000000

bw_guest_internet=10000000

bw_office_internet=30000000
bw_office_to_office=30000000

bw_LAB_internet=30000000
bw_LAB_datacenter=10000000

bw_IoT_to_IoT=5000000
bw_IoT_datacenter=10000000

bw_telesurgery_primary=25000000
bw_telesurgery_backup=25000000

bw_IoT_Datacenter=10000000

bw_assistance=10000000

# ==================== s1 ====================
# Queue on eth1 
sudo ovs-vsctl set port s1-eth1 qos=@qos_s1eth1 \
  -- --id=@qos_s1eth1 create qos type=linux-htb other-config:max-rate=$default_max_bw \
  queues:0=@default_s1_eth1 queues:1=@nat0_to_h1 \
  -- --id=@default_s1_eth1 create queue other-config:max-rate=$default_max_bw \
  -- --id=@nat0_to_h1 create queue other-config:max-rate=$bw_guest_internet

# Queue on eth2
sudo ovs-vsctl set port s1-eth2 qos=@qos_s1eth2 \
  -- --id=@qos_s1eth2 create qos type=linux-htb other-config:max-rate=$default_max_bw \
  queues:0=@default_s1_eth2 queues:2=@nat0_to_h2 \
  -- --id=@default_s1_eth2 create queue other-config:max-rate=$default_max_bw \
  -- --id=@nat0_to_h2 create queue other-config:max-rate=$bw_guest_internet

# Queues on eth3
sudo ovs-vsctl set port s1-eth3 qos=@qos_s1eth3 \
  -- --id=@qos_s1eth3 create qos type=linux-htb other-config:max-rate=$default_max_bw \
  queues:0=@default_s1_eth3 queues:1=@h1_to_nat0 queues:2=@h2_to_nat0 \
  -- --id=@default_s1_eth3 create queue other-config:max-rate=$default_max_bw \
  -- --id=@h1_to_nat0 create queue other-config:max-rate=$bw_guest_internet \
  -- --id=@h2_to_nat0 create queue other-config:max-rate=$bw_guest_internet 

# Queue on eth4
sudo ovs-vsctl set port s1-eth4 qos=@qos_s1eth4 \
  -- --id=@qos_s1eth4 create qos type=linux-htb other-config:max-rate=$default_max_bw \
  queues:0=@default_s1_eth4 queues:6=@nat0_to_h6 queues:7=@nat0_to_h7 \
  -- --id=@default_s1_eth4 create queue other-config:max-rate=$default_max_bw \
  -- --id=@nat0_to_h6 create queue other-config:max-rate=$bw_office_internet \
  -- --id=@nat0_to_h7 create queue other-config:max-rate=$bw_office_internet 

# Queue on eth5
sudo ovs-vsctl set port s1-eth5 qos=@qos_s1eth5 \
  -- --id=@qos_s1eth5 create qos type=linux-htb other-config:max-rate=$default_max_bw \
  queues:0=@default_s1_eth5 queues:8=@nat0_to_h8\
  -- --id=@default_s1_eth5 create queue other-config:max-rate=$default_max_bw \
  -- --id=@nat0_to_h8 create queue other-config:max-rate=$bw_LAB_internet \


# ==================== s2 ====================
#Queue on eth1
sudo ovs-vsctl set port s2-eth1 qos=@qos_s2eth1 \
  -- --id=@qos_s2eth1 create qos type=linux-htb other-config:max-rate=$default_max_bw \
  queues:0=@default_s2_eth1 queues:1=@h4_to_h3 queues:101=@h10_to_h3 \
  -- --id=@default_s2_eth1 create queue other-config:max-rate=$default_max_bw \
  -- --id=@h4_to_h3 create queue other-config:max-rate=$bw_IoT_to_IoT \
  -- --id=@h10_to_h3 create queue other-config:max-rate=$bw_IoT_datacenter

#Queue on eth2
sudo ovs-vsctl set port s2-eth2 qos=@qos_s2eth2 \
  -- --id=@qos_s2eth2 create qos type=linux-htb other-config:max-rate=$default_max_bw \
  queues:0=@default_s2_eth2 queues:2=@h3_to_h4 queues:102=@h10_to_h4 \
  -- --id=@default_s2_eth2 create queue other-config:max-rate=$default_max_bw \
  -- --id=@h3_to_h4 create queue other-config:max-rate=$bw_IoT_to_IoT \
  -- --id=@h10_to_h4 create queue other-config:max-rate=$bw_IoT_datacenter

# Queues on eth5
sudo ovs-vsctl set port s2-eth5 qos=@qos_s2eth5 \
  -- --id=@qos_s2eth5 create qos type=linux-htb other-config:max-rate=$default_max_bw \
  queues:0=@default_s2_eth5 queues:200=@h5_to_h12_primary \
  -- --id=@default_s2_eth5 create queue other-config:max-rate=$default_max_bw \
  -- --id=@h5_to_h12_primary create queue other-config:max-rate=$bw_telesurgery_primary

# Queues on eth6
sudo ovs-vsctl set port s2-eth6 qos=@qos_s2eth6 \
  -- --id=@qos_s2eth6 create qos type=linux-htb other-config:max-rate=$default_max_bw \
  queues:0=@default_s2_eth6 queues:1=@h3_to_h10 queues:2=@h4_to_h10 queues:300=@h5_to_h12_backup queues:903=@h3_to_h9 queues:904=@h4_to_h9 queues:905=@h5_to_h9\
  -- --id=@default_s2_eth6 create queue other-config:max-rate=$default_max_bw \
  -- --id=@h3_to_h10 create queue other-config:max-rate=$bw_IoT_Datacenter \
  -- --id=@h4_to_h10 create queue other-config:max-rate=$bw_IoT_Datacenter \
  -- --id=@h5_to_h12_backup create queue other-config:max-rate=$bw_telesurgery_backup \
  -- --id=@h3_to_h9 create queue other-config:max-rate=$bw_assistance \
  -- --id=@h4_to_h9 create queue other-config:max-rate=$bw_assistance \
  -- --id=@h5_to_h9 create queue other-config:max-rate=$bw_assistance


# ==================== s3 ====================
#Queue on eth1
sudo ovs-vsctl set port s3-eth1 qos=@qos_s3eth1 \
  -- --id=@qos_s3eth1 create qos type=linux-htb other-config:max-rate=$default_max_bw \
  queues:0=@default_s3_eth1 queues:1=@h7_to_h6 \
  -- --id=@default_s3_eth1 create queue other-config:max-rate=$default_max_bw \
  -- --id=@h7_to_h6 create queue other-config:max-rate=$bw_office_to_office

#Queue on eth2
sudo ovs-vsctl set port s3-eth2 qos=@qos_s3eth2 \
  -- --id=@qos_s3eth2 create qos type=linux-htb other-config:max-rate=$default_max_bw \
  queues:0=@default_s3_eth2 queues:2=@h6_to_h7 \
  -- --id=@default_s3_eth2 create queue other-config:max-rate=$default_max_bw \
  -- --id=@h6_to_h7 create queue other-config:max-rate=$bw_office_to_office

# Queues on eth3
sudo ovs-vsctl set port s3-eth3 qos=@qos_s3eth3 \
  -- --id=@qos_s3eth3 create qos type=linux-htb other-config:max-rate=$default_max_bw \
  queues:0=@default_s3_eth3 queues:1=@h6_to_nat0 queues:2=@h7_to_nat0 \
  -- --id=@default_s3_eth3 create queue other-config:max-rate=$default_max_bw \
  -- --id=@h6_to_nat0 create queue other-config:max-rate=$bw_office_internet \
  -- --id=@h7_to_nat0 create queue other-config:max-rate=$bw_office_internet 

#Queue on eth4
sudo ovs-vsctl set port s3-eth4 qos=@qos_s3eth4 \
  -- --id=@qos_s3eth4 create qos type=linux-htb other-config:max-rate=$default_max_bw \
  queues:0=@default_s3_eth4 queues:906=@h6_to_h9 queues:907=@h7_to_h9 \
  -- --id=@default_s3_eth4 create queue other-config:max-rate=$default_max_bw \
  -- --id=@h6_to_h9 create queue other-config:max-rate=$bw_assistance \
  -- --id=@h7_to_h9 create queue other-config:max-rate=$bw_assistance 


# ==================== s4 ====================
# Queues on eth3
sudo ovs-vsctl set port s4-eth3 qos=@qos_s4eth3 \
  -- --id=@qos_s4eth3 create qos type=linux-htb other-config:max-rate=$default_max_bw \
  queues:0=@default_s4_eth3 queues:200=@h12_to_h5_primary \
  -- --id=@default_s4_eth3 create queue other-config:max-rate=$default_max_bw \
  -- --id=@h12_to_h5_primary create queue other-config:max-rate=$bw_telesurgery_primary

# Queues on eth4
sudo ovs-vsctl set port s4-eth4 qos=@qos_s4eth4 \
  -- --id=@qos_s4eth4 create qos type=linux-htb other-config:max-rate=$default_max_bw \
  queues:0=@default_s4_eth4 queues:101=@h10_to_h3 queues:102=@h10_to_h4 queues:103=@h10_to_h8 queues:300=@h12_to_h5_backup queues:910=@h10_to_h9 queues:912=@h12_to_h9 \
  -- --id=@default_s4_eth4 create queue other-config:max-rate=$default_max_bw \
  -- --id=@h10_to_h3 create queue other-config:max-rate=$bw_IoT_Datacenter \
  -- --id=@h10_to_h4 create queue other-config:max-rate=$bw_IoT_Datacenter \
  -- --id=@h10_to_h8 create queue other-config:max-rate=$bw_LAB_datacenter \
  -- --id=@h12_to_h5_backup create queue other-config:max-rate=$bw_telesurgery_backup \
  -- --id=@h10_to_h9 create queue other-config:max-rate=$bw_assistance \
  -- --id=@h12_to_h9 create queue other-config:max-rate=$bw_assistance


# ==================== s5 ====================
# Queues on eth1
sudo ovs-vsctl set port s5-eth1 qos=@qos_s5eth1 \
  -- --id=@qos_s5eth1 create qos type=linux-htb other-config:max-rate=$default_max_bw \
  queues:0=@default_s5_eth1 queues:908=@h9_to_h8 \
  -- --id=@default_s5_eth1 create queue other-config:max-rate=$default_max_bw \
  -- --id=@h9_to_h8 create queue other-config:max-rate=$bw_assistance 

# Queues on eth2
sudo ovs-vsctl set port s5-eth2 qos=@qos_s5eth2 \
  -- --id=@qos_s5eth2 create qos type=linux-htb other-config:max-rate=$default_max_bw \
  queues:0=@default_s5_eth2 queues:908=@h8_to_h9 \
  -- --id=@default_s5_eth2 create queue other-config:max-rate=$default_max_bw \
  -- --id=@h8_to_h9 create queue other-config:max-rate=$bw_assistance 

# Queues on eth3
sudo ovs-vsctl set port s5-eth3 qos=@qos_s5eth3 \
  -- --id=@qos_s5eth3 create qos type=linux-htb other-config:max-rate=$default_max_bw \
  queues:0=@default_s5_eth3 queues:903=@h9_to_h3 queues:904=@h9_to_h4 queues:905=@h9_to_h5 queues:906=@h9_to_h6 queues:907=@h9_to_h7 \
  -- --id=@default_s5_eth3 create queue other-config:max-rate=$default_max_bw \
  -- --id=@h9_to_h3 create queue other-config:max-rate=$bw_assistance \
  -- --id=@h9_to_h4 create queue other-config:max-rate=$bw_assistance \
  -- --id=@h9_to_h5 create queue other-config:max-rate=$bw_assistance \
  -- --id=@h9_to_h6 create queue other-config:max-rate=$bw_assistance \
  -- --id=@h9_to_h7 create queue other-config:max-rate=$bw_assistance 

# Queues on eth4
sudo ovs-vsctl set port s5-eth4 qos=@qos_s5eth4 \
  -- --id=@qos_s5eth4 create qos type=linux-htb other-config:max-rate=$default_max_bw \
  queues:0=@default_s5_eth4 queues:1=@h8_to_h10 queues:910=@h9_to_h10 queues:912=@h9_to_h12 \
  -- --id=@default_s5_eth4 create queue other-config:max-rate=$default_max_bw \
  -- --id=@h8_to_h10 create queue other-config:max-rate=$bw_LAB_datacenter \
  -- --id=@h9_to_h10 create queue other-config:max-rate=$bw_assistance \
  -- --id=@h9_to_h12 create queue other-config:max-rate=$bw_assistance

# Queues on eth5
sudo ovs-vsctl set port s5-eth5 qos=@qos_s5eth5 \
  -- --id=@qos_s5eth5 create qos type=linux-htb other-config:max-rate=$default_max_bw \
  queues:0=@default_s5_eth5 queues:1=@h8_to_nat0 \
  -- --id=@default_s5_eth5 create queue other-config:max-rate=$default_max_bw \
  -- --id=@h8_to_nat0 create queue other-config:max-rate=$bw_LAB_internet 





