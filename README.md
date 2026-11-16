# 🔐 Zero Trust Network with Cisco ISE & 802.1X

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Cisco ISE](https://img.shields.io/badge/Cisco-ISE%203.2-blue?logo=cisco)
![802.1X](https://img.shields.io/badge/Protocol-802.1X-green)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![Status](https://img.shields.io/badge/Status-Active-brightgreen)
![Zero Trust](https://img.shields.io/badge/Framework-Zero%20Trust-red)

---

## 📖 Overview

This repository documents the design, implementation, and testing of a **Zero Trust Network Access Control** solution using **Cisco Identity Services Engine (ISE)** and **IEEE 802.1X** port-based authentication. The project demonstrates how organizations can move away from the traditional "trust but verify" perimeter model toward a **"never trust, always verify"** architecture.

Cisco ISE acts as the central **Policy Decision Point (PDP)**, enforcing granular access control based on identity, device posture, and contextual attributes. Combined with 802.1X on Cisco switches acting as **Policy Enforcement Points (PEP)**, this solution ensures that every endpoint is authenticated, authorized, and continuously validated before gaining access to network resources.

### Key Capabilities Demonstrated:
- **Identity-based access** using Active Directory integration with EAP-TLS and PEAP-MSCHAPv2
- **Device profiling** for automatic classification of endpoints (PC, IoT, Printer, etc.)
- **Posture assessment** to enforce compliance (antivirus, OS patch level)
- **Dynamic VLAN assignment** and **Downloadable ACLs (dACLs)** for micro-segmentation
- **Security Group Tags (SGT)** for TrustSec-based east-west segmentation
- **Change of Authorization (CoA)** for real-time policy enforcement
- **MAB (MAC Authentication Bypass)** for non-802.1X capable devices
- **Guest portal** with self-registration and sponsor approval flow
- **REST API automation** for endpoint management and audit

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔑 **802.1X Authentication** | Wired port authentication using EAP-TLS / PEAP-MSCHAPv2 |
| 🏷️ **MAB Fallback** | MAC Authentication Bypass for printers, VoIP phones, IoT |
| 🩺 **Posture Assessment** | Checks AV, firewall, patch status before granting full access |
| 🌐 **Guest Portal** | Self-service registration with time-limited internet-only access |
| 🔒 **Dynamic ACLs** | Per-session downloadable ACLs pushed by ISE on authentication |
| 🏷️ **SGT / TrustSec** | Security Group Tagging for scalable policy in the data center |
| ↩️ **CoA Support** | Real-time session re-authorization when posture changes |
| 📊 **VLAN Segmentation** | Employees, contractors, IoT, and guests in isolated VLANs |
| 🐍 **Python Automation** | API scripts for audit, quarantine, and session management |
| 📋 **GNS3/EVE-NG Ready** | Full lab topology documented and reproducible in emulators |

---

## 📁 Repository Structure

```
zero-trust-cisco-ise/
│
├── README.md                          # This file
├── .gitignore                         # Git ignore rules
│
├── configs/
│   ├── switches/
│   │   ├── core-switch.cfg            # Core switch full IOS config
│   │   ├── access-switch-01.cfg       # Access switch 01 with 802.1X
│   │   ├── access-switch-02.cfg       # Access switch 02 with 802.1X
│   │   └── radius-test-commands.md    # Verification & troubleshooting commands
│   │
│   └── ise-policies/
│       ├── authentication-policy.md   # ISE Authentication Policy sets
│       ├── authorization-policy.md    # ISE Authorization rules & VLAN/dACL mapping
│       └── dacl-definitions.md        # Downloadable ACL definitions
│
├── topology/
│   └── network-topology.md            # ASCII topology, IP table, VLAN table
│
├── scripts/
│   ├── python/
│   │   ├── ise_api_check.py           # ISE ERS API: sessions, quarantine, posture
│   │   ├── vlan_audit.py              # Netmiko: 802.1X session audit to CSV
│   │   └── requirements.txt           # Python dependencies
│   │
│   └── testing/
│       └── test-plan.md               # Test cases for 802.1X, posture, CoA, etc.
│
├── docs/
│   ├── setup-guide.md                 # Full lab setup: GNS3/EVE-NG, ISE, AD, supplicants
│   └── zero-trust-concepts.md         # Zero Trust theory, pillars, Cisco framework
│
└── report/
    └── project-report-template.md     # Formal project report template
```

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/youruser/zero-trust-cisco-ise.git
cd zero-trust-cisco-ise
```

### 2. Set Up the Lab Environment
Follow [`docs/setup-guide.md`](docs/setup-guide.md) to:
- Deploy ISE 3.2 OVA in VMware/EVE-NG
- Configure GNS3/EVE-NG topology
- Integrate Active Directory

### 3. Apply Switch Configurations
```bash
# Copy configs to your switches via console or SCP
# Core switch
copy tftp://192.168.1.50/core-switch.cfg running-config

# Access switches
copy tftp://192.168.1.50/access-switch-01.cfg running-config
```

### 4. Install Python Dependencies
```bash
cd scripts/python
pip install -r requirements.txt
```

### 5. Run ISE API Audit
```bash
# Edit ise_api_check.py to set your ISE IP, credentials
python ise_api_check.py
```

### 6. Run VLAN/Auth Audit
```bash
# Edit vlan_audit.py to set switch IPs and credentials
python vlan_audit.py
```

### 7. Verify Authentication on Switches
```
SW-ACCESS-01# show authentication sessions
SW-ACCESS-01# show dot1x all
SW-ACCESS-01# test aaa group RADIUS-SERVERS testuser testpass new-code
```

---

## 🛠️ Lab Requirements

### Hardware (Physical Lab)
| Component | Model | Quantity |
|---|---|---|
| Core Switch | Cisco Catalyst 3750/3850/9300 | 1 |
| Access Switches | Cisco Catalyst 2960-X / 3560 | 2 |
| Server | ESXi host (16GB RAM, 4 vCPUs) | 1 |
| Test PCs | Windows 10/11 endpoints | 2–4 |
| IP Phone | Cisco 7900 series | 1 (optional) |

### Software (Virtual Lab — GNS3 / EVE-NG)
| Software | Version | Notes |
|---|---|---|
| Cisco ISE | 3.2 or 3.3 | Requires 12GB RAM VM minimum |
| Cisco IOS | 15.2(4) or later | For switches (IOU/VIRL images) |
| Windows Server | 2019 / 2022 | Active Directory + DNS + NTP |
| GNS3 / EVE-NG | Latest | Network emulator |
| Cisco AnyConnect | 4.10+ | 802.1X supplicant (optional) |
| Wireshark | 4.x | Packet capture for EAP analysis |
| Python | 3.10+ | For automation scripts |

### Network Requirements
- ISE node reachable from all switches on UDP 1812 / 1813
- Syslog port UDP 514 open from switches to ISE
- DNS resolving ISE FQDN from all devices
- NTP synchronized across all devices

---

## 🧰 Technologies Used

| Technology | Role |
|---|---|
| **Cisco ISE 3.2** | Central AAA — authentication, authorization, accounting |
| **IEEE 802.1X** | Port-based Network Access Control (PNAC) |
| **RADIUS (RFC 2865/3579)** | Authentication protocol between switch and ISE |
| **EAP-TLS (RFC 5216)** | Certificate-based mutual authentication |
| **PEAP-MSCHAPv2** | Password-based EAP with AD credentials |
| **MAB** | MAC Authentication Bypass for headless devices |
| **TrustSec / SGT** | Scalable Group Tags for east-west policy |
| **dACL** | Downloadable Access Control Lists per session |
| **CoA (RFC 5176)** | Dynamic authorization changes mid-session |
| **OSPF** | Layer 3 routing between VLANs/SVIs |
| **DHCP Snooping** | Layer 2 security against rogue DHCP servers |
| **Dynamic ARP Inspection** | ARP spoofing prevention |
| **Cisco ERS API** | REST API for ISE programmatic management |
| **Netmiko** | Python SSH library for Cisco device automation |
| **Active Directory** | Identity store for user/machine authentication |

---

## 🗺️ Roadmap

### Phase 1 — Foundation (Weeks 1–2) ✅
- [x] Network topology design and IP addressing
- [x] Core and access switch base configuration
- [x] ISE initial setup and AD integration
- [x] RADIUS configuration on switches
- [x] 802.1X global enable and basic port config

### Phase 2 — Authentication Policies (Weeks 3–4) ✅
- [x] ISE Policy Sets: Wired_802.1X, Wired_MAB
- [x] EAP-TLS with machine certificates
- [x] PEAP-MSCHAPv2 with AD credentials
- [x] MAB for IP phones and printers
- [x] VLAN assignment via authorization policy

### Phase 3 — Advanced Authorization (Weeks 5–6) ✅
- [x] dACL definitions and assignment
- [x] Posture policy with Cisco Temporal Agent
- [x] SGT assignment and TrustSec propagation
- [x] CoA triggers for posture compliance failure
- [x] Guest portal with self-registration

### Phase 4 — Automation & Monitoring (Week 7–8) 🔄
- [x] Python ISE ERS API scripts
- [x] Netmiko VLAN audit script
- [ ] Splunk/Syslog dashboard for auth events
- [ ] Automated quarantine on threat detection

### Phase 5 — Testing & Documentation (Week 9–10) 🔄
- [x] Test plan with 10+ test cases
- [ ] All test cases executed and results recorded
- [x] Setup guide and concept documentation
- [ ] Final project report

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2024 Zero Trust ISE Lab Project

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
```

---

## 👤 Author

**Zero Trust Network Lab Project**

- 🏫 Department of Computer Networks & Cybersecurity
- 📧 Contact: network-lab@university.edu
- 🔗 GitHub: [github.com/youruser/zero-trust-cisco-ise](https://github.com/youruser/zero-trust-cisco-ise)

### Acknowledgements
- Cisco Systems documentation and dCloud labs
- IEEE 802.1X standard working group
- NIST SP 800-207 Zero Trust Architecture guidelines
- EVE-NG community for networking lab resources

---

> **Disclaimer:** This project is for educational and lab purposes only. All IP addresses, credentials shown in configs are examples and should never be used in production without proper security hardening.
