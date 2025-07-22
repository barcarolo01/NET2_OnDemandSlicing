#!/bin/bash

NEW_BW="5000000"

QOS_UUID=$(sudo ovs-vsctl get port s2-eth6 qos)  # Get the QoS UUID for the port
QUEUE_UUID=$(sudo ovs-vsctl get qos $QOS_UUID queues:1)
sudo ovs-vsctl set queue $QUEUE_UUID other-config:max-rate=$NEW_BW

QOS_UUID=$(sudo ovs-vsctl get port s2-eth6 qos)
QUEUE_UUID=$(sudo ovs-vsctl get qos $QOS_UUID queues:2)
sudo ovs-vsctl set queue $QUEUE_UUID other-config:max-rate=$NEW_BW

QOS_UUID=$(sudo ovs-vsctl get port s4-eth4 qos)
QUEUE_UUID=$(sudo ovs-vsctl get qos $QOS_UUID queues:101)
sudo ovs-vsctl set queue $QUEUE_UUID other-config:max-rate=$NEW_BW

QOS_UUID=$(sudo ovs-vsctl get port s4-eth4 qos)
QUEUE_UUID=$(sudo ovs-vsctl get qos $QOS_UUID queues:102)
sudo ovs-vsctl set queue $QUEUE_UUID other-config:max-rate=$NEW_BW