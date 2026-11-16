# 🔍 Wireshark Packet Captures & Protocol Analysis

This directory contains reference packet captures (`.pcap`) demonstrating key control plane protocols in the Cisco ISE Zero Trust Network Access Control architecture.

---

## 📦 Captured Trace Files

| File | Protocol(s) | Ports / EtherType | Description |
|---|---|---|---|
| [`8021x_eap_tls_auth.pcap`](8021x_eap_tls_auth.pcap) | 802.1X, EAPOL, EAP-TLS | EtherType `0x888E` | Port-based network authentication sequence (Supplicant ↔ Switch) |
| [`radius_cisco_ise_avpair.pcap`](radius_cisco_ise_avpair.pcap) | RADIUS, UDP | Ports `1812`, `1813` | AAA Access-Request and Access-Accept with Cisco Vendor-Specific Attributes (dACL, VLAN) |
| [`rfc5176_coa_quarantine.pcap`](rfc5176_coa_quarantine.pcap) | RADIUS CoA (RFC 5176) | UDP Port `3799` | Dynamic Change of Authorization: Re-authentication & Posture Quarantine push |

---

## 🔬 Deep-Dive Protocol Breakdowns

### 1. 802.1X / EAP-TLS Handshake Flow
```
Supplicant (PC)               Switch (Authenticator)              Cisco ISE (Auth Server)
     │                                   │                                    │
     │─── EAPOL-Start ──────────────────>│                                    │
     │<── EAP-Request / Identity ────────│                                    │
     │─── EAP-Response / Identity ──────>│─── RADIUS Access-Request (Identity)─>│
     │                                   │<── RADIUS Access-Challenge (TLS)──│
     │<── EAP-Request / EAP-TLS Start ───│                                    │
     │─── EAP-Response / Client-Hello ──>│─── RADIUS Access-Request (TLS)────>│
     │                                   │<── RADIUS Access-Challenge ───────│
     │<── EAP-Request / Server-Hello, ───│                                    │
     │    Certificate, ServerKeyExchange │                                    │
     │─── EAP-Response / Certificate, ───>│─── RADIUS Access-Request (TLS)────>│
     │    ClientKeyExchange, Finished    │                                    │
     │                                   │<── RADIUS Access-Accept ──────────│
     │<── EAP-Success ───────────────────│    (Includes VLAN 10 + dACL)       │
     │                                   │                                    │
[Port State: Authorized]                 │                                    │
```

#### Key Frame Attributes in `8021x_eap_tls_auth.pcap`:
- **EtherType**: `0x888E` (802.1X Authentication)
- **EAPOL Type**: `1` (EAP-Packet), `2` (EAPOL-Start), `3` (EAPOL-Logoff)
- **EAP Code**: `1` (Request), `2` (Response), `3` (Success), `4` (Failure)
- **EAP Type**: `13` (EAP-TLS - RFC 5216)

---

### 2. RADIUS Access-Accept & Cisco AV-Pairs

When Cisco ISE validates the supplicant certificate and AD group membership, it responds with **RADIUS Access-Accept (Code 2)** containing dynamic enforcement attributes:

```yaml
RADIUS Attributes:
  - Code: 2 (Access-Accept)
  - Tunnel-Type (64): VLAN (13)
  - Tunnel-Medium-Type (65): 802 (6)
  - Tunnel-Private-Group-ID (81): "10"
  - Vendor-Specific (26): Cisco (9)
      - cisco-av-pair: "ACS:inacl#1=permit ip any any"
      - cisco-av-pair: "profile-name=EMPLOYEE_FULL_ACCESS"
```

---

### 3. RFC 5176 Dynamic Change of Authorization (CoA)

Triggered when posture assessment changes (e.g., endpoint disables antivirus or fails OS compliance check):

```
Cisco ISE (PAN / PDP)                    Cisco Catalyst Switch (PEP)
         │                                            │
         │─── CoA-Request (Code 43, Port 3799) ──────>│
         │    Cisco-AVPair: subscriber:command=reauth  │
         │    Cisco-AVPair: audit-session-id=C0A8...   │
         │    Cisco-AVPair: dacl=DACL-QUARANTINE      │
         │                                            │
         │<── CoA-ACK (Code 44) ──────────────────────│
         │                                            │
[Switch transitions session to Quarantine VLAN 99 with restrictive dACL]
```

---

## 🛠️ Wireshark Display Filters

| Analysis Task | Wireshark Filter |
|---|---|
| Filter all 802.1X / EAPOL traffic | `eapol` |
| Filter EAP-TLS protocol packets | `eap.type == 13` |
| Filter RADIUS Authentication | `radius.code == 1 || radius.code == 2` |
| Filter RADIUS Dynamic CoA | `udp.port == 3799` |
| Filter Cisco Vendor-Specific Attributes | `radius.Cisco_AVPair` |
| Filter EAP Success / Failure results | `eap.code == 3 || eap.code == 4` |
