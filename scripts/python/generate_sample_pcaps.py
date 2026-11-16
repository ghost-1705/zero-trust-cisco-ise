#!/usr/bin/env python3
"""
generate_sample_pcaps.py
========================
Generates realistic educational Wireshark .pcap packet capture files:
  1. captures/8021x_eap_tls_auth.pcap
  2. captures/radius_cisco_ise_avpair.pcap
  3. captures/rfc5176_coa_quarantine.pcap

Author : ghost-1705
License: MIT
"""

import struct
import os
import time

def write_pcap(filename, packets):
    """
    Writes a list of raw packet bytes into a standard libpcap (.pcap) file.
    """
    # PCAP Global Header (24 bytes)
    # Magic (0xa1b2c3d4), Major 2, Minor 4, Zone 0, Sigfigs 0, Snaplen 65535, LinkType 1 (Ethernet)
    global_hdr = struct.pack("<IHHiIII", 0xa1b2c3d4, 2, 4, 0, 0, 65535, 1)
    
    with open(filename, "wb") as f:
        f.write(global_hdr)
        base_ts = int(time.time()) - 3600
        for i, pkt in enumerate(packets):
            ts_sec = base_ts + i
            ts_usec = (i * 123456) % 1000000
            pkt_len = len(pkt)
            # Packet header: ts_sec, ts_usec, incl_len, orig_len
            pkt_hdr = struct.pack("<IIII", ts_sec, ts_usec, pkt_len, pkt_len)
            f.write(pkt_hdr)
            f.write(pkt)

def mac_bytes(mac_str):
    return bytes.fromhex(mac_str.replace(":", "").replace("-", ""))

def ip_bytes(ip_str):
    return bytes(map(int, ip_str.split(".")))

def build_eth(dst_mac, src_mac, ethertype):
    return mac_bytes(dst_mac) + mac_bytes(src_mac) + struct.pack("!H", ethertype)

def build_ipv4_udp(src_ip, dst_ip, src_port, dst_port, payload):
    # IPv4 Header
    ip_len = 20 + 8 + len(payload)
    # Ver/IHL (0x45), ToS (0), TotalLen, Id (0x1234), Flags/Frag (0), TTL (64), Proto UDP (17), Chksum (0)
    ip_hdr = struct.pack("!BBHHHBBH4s4s", 0x45, 0, ip_len, 0x1234, 0, 64, 17, 0, ip_bytes(src_ip), ip_bytes(dst_ip))
    # UDP Header
    udp_len = 8 + len(payload)
    udp_hdr = struct.pack("!HHHH", src_port, dst_port, udp_len, 0)
    return ip_hdr + udp_hdr + payload

def generate_eapol_pcaps(out_dir):
    packets = []
    # Supplicant and Switch Authenticator MACs
    supplicant = "00:1A:2B:3C:4D:5E"
    authenticator = "00:00:0C:07:AC:01"
    
    # 1. EAPOL-Start (Supplicant -> Switch, EtherType 0x888E)
    eapol_hdr = struct.pack("!BBH", 1, 1, 0) # Ver 1, Type EAPOL-Start (1), Len 0
    packets.append(build_eth(authenticator, supplicant, 0x888E) + eapol_hdr)
    
    # 2. EAP-Request / Identity (Switch -> Supplicant)
    # EAP: Code=1(Request), Id=1, Len=5, Type=1 (Identity)
    eap_req_id = struct.pack("!BBHB", 1, 1, 5, 1)
    eapol_pkt = struct.pack("!BBH", 1, 0, len(eap_req_id)) + eap_req_id
    packets.append(build_eth(supplicant, authenticator, 0x888E) + eapol_pkt)
    
    # 3. EAP-Response / Identity (Supplicant -> Switch)
    user_str = b"john.doe@enterprise.local"
    eap_resp_id = struct.pack("!BBHB", 2, 1, 5 + len(user_str), 1) + user_str
    eapol_pkt = struct.pack("!BBH", 1, 0, len(eap_resp_id)) + eap_resp_id
    packets.append(build_eth(authenticator, supplicant, 0x888E) + eapol_pkt)
    
    # 4. EAP-Request / EAP-TLS Start (Code 1, Id 2, Type 13)
    eap_tls_start = struct.pack("!BBHBB", 1, 2, 6, 13, 0x20) # Type 13 (EAP-TLS), Flags Start (0x20)
    eapol_pkt = struct.pack("!BBH", 1, 0, len(eap_tls_start)) + eap_tls_start
    packets.append(build_eth(supplicant, authenticator, 0x888E) + eapol_pkt)
    
    # 5. EAP-Success (Code 3, Id 2, Len 4)
    eap_success = struct.pack("!BBH", 3, 2, 4)
    eapol_pkt = struct.pack("!BBH", 1, 0, len(eap_success)) + eap_success
    packets.append(build_eth(supplicant, authenticator, 0x888E) + eapol_pkt)
    
    write_pcap(os.path.join(out_dir, "8021x_eap_tls_auth.pcap"), packets)

def generate_radius_pcaps(out_dir):
    packets = []
    sw_mac = "00:00:0C:07:AC:01"
    ise_mac = "00:50:56:89:11:22"
    sw_ip = "192.168.100.11"
    ise_ip = "192.168.1.100"
    
    # RADIUS Access-Request (Code 1, Identifier 12)
    # Attributes: User-Name (1), NAS-IP-Address (4), Calling-Station-Id (31)
    username_attr = struct.pack("!BB", 1, 2 + len(b"john.doe@enterprise.local")) + b"john.doe@enterprise.local"
    nas_ip_attr = struct.pack("!BB4s", 4, 6, ip_bytes(sw_ip))
    calling_mac = b"00-1A-2B-3C-4D-5E"
    calling_attr = struct.pack("!BB", 31, 2 + len(calling_mac)) + calling_mac
    radius_attrs = username_attr + nas_ip_attr + calling_attr
    
    radius_len = 20 + len(radius_attrs)
    authenticator = bytes([0x11] * 16)
    radius_req = struct.pack("!BBH16s", 1, 12, radius_len, authenticator) + radius_attrs
    
    eth_ip_udp = build_eth(ise_mac, sw_mac, 0x0800) + build_ipv4_udp(sw_ip, ise_ip, 1812, 1812, radius_req)
    packets.append(eth_ip_udp)
    
    # RADIUS Access-Accept (Code 2, Identifier 12)
    # Attributes: Tunnel-Type (64), Tunnel-Medium-Type (65), Tunnel-Private-Group-ID (81=VLAN 10), Cisco-AVPair (26)
    vlan_attr = struct.pack("!BBB", 64, 6, 13) # VLAN
    cisco_dacl = b"ACS:inacl#1=permit ip any any"
    # Vendor-Specific (Type 26, Vendor Cisco 9, Type 1 cisco-av-pair)
    vendor_payload = struct.pack("!BB", 1, 2 + len(cisco_dacl)) + cisco_dacl
    cisco_attr = struct.pack("!BBI", 26, 6 + len(vendor_payload), 9) + vendor_payload
    resp_attrs = vlan_attr + cisco_attr
    
    radius_accept = struct.pack("!BBH16s", 2, 12, 20 + len(resp_attrs), bytes([0x22] * 16)) + resp_attrs
    packets.append(build_eth(sw_mac, ise_mac, 0x0800) + build_ipv4_udp(ise_ip, sw_ip, 1812, 1812, radius_accept))
    
    write_pcap(os.path.join(out_dir, "radius_cisco_ise_avpair.pcap"), packets)

def generate_coa_pcaps(out_dir):
    packets = []
    sw_mac = "00:00:0C:07:AC:01"
    ise_mac = "00:50:56:89:11:22"
    sw_ip = "192.168.100.11"
    ise_ip = "192.168.1.100"
    
    # RFC 5176 CoA-Request (Code 43, Identifier 77, Port 3799)
    # Attributes: Cisco-AVPair subscriber:command=reauthenticate, Cisco-AVPair audit-session-id=C0A8640B0000001A
    av1 = b"subscriber:command=reauthenticate"
    av2 = b"audit-session-id=C0A8640B0000001A"
    cisco_attr1 = struct.pack("!BBI", 26, 6 + 2 + len(av1), 9) + struct.pack("!BB", 1, 2 + len(av1)) + av1
    cisco_attr2 = struct.pack("!BBI", 26, 6 + 2 + len(av2), 9) + struct.pack("!BB", 1, 2 + len(av2)) + av2
    coa_attrs = cisco_attr1 + cisco_attr2
    
    coa_req = struct.pack("!BBH16s", 43, 77, 20 + len(coa_attrs), bytes([0x33] * 16)) + coa_attrs
    packets.append(build_eth(sw_mac, ise_mac, 0x0800) + build_ipv4_udp(ise_ip, sw_ip, 3799, 3799, coa_req))
    
    # CoA-ACK (Code 44, Identifier 77)
    coa_ack = struct.pack("!BBH16s", 44, 77, 20, bytes([0x44] * 16))
    packets.append(build_eth(ise_mac, sw_mac, 0x0800) + build_ipv4_udp(sw_ip, ise_ip, 3799, 3799, coa_ack))
    
    write_pcap(os.path.join(out_dir, "rfc5176_coa_quarantine.pcap"), packets)

if __name__ == "__main__":
    out = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "captures"))
    os.makedirs(out, exist_ok=True)
    generate_eapol_pcaps(out)
    generate_radius_pcaps(out)
    generate_coa_pcaps(out)
    print("Generated educational sample PCAPs in captures/:")
    for f in os.listdir(out):
        if f.endswith(".pcap"):
            print(f"  - {f} ({os.path.getsize(os.path.join(out, f))} bytes)")
