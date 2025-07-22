#!/bin/bash

# Create the mirror
sudo ovs-vsctl \
  -- --id=@in_port get Port s4-eth1 \
  -- --id=@out_port get Port s4-eth2 \
  -- --id=@m create Mirror name=s4_mirror select-dst-port=@in_port output-port=@out_port \
  -- set Bridge s4 mirrors=@m