# Downloadable ACL (dACL) Definitions

## Overview

**Downloadable ACLs (dACLs)** are ACLs stored centrally on Cisco ISE and pushed to the Network Access Device (switch) dynamically upon successful authentication. Unlike static ACLs configured on each switch interface, dACLs are managed in one place and applied per-session, enabling fine-grained, identity-based traffic control regardless of which port a user connects from.

### How dACLs Work

```
1. Endpoint authenticates (802.1X / MAB)
2. ISE evaluates Authorization Policy → matches Employee_Compliant rule
3. ISE sends Access-Accept with:
      Cisco-AVPair = "ip:inacl#1=permit ip any any"
      (or references a named dACL)
4. Switch creates a per-session ACL and applies it ingress on the port
5. Traffic from the endpoint is filtered by this ACL
6. When session ends, ACL is removed automatically
```

Navigate in ISE: **Policy > Policy Elements > Results > Authorization > Downloadable ACLs**

---

## dACL: PERMIT_ALL_TRAFFIC

**Purpose**: Full network access for compliant employee endpoints. Assigned to employees who have passed posture assessment.

**Assigned to Authorization Profile**: `EMPLOYEE_FULL_ACCESS`  
**Applied to**: VLAN 10 (Employees)  
**SGT**: Employee (10)

```
! dACL Name: PERMIT_ALL_TRAFFIC
! Applied to: Compliant Employees
! VLAN: 10

remark Allow all IP traffic (inbound from endpoint)
permit ip any any
```

> **Note**: Although this ACL is permissive, the SGT-based policy matrix (SGACL) still controls east-west traffic between Security Groups. The dACL controls what the endpoint can send; SGACL controls what can flow between groups.

**ISE Configuration:**
- **Name**: `PERMIT_ALL_TRAFFIC`
- **IP version**: `IPv4`
- **DACL Content**:
  ```
  permit ip any any
  ```

---

## dACL: PERMIT_INTERNET_ONLY

**Purpose**: Allow only internet-bound traffic (HTTP, HTTPS, DNS). Blocks all access to internal RFC 1918 address ranges. Applied to Guests and Contractors without server access.

**Assigned to Authorization Profiles**: `GUEST_INTERNET_ACCESS`, `CONTRACTOR_LIMITED_ACCESS`  
**Applied to**: VLAN 20 (Contractors), VLAN 40 (Guests)  
**SGT**: Contractor (20), Guest (40)

```
! dACL Name: PERMIT_INTERNET_ONLY
! Applied to: Guest and Contractor sessions
! Blocks all internal RFC 1918 access

remark Deny access to RFC 1918 internal ranges
deny ip any 10.0.0.0 0.255.255.255
deny ip any 172.16.0.0 0.15.255.255
deny ip any 192.168.0.0 0.0.255.255

remark Allow DNS (UDP 53)
permit udp any any eq 53

remark Allow HTTP (TCP 80)
permit tcp any any eq 80

remark Allow HTTPS (TCP 443)
permit tcp any any eq 443

remark Allow NTP (UDP 123) for time sync
permit udp any any eq 123

remark Allow DHCP (UDP 67/68)
permit udp any any eq 67
permit udp any any eq 68

remark Allow ICMP ping for basic connectivity
permit icmp any any echo
permit icmp any any echo-reply

remark Deny everything else
deny ip any any
```

**ISE Configuration:**
- **Name**: `PERMIT_INTERNET_ONLY`
- **IP version**: `IPv4`
- **DACL Content**: (paste ACL text above without `remark` lines if needed)

---

## dACL: PERMIT_IOT_ISOLATED

**Purpose**: Highly restrictive ACL for IoT devices. Only permits communication to the designated IoT management server on specific application ports. Prevents IoT devices from reaching any other internal systems or the internet directly.

**Assigned to Authorization Profile**: `IOT_DEVICE_ACCESS`  
**Applied to**: VLAN 30 (IoT)  
**SGT**: IoT (30)  
**IoT Management Server**: `192.168.200.20`

```
! dACL Name: PERMIT_IOT_ISOLATED
! Applied to: IoT devices (cameras, sensors, printers)
! Only allows specific ports to dedicated IoT server

remark Allow DHCP
permit udp any host 255.255.255.255 eq 67
permit udp any any eq 68

remark Allow DNS to internal DNS server only
permit udp any host 192.168.200.10 eq 53
permit tcp any host 192.168.200.10 eq 53

remark Allow MQTT (TCP 1883) to IoT server - unencrypted
permit tcp any host 192.168.200.20 eq 1883

remark Allow MQTT over TLS (TCP 8883) to IoT server
permit tcp any host 192.168.200.20 eq 8883

remark Allow CoAP (UDP 5683) to IoT server
permit udp any host 192.168.200.20 eq 5683

remark Allow SNMP trap (UDP 162) to IoT server for managed devices
permit udp any host 192.168.200.20 eq 162

remark Allow ICMP to IoT server only (for health checks)
permit icmp any host 192.168.200.20

remark Allow NTP to IoT server
permit udp any host 192.168.200.20 eq 123

remark Allow HTTP to IoT server for firmware updates
permit tcp any host 192.168.200.20 eq 80
permit tcp any host 192.168.200.20 eq 443

remark Deny all RFC 1918 access (inter-IoT and other internal)
deny ip any 10.0.0.0 0.255.255.255
deny ip any 172.16.0.0 0.15.255.255
deny ip any 192.168.0.0 0.0.255.255

remark Deny all internet access
deny ip any any
```

**ISE Configuration:**
- **Name**: `PERMIT_IOT_ISOLATED`
- **IP version**: `IPv4`
- **DACL Content**: (paste ACL entries above)

---

## dACL: DENY_ALL

**Purpose**: Complete traffic block for quarantined endpoints — non-compliant devices, failed authentication (via auth fail VLAN), or manually quarantined endpoints. Only allows DHCP, DNS to ISE, and HTTPS to the ISE remediation portal so that the user can see a redirect page.

**Assigned to Authorization Profile**: `QUARANTINE_ACCESS`  
**Applied to**: VLAN 99 (Quarantine)  
**SGT**: Quarantine (99)

```
! dACL Name: DENY_ALL
! Applied to: Quarantined / non-compliant / unknown endpoints
! Permits ONLY remediation portal access

remark Allow DHCP to get IP address
permit udp any any eq 67
permit udp any any eq 68

remark Allow DNS to internal DNS only
permit udp any host 192.168.200.10 eq 53

remark Allow HTTPS to ISE for guest/remediation portal only
permit tcp any host 192.168.1.100 eq 8443

remark Allow ISE posture redirect target
permit tcp any host 192.168.1.100 eq 443
permit tcp any host 192.168.1.100 eq 80

remark Allow ICMP only to ISE (for redirect to work)
permit icmp any host 192.168.1.100

remark Deny all other traffic
deny ip any any log
```

**ISE Configuration:**
- **Name**: `DENY_ALL`
- **IP version**: `IPv4`
- **DACL Content**: (paste ACL entries above)

---

## dACL: PERMIT_REMEDIATION

**Purpose**: For endpoints where posture status is "Unknown" (supplicant just connected, posture agent not yet run). Allows internet access and ISE communication so the AnyConnect posture module can download and run. Triggers a redirect to the AnyConnect download page.

**Assigned to Authorization Profile**: `EMPLOYEE_POSTURE_UNKNOWN`  
**Applied to**: VLAN 10 (temporary until posture completes)  
**SGT**: Employee (10)

```
! dACL Name: PERMIT_REMEDIATION
! Applied to: Employees with unknown posture status
! Allows ISE communication + internet for AnyConnect download

remark Allow DHCP
permit udp any any eq 67
permit udp any any eq 68

remark Allow DNS
permit udp any any eq 53

remark Allow ISE for posture assessment
permit tcp any host 192.168.1.100 eq 443
permit tcp any host 192.168.1.100 eq 8443
permit tcp any host 192.168.1.100 eq 8905
permit udp any host 192.168.1.100 eq 8905
permit tcp any host 192.168.1.100 eq 8906

remark Allow internet for AnyConnect download and updates
permit tcp any any eq 80
permit tcp any any eq 443

remark Allow ICMP for diagnostics
permit icmp any any

remark Deny internal resources until posture is confirmed
deny ip any 10.0.0.0 0.255.255.255
deny ip any 172.16.0.0 0.15.255.255
deny ip any 192.168.0.0 0.0.255.255

remark Deny all other
deny ip any any
```

---

## dACL: VOIP_PERMIT

**Purpose**: Permit voice and signaling traffic for Cisco IP Phones. Applied to voice VLAN ports.

**Assigned to Authorization Profile**: `VOIP_PHONE_ACCESS`  
**Applied to**: VLAN 50 (VoIP)  
**SGT**: VoIP (50)

```
! dACL Name: VOIP_PERMIT
! Applied to: Cisco IP Phones (MAB profiled)

remark Allow DHCP
permit udp any any eq 67
permit udp any any eq 68

remark Allow DNS
permit udp any host 192.168.200.10 eq 53

remark Allow SCCP (Skinny) to CUCM
permit tcp any 192.168.200.0 0.0.0.255 eq 2000

remark Allow SIP to CUCM
permit tcp any 192.168.200.0 0.0.0.255 eq 5060
permit udp any 192.168.200.0 0.0.0.255 eq 5060
permit tcp any 192.168.200.0 0.0.0.255 eq 5061

remark Allow RTP/RTCP media streams (dynamic ports)
permit udp any any range 16384 32767

remark Allow TFTP to CUCM for phone firmware
permit udp any 192.168.200.0 0.0.0.255 eq 69

remark Allow NTP
permit udp any any eq 123

remark Allow ICMP
permit icmp any any

remark Deny all other traffic
deny ip any any
```

---

## Summary Table

| dACL Name | Purpose | Key Allowed Traffic | Assigned To |
|---|---|---|---|
| `PERMIT_ALL_TRAFFIC` | Full access | All IP | Compliant Employees |
| `PERMIT_INTERNET_ONLY` | Internet only | HTTP, HTTPS, DNS | Guests, Contractors |
| `PERMIT_IOT_ISOLATED` | IoT isolation | MQTT, CoAP to IoT server only | IoT Devices |
| `DENY_ALL` | Full block + remediation | DHCP, DNS, ISE portal only | Quarantine |
| `PERMIT_REMEDIATION` | Posture pending | ISE, DNS, internet | Unknown Posture |
| `VOIP_PERMIT` | Voice only | SCCP, SIP, RTP, TFTP | IP Phones |

---

## Important Notes

> **ACL Order**: Cisco ACLs are processed top-to-bottom; the first matching statement wins. Place more specific `deny` entries before broader `permit` entries.

> **dACL vs Port ACL**: A dACL overrides a static port ACL during an authenticated session. After the session ends (port goes unauthorized), the original static config resumes.

> **IPv6**: If IPv6 is in use, create corresponding `IPv6` dACLs and assign them in the Authorization Profile under **DACL Name (IPv6)**.

> **Testing dACLs**: Use `show ip access-lists` on the switch during an active session to verify the dACL was downloaded and applied. The session-specific ACL will appear as `Auth-proxy-...` or with a dynamic name.
