#!/usr/bin/env python3
"""
ise_mock_demo.py
================
Offline Zero Trust Network Access Control & Cisco ISE Simulation Engine.

Demonstrates the full Zero Trust lifecycle without requiring live hardware:
  1. Endpoint Discovery & Profiling (EAP-TLS, PEAP, MAB)
  2. Switch Port 802.1X Session Auditing
  3. Posture Evaluation & Non-Compliance Detection
  4. Automated Dynamic Authorization (CoA) Quarantine Trigger
  5. Enforcement of Quarantine dACL & Remediation VLAN

Usage:
    python ise_mock_demo.py
    python ise_mock_demo.py --export-csv sample_audit.csv

Author : ghost-1705
License: MIT
"""

import sys
import time
import json
import csv
from datetime import datetime

# ANSI Colors for terminal visualization
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

MOCK_ENDPOINTS = [
    {
        "mac": "00:1A:2B:3C:4D:5E",
        "ip": "10.10.10.101",
        "switch": "SW-ACCESS-01",
        "port": "GigabitEthernet0/1",
        "identity": "john.doe@enterprise.local",
        "auth_method": "dot1x",
        "eap_type": "EAP-TLS",
        "vlan": 10,
        "dacl": "DACL-EMPLOYEE-FULL",
        "posture": "Compliant",
        "profile": "Cisco-IP-Phone-or-Workstation",
        "status": "Authorized"
    },
    {
        "mac": "00:2B:3C:4D:5E:6F",
        "ip": "10.10.10.102",
        "switch": "SW-ACCESS-01",
        "port": "GigabitEthernet0/2",
        "identity": "alice.smith@enterprise.local",
        "auth_method": "dot1x",
        "eap_type": "EAP-TLS",
        "vlan": 10,
        "dacl": "DACL-EMPLOYEE-FULL",
        "posture": "Non-Compliant (AV Disabled)",
        "profile": "Workstation-Windows11",
        "status": "Authorized"
    },
    {
        "mac": "00:50:60:03:00:01",
        "ip": "10.10.50.15",
        "switch": "SW-ACCESS-01",
        "port": "GigabitEthernet0/3",
        "identity": "005060030001",
        "auth_method": "mab",
        "eap_type": "N/A",
        "vlan": 50,
        "dacl": "DACL-VOIP-PHONE",
        "posture": "Not Applicable",
        "profile": "Cisco-IP-Phone-8845",
        "status": "Authorized"
    },
    {
        "mac": "00:0C:29:A1:B2:C3",
        "ip": "10.10.30.50",
        "switch": "SW-ACCESS-01",
        "port": "GigabitEthernet0/4",
        "identity": "000c29a1b2c3",
        "auth_method": "mab",
        "eap_type": "N/A",
        "vlan": 30,
        "dacl": "DACL-IOT-CAMERA",
        "posture": "Not Applicable",
        "profile": "Axis-IP-Camera",
        "status": "Authorized"
    },
    {
        "mac": "F4:D1:08:99:88:77",
        "ip": "10.10.99.200",
        "switch": "SW-ACCESS-02",
        "port": "GigabitEthernet0/4",
        "identity": "unknown-device",
        "auth_method": "mab",
        "eap_type": "N/A",
        "vlan": 99,
        "dacl": "DACL-QUARANTINE-REMEDIATION",
        "posture": "Failed",
        "profile": "Unknown",
        "status": "Quarantined"
    }
]

def print_banner():
    banner = f"""{CYAN}{BOLD}
================================================================================
          ZERO TRUST NETWORK ACCESS CONTROL (ZTNA) SIMULATOR
          Cisco ISE 3.2 + IEEE 802.1X + Dynamic CoA Engine
================================================================================{RESET}
"""
    print(banner)

def step_header(step_num, title):
    print(f"\n{BOLD}[Step {step_num}] {title}{RESET}")
    print("-" * 75)
    time.sleep(0.3)

def simulate_discovery():
    step_header(1, "Continuous Profiling & Active RADIUS Session Audit")
    print(f"{'Interface':<16} {'MAC Address':<20} {'Method':<8} {'VLAN':<6} {'Posture':<26} {'Status'}")
    print("=" * 88)
    for ep in MOCK_ENDPOINTS:
        status_color = GREEN if ep["status"] == "Authorized" else RED
        posture_color = GREEN if "Compliant" in ep["posture"] and "Non" not in ep["posture"] else (YELLOW if "Non" in ep["posture"] else CYAN)
        print(f"{ep['port']:<16} {ep['mac']:<20} {ep['auth_method']:<8} {ep['vlan']:<6} {posture_color}{ep['posture']:<26}{RESET} {status_color}{ep['status']}{RESET}")
        time.sleep(0.1)

def simulate_posture_evaluation():
    step_header(2, "Continuous Posture Evaluation via Cisco ISE AnyConnect Agent")
    target = MOCK_ENDPOINTS[1]
    print(f"[*] Querying ISE MnT API for Endpoint: {BOLD}{target['mac']}{RESET}")
    print(f"    - IP Address       : {target['ip']}")
    print(f"    - Identity Source  : Active Directory (CN=Alice Smith,OU=Engineering)")
    print(f"    - Anti-Virus Check : {RED}[FAIL]{RESET} CrowdStrike Falcon sensor disabled")
    print(f"    - OS Patch Check   : {YELLOW}[WARN]{RESET} Missing KB5034441 security rollup")
    print(f"    - Evaluation Result: {RED}{BOLD}NON-COMPLIANT{RESET}")
    print(f"[!] Zero Trust Policy Trigger: RFC 5176 Change of Authorization (CoA) required.")

def simulate_coa_execution():
    step_header(3, "Executing RFC 5176 CoA Re-Authorization & DACL Enforcement")
    target = MOCK_ENDPOINTS[1]
    print(f"[*] Dispatching CoA-Request from ISE PAN (192.168.1.100) to {target['switch']}...")
    time.sleep(0.4)
    print(f"    >> RADIUS Code: 43 (CoA-Request) | ID: 104")
    print(f"    >> Cisco-AVPair: audit-session-id=C0A8640B0000001A")
    print(f"    >> Cisco-AVPair: subscriber:command=reauthenticate")
    print(f"    >> Cisco-AVPair: url-redirect-acl=ACL-WEBAUTH-REDIRECT")
    print(f"    >> Cisco-AVPair: dacl:in=DACL-QUARANTINE-REMEDIATION")
    time.sleep(0.3)
    print(f"[*] Response from {target['switch']}: {GREEN}CoA-ACK (Code 44) Received.{RESET}")

    # Mutate state
    target["vlan"] = 99
    target["dacl"] = "DACL-QUARANTINE-REMEDIATION"
    target["status"] = "Quarantined"

    print(f"\n{GREEN}[+] Session dynamically transitioned to VLAN 99 (Quarantine / Remediation).{RESET}")
    print(f"    Applied dACL: Permit DNS & Patch Server (192.168.200.10); Deny Corporate Subnets.")

def export_audit_csv(filepath="sample_audit_report.csv"):
    step_header(4, f"Exporting Structured Audit Log to {filepath}")
    headers = ["MAC Address", "IP Address", "Switch", "Port", "Identity", "Auth Method", "VLAN", "dACL", "Posture", "Status"]
    with open(filepath, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for ep in MOCK_ENDPOINTS:
            writer.writerow([
                ep["mac"], ep["ip"], ep["switch"], ep["port"],
                ep["identity"], ep["auth_method"], ep["vlan"],
                ep["dacl"], ep["posture"], ep["status"]
            ])
    print(f"{GREEN}[SUCCESS]{RESET} Audit report written with {len(MOCK_ENDPOINTS)} verified endpoint records.")

def main():
    print_banner()
    simulate_discovery()
    simulate_posture_evaluation()
    simulate_coa_execution()
    export_csv = "audit_report_demo.csv"
    if "--export-csv" in sys.argv:
        idx = sys.argv.index("--export-csv")
        if idx + 1 < len(sys.argv):
            export_csv = sys.argv[idx + 1]
    export_audit_csv(export_csv)
    print(f"\n{BOLD}{GREEN}Zero Trust verification cycle completed successfully.{RESET}\n")

if __name__ == "__main__":
    main()
