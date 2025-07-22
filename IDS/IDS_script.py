from scapy.all import sniff, IP, ICMP
from collections import defaultdict
import time

# Dict of timestamp of ping packet received
icmp_counter = defaultdict(list)

PING_THRESHOLD = 100  # Number of packets
TIME_THRESHOLD = 5  # Time window to monitor

def detect_attack(pkt):
    if pkt.haslayer(ICMP) and pkt.haslayer(IP):
        src = pkt[IP].src
        icmp_counter[src].append(time.time())

        # Remove old entries
        icmp_counter[src] = [t for t in icmp_counter[src] if time.time() - t < TIME_THRESHOLD]

        if len(icmp_counter[src]) > PING_THRESHOLD:
            if src != "172.64.255.1": # Do not take into account ping replies from Datacenter
                print(f"[WARNING] Ping flood detected from {src}")
                icmp_counter[src] = []  # Flush list of timestamp

print("====== IDS ACTIVATED ======")
print("Scanning...")
sniff(filter="ip", prn=detect_attack, store=0) # When a packet is detected, "detect_attack" is called