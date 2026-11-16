# Network Topology — Zero Trust 802.1X Lab

## ASCII Topology Diagram

```
                             ┌─────────────────────────────────────────────────┐
                             │              INTERNET / WAN                      │
                             └───────────────────┬─────────────────────────────┘
                                                 │ 172.16.0.1/30
                                          ┌──────┴──────┐
                                          │   FIREWALL   │
                                          │  (ASA/FTD)  │
                                          └──────┬──────┘
                                                 │ 172.16.0.2/30
                                                 │
                             ┌───────────────────┴────────────────────────────────┐
                             │              SW-CORE-01 (Catalyst 3850)            │
                             │          192.168.100.1/24 (Mgmt VLAN 100)         │
                             │   VLAN SVIs: 10.10.10.1, 10.10.20.1, 10.10.30.1  │
                             │              10.10.40.1, 10.10.50.1, 10.10.99.1  │
                             └──────┬──────────────────────────┬─────────────────┘
                                    │ Gi1/0/1 Trunk            │ Gi1/0/2 Trunk
                                    │ VLANs 10,20,30,40,50,99  │ VLANs 10,20,30,40,50,99
                      ┌─────────────┴─────────────┐    ┌───────┴──────────────────────┐
                      │   SW-ACCESS-01             │    │   SW-ACCESS-02               │
                      │   (Catalyst 2960-X)        │    │   (Catalyst 2960-X)          │
                      │   192.168.100.11/24        │    │   192.168.100.12/24          │
                      │   Building A, Floor 1      │    │   Building A, Floor 2        │
                      └──┬──────┬──────┬──────┬───┘    └────┬──────┬──────┬──────┬────┘
                   Gi0/1 │ Gi0/2│ Gi0/3│ Gi0/4│        Gi0/1│ Gi0/2│ Gi0/3│ Gi0/4│
                         │      │      │      │               │      │      │      │
                    [PC1] [PC2][VoIP] [IoT1]            [PC3] [PC4][Guest][Printer]
                  EAP-TLS EAP  Cisco  Camera          PEAP  PEAP  MAB    MAB
                  VLAN 10  TLS  Phone  VLAN 30         VLAN10 VLAN10 VLAN40 VLAN30
                                VLAN50

                                              ┌─────────────────────────────────────┐
                                              │      SERVER VLAN 200               │
                                              │  (Connected to SW-CORE-01 Gi1/0/40)│
                                              │                                     │
                                              │  ┌──────────────────────────────┐   │
                                              │  │ ISE-PRIMARY                  │   │
                                              │  │ Cisco ISE 3.2 (VM)           │   │
                                              │  │ IP: 192.168.1.100/24         │   │
                                              │  │ Ports: 1812,1813,1700,8443   │   │
                                              │  └──────────────────────────────┘   │
                                              │                                     │
                                              │  ┌──────────────────────────────┐   │
                                              │  │ AD-SERVER                    │   │
                                              │  │ Windows Server 2022          │   │
                                              │  │ Active Directory + DNS + CA  │   │
                                              │  │ IP: 192.168.200.10/24        │   │
                                              │  └──────────────────────────────┘   │
                                              │                                     │
                                              │  ┌──────────────────────────────┐   │
                                              │  │ IOT-SERVER                   │   │
                                              │  │ MQTT Broker / IoT Platform   │   │
                                              │  │ IP: 192.168.200.20/24        │   │
                                              │  └──────────────────────────────┘   │
                                              │                                     │
                                              │  ┌──────────────────────────────┐   │
                                              │  │ DHCP-SERVER                  │   │
                                              │  │ Windows DHCP / ISC DHCP      │   │
                                              │  │ IP: 192.168.200.10 (AD Svr)  │   │
                                              │  └──────────────────────────────┘   │
                                              └─────────────────────────────────────┘
```

---

## IP Addressing Table

| Device | Interface | IP Address | Subnet Mask | VLAN | Role |
|---|---|---|---|---|---|
| SW-CORE-01 | Vlan10 (SVI) | 10.10.10.1 | 255.255.255.0 | 10 | Employee gateway |
| SW-CORE-01 | Vlan20 (SVI) | 10.10.20.1 | 255.255.255.0 | 20 | Contractor gateway |
| SW-CORE-01 | Vlan30 (SVI) | 10.10.30.1 | 255.255.255.0 | 30 | IoT gateway |
| SW-CORE-01 | Vlan40 (SVI) | 10.10.40.1 | 255.255.255.0 | 40 | Guest gateway |
| SW-CORE-01 | Vlan50 (SVI) | 10.10.50.1 | 255.255.255.0 | 50 | VoIP gateway |
| SW-CORE-01 | Vlan99 (SVI) | 10.10.99.1 | 255.255.255.0 | 99 | Quarantine gateway |
| SW-CORE-01 | Vlan100 (SVI) | 192.168.100.1 | 255.255.255.0 | 100 | Management gateway |
| SW-CORE-01 | Vlan200 (SVI) | 192.168.200.1 | 255.255.255.0 | 200 | Server gateway |
| SW-CORE-01 | Gi1/0/48 | 172.16.0.2 | 255.255.255.252 | — | WAN/Firewall uplink |
| SW-ACCESS-01 | Vlan100 (SVI) | 192.168.100.11 | 255.255.255.0 | 100 | Management IP |
| SW-ACCESS-02 | Vlan100 (SVI) | 192.168.100.12 | 255.255.255.0 | 100 | Management IP |
| ISE-PRIMARY | eth0 | 192.168.1.100 | 255.255.255.0 | 200 | RADIUS / Admin / Portal |
| ISE-SECONDARY | eth0 | 192.168.1.101 | 255.255.255.0 | 200 | RADIUS failover (opt.) |
| AD-SERVER | NIC0 | 192.168.200.10 | 255.255.255.0 | 200 | AD, DNS, NTP, DHCP, CA |
| IOT-SERVER | NIC0 | 192.168.200.20 | 255.255.255.0 | 200 | MQTT Broker |
| SNMP-MONITOR | NIC0 | 192.168.200.30 | 255.255.255.0 | 200 | SNMP NMS (SolarWinds/PRTG) |
| FIREWALL | inside | 172.16.0.1 | 255.255.255.252 | — | Default gateway for core |
| PC1 (Employee) | NIC | 10.10.10.10 | 255.255.255.0 | 10 | DHCP from AD-SERVER |
| PC2 (Employee) | NIC | 10.10.10.11 | 255.255.255.0 | 10 | DHCP |
| PC3 (Contractor) | NIC | 10.10.20.10 | 255.255.255.0 | 20 | DHCP |
| PC4 (Contractor) | NIC | 10.10.20.11 | 255.255.255.0 | 20 | DHCP |
| VoIP Phone | NIC | 10.10.50.10 | 255.255.255.0 | 50 | DHCP |
| IoT Camera | NIC | 10.10.30.10 | 255.255.255.0 | 30 | DHCP |
| IoT Printer | NIC | 10.10.30.11 | 255.255.255.0 | 30 | DHCP |
| Guest Laptop | NIC | 10.10.40.10 | 255.255.255.0 | 40 | DHCP |

---

## VLAN Table

| VLAN ID | Name | Subnet | Gateway | Purpose | Access Level | DHCP Server |
|---|---|---|---|---|---|---|
| 10 | EMPLOYEES | 10.10.10.0/24 | 10.10.10.1 | Corporate endpoints — domain-joined PCs | Full internal access | AD-SERVER |
| 20 | CONTRACTORS | 10.10.20.0/24 | 10.10.20.1 | Third-party contractor devices | Internet + limited servers | AD-SERVER |
| 30 | IOT_DEVICES | 10.10.30.0/24 | 10.10.30.1 | Cameras, sensors, printers | IoT server only | AD-SERVER |
| 40 | GUEST | 10.10.40.0/24 | 10.10.40.1 | Visitor devices — internet only | Internet only | AD-SERVER |
| 50 | VOIP | 10.10.50.0/24 | 10.10.50.1 | Cisco IP Phones | CUCM + voice only | AD-SERVER |
| 99 | QUARANTINE | 10.10.99.0/24 | 10.10.99.1 | Non-compliant / unknown / failed auth | ISE portal only | AD-SERVER |
| 100 | MANAGEMENT | 192.168.100.0/24 | 192.168.100.1 | Switch management traffic | Infrastructure only | Static/ISE |
| 200 | SERVERS | 192.168.200.0/24 | 192.168.200.1 | ISE, AD, IoT servers | Server-to-server | Static |

---

## Routing Table Summary (SW-CORE-01)

| Destination | Mask | Next-Hop / Exit Interface | Protocol | Metric |
|---|---|---|---|---|
| 10.10.10.0 | /24 | Vlan10 (directly connected) | C | — |
| 10.10.20.0 | /24 | Vlan20 (directly connected) | C | — |
| 10.10.30.0 | /24 | Vlan30 (directly connected) | C | — |
| 10.10.40.0 | /24 | Vlan40 (directly connected) | C | — |
| 10.10.50.0 | /24 | Vlan50 (directly connected) | C | — |
| 10.10.99.0 | /24 | Vlan99 (directly connected) | C | — |
| 192.168.100.0 | /24 | Vlan100 (directly connected) | C | — |
| 192.168.200.0 | /24 | Vlan200 (directly connected) | C | — |
| 172.16.0.0 | /30 | Gi1/0/48 (directly connected) | C | — |
| 0.0.0.0 | /0 | 172.16.0.1 (Firewall) | S | 1 |

---

## DNS Server Details

| Role | Server | IP Address | Zones |
|---|---|---|---|
| Primary DNS | AD-SERVER | 192.168.200.10 | lab.local, reverse zones, ISE FQDN |
| Secondary DNS | (AD replication) | — | Replicated from primary |
| Public DNS (fallback) | Google | 8.8.8.8, 8.8.4.4 | Internet resolution |
| ISE FQDN | ise.lab.local | 192.168.1.100 | Required for guest portal, CoA |

**DNS Records Required:**
```
ise.lab.local        A     192.168.1.100
ise2.lab.local       A     192.168.1.101   (secondary if present)
ad.lab.local         A     192.168.200.10
iot.lab.local        A     192.168.200.20
```

---

## NTP Server Details

| Device | NTP Source | Stratum |
|---|---|---|
| AD-SERVER | pool.ntp.org | 2 |
| SW-CORE-01 | AD-SERVER (192.168.200.10) | 3 |
| SW-ACCESS-01 | SW-CORE-01 (192.168.100.1) | 4 |
| SW-ACCESS-02 | SW-CORE-01 (192.168.100.1) | 4 |
| ISE-PRIMARY | AD-SERVER (192.168.200.10) | 3 |

> **Important**: NTP synchronization is critical for 802.1X/EAP-TLS. Certificate validity checks depend on accurate time. All devices must be within ±5 minutes of each other.

---

## ISE Communication Ports / Protocol Table

| Source | Destination | Port | Protocol | Purpose |
|---|---|---|---|---|
| SW-ACCESS-01/02 | ISE-PRIMARY | 1812 | UDP | RADIUS Authentication |
| SW-ACCESS-01/02 | ISE-PRIMARY | 1813 | UDP | RADIUS Accounting |
| ISE-PRIMARY | SW-ACCESS-01/02 | 3799 | UDP | CoA (Change of Authorization) |
| SW-CORE-01 | ISE-PRIMARY | 1812 | UDP | RADIUS Authentication |
| SW-CORE-01 | ISE-PRIMARY | 1813 | UDP | RADIUS Accounting |
| ISE-PRIMARY | SW-CORE-01 | 3799 | UDP | CoA |
| All Switches | ISE-PRIMARY | 514 | UDP | Syslog |
| Admin Browser | ISE-PRIMARY | 443 | TCP | ISE Admin GUI |
| Guest/Endpoints | ISE-PRIMARY | 8443 | TCP | Guest Portal (HTTPS) |
| AnyConnect Agent | ISE-PRIMARY | 8905 | TCP/UDP | Posture Assessment |
| AnyConnect Agent | ISE-PRIMARY | 8906 | TCP | Posture Profile Update |
| ISE-PRIMARY | AD-SERVER | 389 | TCP/UDP | LDAP (Active Directory) |
| ISE-PRIMARY | AD-SERVER | 636 | TCP | LDAPS (AD secure) |
| ISE-PRIMARY | AD-SERVER | 88 | TCP/UDP | Kerberos (AD auth) |
| ISE-PRIMARY | AD-SERVER | 3268 | TCP | Global Catalog LDAP |
| ISE-PRIMARY | AD-SERVER | 53 | UDP | DNS |
| ISE-PRIMARY | AD-SERVER | 123 | UDP | NTP |
| All Switches | ISE-PRIMARY | — | RADIUS/SNMP | Device management |
| SNMP-MONITOR | All Switches | 161 | UDP | SNMP polling |
| All Switches | SNMP-MONITOR | 162 | UDP | SNMP traps |
