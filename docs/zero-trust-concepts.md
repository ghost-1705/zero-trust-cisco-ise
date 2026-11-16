# Zero Trust Network — Concepts and Framework

## 1. What is Zero Trust?

**Zero Trust** is a cybersecurity strategy and framework built on the principle: **"Never trust, always verify."**

Traditional security models assumed that everything *inside* the corporate network perimeter was trustworthy. Zero Trust discards this notion entirely. Instead, it treats every access request — from inside or outside the network — as potentially compromised and requires explicit verification of:

- **Who** is making the request (identity)
- **What** device they are using (device health)
- **Where** they are (network context)
- **What** they are trying to access (resource sensitivity)
- **When** (time-based access)

> *"Zero trust is a security concept centered on the belief that organizations should not automatically trust anything inside or outside their perimeters and instead must verify anything and everything trying to connect to its systems before granting access."*  
> — John Kindervag, Forrester Research (originator of the Zero Trust concept, 2010)

---

## 2. The Five Zero Trust Pillars

NIST SP 800-207 and Cisco's framework both describe Zero Trust through key pillars:

### Pillar 1: Identity
- Verify **who** the user is using strong authentication (MFA, certificates)
- Continuously validate identity — not just at login
- Apply least-privilege access based on role

**ISE mapping**: Active Directory integration, 802.1X user authentication, identity-based policy sets

### Pillar 2: Devices
- Assess **device health** before granting access (posture)
- Classify devices by type (corporate, BYOD, IoT)
- Block or restrict non-compliant or unknown devices

**ISE mapping**: Endpoint profiling, posture assessment (AV, patch, firewall), dACL enforcement

### Pillar 3: Networks
- Assume the network is **hostile** — both internal and external
- Microsegment the network; limit lateral movement
- Encrypt traffic in transit (TLS, MACsec)

**ISE mapping**: VLAN segmentation, SGT/TrustSec, 802.1X port-based access control, dACLs

### Pillar 4: Applications
- Control access to applications based on identity and device, not IP address
- Use application-layer policies (not just network-layer)
- Integrate with identity providers (SSO, SAML)

**ISE mapping**: URL redirect ACLs for application-based redirection, Cisco Duo MFA integration

### Pillar 5: Data
- Classify data by sensitivity
- Apply data-centric policies regardless of network location
- Monitor and log all data access

**ISE mapping**: Logging all RADIUS events to SIEM, TrustSec SGT-based data access control

---

## 3. Traditional Perimeter Security vs. Zero Trust

| Dimension | Traditional (Castle-and-Moat) | Zero Trust |
|---|---|---|
| **Trust Model** | Trust everything inside the firewall | Trust nothing; verify everything |
| **Network Boundary** | Hard perimeter (firewall at edge) | No implicit perimeter; identity is the perimeter |
| **User Verification** | Once at VPN login | Continuously — every session and resource |
| **Device Trust** | "On the corporate network = trusted" | Device posture verified before access |
| **Lateral Movement** | Easy — once inside, roam freely | Blocked — microsegmentation limits blast radius |
| **Remote Access** | VPN gives full LAN access | Per-app, per-identity, least-privilege access |
| **Insider Threats** | Difficult to detect/contain | Limited by least-privilege; monitored continuously |
| **Cloud/BYOD** | Struggles to handle off-network | Native to identity-based model |
| **Logging** | Perimeter-focused (firewall logs) | Everywhere — network, endpoint, app, data |

**Key insight**: The traditional perimeter model fails in a world of cloud, BYOD, remote work, and sophisticated attackers who can bypass edge controls. Zero Trust assumes breach and limits blast radius.

---

## 4. Cisco Zero Trust Framework

Cisco's Zero Trust framework — called **Cisco Secure Zero Trust** — is organized into three main planes:

```
┌───────────────────────────────────────────────────────────────┐
│                 CISCO ZERO TRUST FRAMEWORK                    │
│                                                               │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │  WORKFORCE  │  │  WORKLOADS   │  │    WORKPLACE         │ │
│  │             │  │              │  │                      │ │
│  │ Who is      │  │ What apps    │  │ What network, where  │ │
│  │ accessing?  │  │ are running? │  │ device is connecting │ │
│  │             │  │              │  │                      │ │
│  │ Cisco Duo   │  │ Cisco AppD   │  │ Cisco ISE            │ │
│  │ (MFA/SSO)   │  │ Tetration    │  │ 802.1X, Profiling    │ │
│  │ ISE + AD    │  │ Secure Cloud │  │ Segmentation         │ │
│  └─────────────┘  └──────────────┘  └──────────────────────┘ │
│                                                               │
│  Underpinned by: Cisco SecureX / XDR — Unified Visibility     │
└───────────────────────────────────────────────────────────────┘
```

### Cisco Duo (Workforce)
- Multi-Factor Authentication (MFA) for all user logins
- Device trust assessment (Duo Device Health App)
- SSO via SAML for cloud applications
- Integrates with ISE for posture signals

### Cisco ISE (Workplace)
- 802.1X Network Access Control
- Device profiling and classification
- Policy Decision Point (PDP) for network access
- TrustSec / SGT for east-west segmentation
- Guest lifecycle management

### Cisco Umbrella (DNS Security)
- DNS-layer security — blocks malicious domains
- Cloud-delivered SWG (Secure Web Gateway)
- Works for on-prem and remote users

### Cisco Stealthwatch / Secure Network Analytics
- Network traffic analysis (NetFlow)
- Encrypted Traffic Analytics (ETA) — detects threats in TLS traffic
- Behavioral analytics for insider threats and lateral movement
- Sends threat feeds back to ISE for automated response (pxGrid)

### Cisco pxGrid
- **Policy Exchange Grid** — the integration layer between ISE and security tools
- Allows Stealthwatch, Firepower, Splunk, etc. to share and act on context (who is on what IP)
- Enables automated quarantine: Stealthwatch detects anomaly → pxGrid signals ISE → ISE sends CoA to quarantine endpoint

---

## 5. How 802.1X and ISE Map to Zero Trust

| Zero Trust Principle | ISE / 802.1X Implementation |
|---|---|
| Verify explicitly | 802.1X requires auth before any network access; EAP-TLS uses mutual certificates |
| Use least-privilege access | dACLs and VLANs limit what an authenticated user can reach |
| Assume breach | Posture checks verify device health; CoA quarantines compromised devices |
| Continuous monitoring | RADIUS accounting tracks all sessions; pxGrid shares context with SIEM |
| Microsegmentation | SGT/TrustSec tags traffic; SGACL policies control inter-group communication |
| Identity as the perimeter | Authorization is based on identity (AD group), not IP address |

---

## 6. Zero Trust Maturity Model

CISA (Cybersecurity and Infrastructure Security Agency) defines a Zero Trust Maturity Model with three stages:

| Stage | Description | 802.1X/ISE Status in This Lab |
|---|---|---|
| **Traditional** | Perimeter-based, no microsegmentation, implicit trust | — (before project) |
| **Initial** | 802.1X deployed, VLAN segmentation, identity-based authz | ✅ Core deployment |
| **Advanced** | Posture-aware, CoA, automated response via pxGrid/XDR | ✅ Phase 3 of this project |
| **Optimal** | AI-driven, continuous adaptive auth, full workload coverage | 🔄 Future roadmap |

---

## 7. Glossary of Terms

| Term | Definition |
|---|---|
| **AAA** | Authentication, Authorization, and Accounting — the three functions of network access control |
| **Authentication** | Verifying *who* a user or device is (e.g., password, certificate, MAC address) |
| **Authorization** | Deciding *what* an authenticated user is allowed to do (VLAN, ACL, SGT) |
| **Accounting** | Recording *what* a user did during their session (start/stop logs, session duration) |
| **RADIUS** | Remote Authentication Dial-In User Service — protocol (UDP 1812/1813) used between switch and ISE |
| **EAP** | Extensible Authentication Protocol — framework for 802.1X authentication methods |
| **EAP-TLS** | EAP with Transport Layer Security — uses X.509 certificates for mutual authentication |
| **PEAP** | Protected EAP — tunnels inner EAP method (MSCHAPv2) inside a TLS session |
| **MAB** | MAC Authentication Bypass — authenticates devices using their MAC address when no 802.1X supplicant is present |
| **NAS** | Network Access Server — the switch or wireless AP that enforces access control |
| **PDP** | Policy Decision Point — ISE decides whether to allow/deny and what policy applies |
| **PEP** | Policy Enforcement Point — the switch that enforces the PDP decision |
| **dACL** | Downloadable ACL — an ACL stored in ISE, pushed to the switch per session via RADIUS |
| **CoA** | Change of Authorization (RFC 5176) — allows ISE to modify an active session's policy without disconnecting |
| **SGT** | Security Group Tag — a numeric label (2 bytes) embedded in traffic for group-based policy |
| **TrustSec** | Cisco's proprietary framework using SGTs for scalable group-based policy in the data center |
| **SGACL** | Security Group ACL — the policy defining what SGT X can communicate with SGT Y |
| **NAC** | Network Access Control — the broader category of technologies that control endpoint access |
| **Posture** | Assessment of a device's security health (AV status, OS patches, firewall, encryption) |
| **Profiling** | ISE's ability to automatically classify device types using DHCP, CDP, LLDP, HTTP user agents, Nmap |
| **pxGrid** | Cisco's Policy Exchange Grid — integration platform for sharing identity/security context between products |
| **ISE** | Identity Services Engine — Cisco's central AAA and policy platform |
| **ERS** | External RESTful Services — ISE's REST API for programmatic management |
| **MnT** | Monitoring and Troubleshooting — ISE's logging and analytics node |
| **SVI** | Switched Virtual Interface — a Layer 3 interface on a switch that acts as the VLAN gateway |
| **VLAN** | Virtual Local Area Network — logical network segmentation at Layer 2 |
| **Trunk** | A link carrying multiple VLANs (tagged with 802.1Q) between switches |
| **PortFast** | Cisco STP feature that bypasses listening/learning states for access ports |
| **BPDUGuard** | Cisco STP feature that disables a port if BPDU frames are received (prevents rogue switches) |
| **DHCP Snooping** | Layer 2 security that blocks rogue DHCP servers by trusting only designated uplink ports |
| **DAI** | Dynamic ARP Inspection — validates ARP packets against DHCP snooping binding table to prevent ARP spoofing |
| **Zero Trust** | Security model requiring explicit verification of every user and device before granting access |
| **MFA** | Multi-Factor Authentication — requiring two or more of: something you know, have, or are |
| **PKI** | Public Key Infrastructure — framework for issuing, managing, and revoking digital certificates |
| **RFC 3579** | RADIUS Support for EAP — defines how EAP messages are transported over RADIUS |
| **RFC 5216** | The EAP-TLS Authentication Protocol — certificate-based mutual authentication over EAP |
| **RFC 5176** | Dynamic Authorization Extensions to RADIUS (CoA) — mid-session policy changes |
| **NIST SP 800-207** | NIST's Zero Trust Architecture guide — foundational reference for ZTA design |
