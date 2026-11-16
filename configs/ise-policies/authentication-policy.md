# ISE Authentication Policy Configuration Guide

## Overview

Authentication Policies in Cisco ISE define **how** a network access request is authenticated — which protocols are allowed, which identity sources are queried, and in which order. Authentication policies are grouped inside **Policy Sets**, which act as top-level containers matching traffic by NAS (Network Access Server) attributes before the more granular authentication and authorization rules are evaluated.

---

## Policy Set Structure

```
Policy Set
├── Conditions (match by NAS-IP, Wired, Wireless, VPN, etc.)
├── Allowed Protocols (EAP types permitted)
│
├── Authentication Policy (Who are you?)
│   ├── Rule 1: Wired_802.1X → EAP-TLS / PEAP → AD + Internal CA
│   ├── Rule 2: Wired_MAB    → Host Lookup → Endpoints DB
│   └── Default             → Deny Access
│
└── Authorization Policy (What can you do?)
    ├── Rule 1: AD Group Employees → VLAN 10 + PERMIT_ALL_TRAFFIC
    ├── Rule 2: Profiled IP Phone  → VLAN 50 + VOIP_PERMIT
    └── ...
```

A **Policy Set** is selected based on a condition evaluated at the top level (before drilling into authentication/authorization rules). This allows different policy sets for Wired, Wireless, and VPN.

---

## Policy Sets Defined

### Policy Set 1: Wired_Access

| Field | Value |
|---|---|
| **Name** | Wired_Access |
| **Status** | Enabled |
| **Condition** | `Radius:NAS-Port-Type EQUALS Ethernet` |
| **Allowed Protocols** | Wired_Allowed_Protocols (see below) |
| **Description** | Handles all 802.1X and MAB requests from wired switches |

### Policy Set 2: Guest_Access

| Field | Value |
|---|---|
| **Name** | Guest_CWA |
| **Status** | Enabled |
| **Condition** | `Radius:NAS-Port-Type EQUALS Ethernet AND ISE:ExternalGroups EQUALS Guest` |
| **Allowed Protocols** | MAB_Only |
| **Description** | Captive Web Authentication for guest self-registration |

---

## Allowed Protocols Configuration

### Profile: Wired_Allowed_Protocols

Navigate in ISE: **Policy > Policy Elements > Results > Authentication > Allowed Protocols**

| Protocol | Enabled | Notes |
|---|---|---|
| **EAP-TLS** | ✅ Yes | Certificate-based mutual auth (most secure) |
| **PEAP** (inner MSCHAPv2) | ✅ Yes | Password-based with AD credentials |
| **PEAP** (inner EAP-TLS) | ✅ Yes | Certificate inside PEAP tunnel |
| **EAP-FAST** | Optional | Cisco proprietary, used for posture |
| **LEAP** | ❌ No | Deprecated, vulnerable to brute force |
| **EAP-MD5** | ❌ No | No mutual auth, insecure |
| **MAB** (PAP) | ✅ Yes | Required for MAC Auth Bypass |
| **Process Host Lookup** | ✅ Yes | Required for MAB |

---

## Authentication Policy Rules

### Inside Policy Set: Wired_Access

| Rule # | Rule Name | Condition | Identity Source | If Auth Fails | If User Not Found |
|---|---|---|---|---|---|
| 1 | Dot1X_EAP-TLS | `Network Access:EapAuthentication EQUALS EAP-TLS` | AD + Internal CA | REJECT | DROP |
| 2 | Dot1X_PEAP | `Network Access:EapAuthentication EQUALS PEAP` | Active Directory | REJECT | DROP |
| 3 | Wired_MAB | `Network Access:UseCase EQUALS Host Lookup` | Internal Endpoints DB | CONTINUE | CONTINUE |
| 4 | Default | — | Deny Access | — | — |

---

## Detailed Rule Descriptions

### Rule 1: Dot1X_EAP-TLS

- **Purpose**: Authenticate corporate laptops and workstations using machine certificates issued by the internal CA.
- **Condition**: EAP type is EAP-TLS (detected automatically from supplicant).
- **Identity Source Sequence**:
  1. Check **AD_Join_Point** (verify certificate CN against AD user/machine account)
  2. Check **Internal CA Certificate Authority** for valid certificate chain
- **On Auth Fail**: Send RADIUS `Access-Reject` → switch places port in VLAN 99 (Quarantine)
- **On User Not Found**: Drop — no fallback for unknown certificates

**EAP-TLS Flow:**
```
Client              Switch              ISE                  AD / CA
  |--EAP-Start-------->|                  |                    |
  |<--EAP-Request/ID---|                  |                    |
  |--EAP-Response/ID-->|                  |                    |
  |                    |--Access-Request->|                    |
  |                    |                  |--Validate Cert---->|
  |                    |                  |<--Cert Valid-------|
  |<--EAP-TLS Handshake (mutual cert exchange)--------------->|
  |                    |<--Access-Accept--|                    |
  |<--Port Authorized--|                  |                    |
```

### Rule 2: Dot1X_PEAP (MSCHAPv2)

- **Purpose**: Authenticate users who provide AD username/password (e.g., domain workstations, personal devices with corporate WiFi profile).
- **Condition**: EAP type is PEAP.
- **Identity Source**: Active Directory (`AD_Join_Point`)
- **On Auth Fail**: Send `Access-Reject` → switch sends EAP-Failure → port goes to VLAN 99
- **On User Not Found**: Reject → VLAN 99

**PEAP Flow:**
```
Client              Switch              ISE                  AD
  |--EAP-Start-------->|                  |                    |
  |<--EAP-Request/ID---|                  |                    |
  |--EAP-Response/ID-->|--RADIUS Request->|                    |
  |<---TLS Tunnel Established (ISE cert)------------------>   |
  |--MSCHAPv2 (username/password in tunnel)                   |
  |                    |                  |--MS-CHAPv2 auth--->|
  |                    |                  |<--Auth OK----------|
  |                    |<--Access-Accept--|                    |
  |<--Port Authorized--|                  |                    |
```

### Rule 3: Wired_MAB

- **Purpose**: Authenticate devices that cannot perform 802.1X (printers, IP phones, IoT sensors, cameras).
- **How it works**: The switch sends the device's MAC address as both the username and password in a RADIUS Access-Request.
- **Condition**: `Network Access:UseCase EQUALS Host Lookup`
- **Identity Source**: Internal Endpoints database (ISE Endpoint repository)
- **Profiling**: ISE profiles the device using DHCP fingerprint, CDP/LLDP, HTTP User-Agent, Nmap, etc.
- **On Not Found**: `CONTINUE` → goes to authorization; unknown MAB devices can be redirected to guest portal or placed in quarantine per authorization rule.

---

## ISE GUI Navigation — Creating Authentication Policy Rules

### Step 1: Navigate to Policy Sets
1. Log in to ISE admin: `https://192.168.1.100/admin`
2. Go to **Policy > Policy Sets**
3. Click **+** to create a new Policy Set or click the **>** arrow on an existing one

### Step 2: Configure Policy Set Conditions
1. Under **Policy Set Name**, enter `Wired_Access`
2. Click the **+** under **Conditions**
3. Select **Radius > NAS-Port-Type > Equals > Ethernet**
4. Under **Allowed Protocols**, select `Wired_Allowed_Protocols`
5. Click **Save**

### Step 3: Edit Authentication Policy
1. Inside the Policy Set, expand the **Authentication Policy** section
2. Click **+** to add a new rule
3. For Rule 1 (EAP-TLS):
   - **Name**: `Dot1X_EAP-TLS`
   - **Conditions**: Click **+** → `Network Access > EapAuthentication > Equals > EAP-TLS`
   - **Use**: `AD_Join_Point`
   - **If Auth Fail**: `REJECT`
   - **If User Not Found**: `DROP`
4. Click **Save**
5. Repeat for PEAP and MAB rules

### Step 4: Reorder Rules
- Drag rules to ensure EAP-TLS is evaluated before PEAP, and PEAP before MAB.
- More specific rules should always be higher in the list.

### Step 5: Configure Allowed Protocols Profile
1. Navigate to **Policy > Policy Elements > Results > Authentication > Allowed Protocols**
2. Click **Add**
3. Name it `Wired_Allowed_Protocols`
4. Enable: EAP-TLS, PEAP (MSCHAPv2), Process Host Lookup (for MAB)
5. Disable: LEAP, EAP-MD5
6. Click **Submit**

---

## Identity Source Sequence

Navigate to: **Administration > Identity Management > Identity Source Sequences**

### Sequence: AD_and_Endpoints

| Priority | Source | Description |
|---|---|---|
| 1 | Active Directory (`lab.local`) | For user/machine authentication |
| 2 | Internal Endpoints | For MAB lookup |
| 3 | Internal Users | For local test accounts |

**Treatment for auth failure**: If a selected identity source fails to respond (not found ≠ auth fail), proceed to the next source in the sequence.

---

## Certificate Authority Configuration

For EAP-TLS to work, ISE must trust the CA that issued client certificates:

1. Navigate to **Administration > System > Certificates > Trusted Certificates**
2. Import the Root CA certificate (PEM format)
3. Enable **Trust for client authentication**
4. Optionally enable **Trust for ISE Auth**

Machine certificates on Windows endpoints should be enrolled automatically via **Group Policy (GPO)**:
- **Certificate Template**: Computer (or custom template)
- **Auto-enrollment**: Enabled in GPO → Computer Configuration → Windows Settings → Security Settings → Public Key Policies

---

## Monitoring Authentication Events

Navigate to: **Operations > RADIUS > Live Logs**

Key columns to watch:
- **Identity**: Username or MAC address
- **Authentication Policy**: Which rule matched
- **Authorization Policy**: Which authz rule applied
- **Result**: Authentication passed / failed
- **Failure Reason**: If failed, root cause code
- **Endpoint Profile**: Profiled device type

Use the **Detail** icon to see the full RADIUS attribute exchange for any log entry.
