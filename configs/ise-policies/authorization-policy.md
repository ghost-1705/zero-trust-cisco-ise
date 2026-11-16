# ISE Authorization Policy Configuration Guide

## Overview

After a successful (or conditionally continued) authentication, ISE evaluates the **Authorization Policy** to determine *what* a user or device is allowed to do. The result of an authorization rule is an **Authorization Profile** that tells the switch:

- Which **VLAN** to assign the port to
- Which **dACL** (Downloadable ACL) to apply to the session
- Which **SGT** (Security Group Tag) to stamp on traffic
- Whether to redirect to a **web portal** (guest, remediation)
- Whether **CoA** (Change of Authorization) should trigger later

---

## Authorization Rules Table

| # | Rule Name | Conditions | VLAN | dACL | SGT | Redirect | Notes |
|---|---|---|---|---|---|---|---|
| 1 | Employee_Compliant | AD Group = Employees AND Posture = Compliant | 10 | PERMIT_ALL_TRAFFIC | SGT-10 (Employee) | None | Full access for healthy domain machines |
| 2 | Employee_NonCompliant | AD Group = Employees AND Posture = NonCompliant | 99 | DENY_ALL | SGT-99 (Quarantine) | Remediation Portal | Redirect to fix AV/patch |
| 3 | Employee_Unknown_Posture | AD Group = Employees AND Posture = Unknown | 10 | PERMIT_REMEDIATION | SGT-10 | None | Redirect to ISE Posture Agent download |
| 4 | Contractor | AD Group = Contractors | 20 | PERMIT_INTERNET_ONLY | SGT-20 (Contractor) | None | Internet and limited servers only |
| 5 | IoT_Profiled | Endpoint Profile = IP-Camera OR Printer OR IoT | 30 | PERMIT_IOT_ISOLATED | SGT-30 (IoT) | None | Restricted to IoT MQTT server |
| 6 | VoIP_Phone | Endpoint Profile = Cisco-IP-Phone | 50 | None (implicit allow) | SGT-50 (VoIP) | None | Voice VLAN, CDP-profiled Cisco phones |
| 7 | Guest_Registered | Guest Flow = True | 40 | PERMIT_INTERNET_ONLY | SGT-40 (Guest) | None | After guest portal self-registration |
| 8 | Guest_Unregistered | MAB AND Unknown AND Guest VLAN | 40 | PERMIT_REDIRECT_ONLY | SGT-40 | Guest Portal | Redirect to self-service guest portal |
| 9 | Unknown_Device | No Match Above | 99 | DENY_ALL | SGT-99 | None | Catch-all; quarantine unknown |
| 10 | Auth_Failed | Auth Failure (via CoA or fail action) | 99 | DENY_ALL | SGT-99 | None | For RADIUS reject fall-through |

---

## VLAN Assignment Details

VLAN assignment is performed by ISE including the RADIUS attributes in the Access-Accept:

| RADIUS Attribute | Value for VLAN 10 Example |
|---|---|
| `Tunnel-Type` (64) | `VLAN` (value = 13) |
| `Tunnel-Medium-Type` (65) | `802` (value = 6) |
| `Tunnel-Private-Group-ID` (81) | `10` (string — VLAN ID or name) |

The switch places the authenticated port into the specified VLAN, overriding the port's default configured access VLAN.

---

## Downloadable ACL (dACL) Details

dACLs are pushed by ISE via the `Cisco-AVPair = ip:inacl#1=...` RADIUS attribute. The switch creates a per-session ACL and applies it to the authenticated port's ingress traffic.

### dACL Assignment in Authorization Profile

Navigate: **Policy > Policy Elements > Results > Authorization > Authorization Profiles**

Each profile has a **Common Tasks** section:
- **DACL Name**: Select from pre-defined dACLs
- **VLAN**: Select the VLAN ID
- **SGT**: Select the Security Group Tag
- **Web Redirection**: For guest/remediation portals

---

## Posture Conditions

Posture is assessed by the **ISE Posture Module** (installed via AnyConnect or Temporal Agent).

### Posture Requirements Defined

Navigate: **Policy > Policy Elements > Conditions > Posture**

| Requirement Name | Check Type | Condition | Remediation |
|---|---|---|---|
| AV_Check_Requirement | Anti-Malware | Windows Defender or Symantec = Running & Updated | Message: "Enable AV" |
| Firewall_Check | Firewall | Windows Firewall = Enabled | Auto-remediation: Enable firewall |
| OS_Patch_Check | Windows Update | Last Update < 30 days | Message: "Run Windows Update" |
| Disk_Encryption | Disk Encryption | BitLocker = Enabled on C: | Message: "Enable BitLocker" |

### Posture Policy Rules

Navigate: **Policy > Posture**

| Rule | OS | Requirements | Grace Period |
|---|---|---|---|
| Windows_Posture | Windows 10/11 | AV_Check + Firewall_Check + OS_Patch_Check | 1 hour |
| Mac_Posture | macOS 12+ | Gatekeeper = On, FileVault = On | 1 hour |
| Any_Device | Any | (minimum check) | 24 hours |

**Posture Status flow:**
```
Device Connects → 802.1X Auth Passes
       ↓
ISE assigns "Unknown Posture" profile → Limited access + redirect to agent
       ↓
AnyConnect Posture Agent runs checks
       ↓
  Pass? → CoA → ISE reassigns "Compliant" profile → Full access (VLAN 10)
  Fail? → CoA → ISE reassigns "NonCompliant" profile → VLAN 99 + Remediation portal
```

---

## Security Group Tag (SGT) Assignments

SGTs are part of Cisco **TrustSec** and provide scalable policy based on group membership rather than IP addresses. The SGT is embedded in the Cisco MetaData (CMD) header of frames.

| SGT Value | SGT Name | Description | VLAN Mapping |
|---|---|---|---|
| 10 | Employee | Full-trust corporate users | VLAN 10 |
| 20 | Contractor | Limited-trust third-party users | VLAN 20 |
| 30 | IoT | Untrusted headless devices | VLAN 30 |
| 40 | Guest | Untrusted external users | VLAN 40 |
| 50 | VoIP | Voice-only devices | VLAN 50 |
| 99 | Quarantine | Non-compliant/unknown endpoints | VLAN 99 |
| 100 | Servers | Internal servers (static assignment) | VLAN 200 |
| 110 | ISE_Admin | ISE policy node | VLAN 200 |

### SGT Policy Matrix (SGACL)

Defines which SGTs can communicate:

| Source \ Destination | Employee (10) | Contractor (20) | IoT (30) | Guest (40) | Servers (100) |
|---|---|---|---|---|---|
| **Employee (10)** | Permit | Deny | Deny | Deny | Permit |
| **Contractor (20)** | Deny | Permit | Deny | Deny | Permit (port 443, 22) |
| **IoT (30)** | Deny | Deny | Permit | Deny | Permit (port 1883) |
| **Guest (40)** | Deny | Deny | Deny | Permit | Deny |
| **Quarantine (99)** | Deny | Deny | Deny | Deny | Deny |

---

## Change of Authorization (CoA) Triggers

CoA allows ISE to push policy changes to an active session **without requiring the user to re-authenticate**. This is defined in RFC 5176.

### CoA Types Supported

| CoA Type | RADIUS Message | Use Case |
|---|---|---|
| **Re-Auth** | CoA-Request with `Cisco-AVPair = subscriber:command=reauthenticate` | Force re-authentication |
| **Port Bounce** | CoA-Request with `Cisco-AVPair = subscriber:command=bounce-port` | Disconnect and re-auth (e.g. guest login) |
| **Port Disable** | CoA-Request with `Cisco-AVPair = subscriber:command=disable-port` | Shut down port (threat response) |
| **VLAN Change** | New Access-Accept with updated VLAN attributes | Re-assign VLAN without disconnect |
| **dACL Change** | New Access-Accept with updated ACL | Apply new ACL (posture change) |
| **Session Terminate** | Disconnect-Request | Forcibly disconnect session |

### CoA Trigger Scenarios

| Trigger | Action | Result |
|---|---|---|
| Posture changes from Unknown → Compliant | CoA VLAN change | Move from restricted to VLAN 10 + PERMIT_ALL |
| Posture changes from Compliant → NonCompliant | CoA VLAN change + dACL | Move to VLAN 99 + DENY_ALL |
| Threat detected by Stealthwatch/XDR | CoA Port Disable | Port shut down immediately |
| Guest timer expires (24h) | CoA Session Terminate | Disconnect guest session |
| Admin manually quarantines via ISE UI | CoA Port Bounce → new auth | Device re-auths, gets quarantine profile |
| AV definition update causes posture pass | CoA VLAN change | Restore normal access |

### CoA Configuration on Switch

The switch must accept CoA messages from ISE. This is configured with:
```
aaa server radius dynamic-author
 client 192.168.1.100 server-key ChangeMe_SharedSecret!
 auth-type any
```
Port `3799/UDP` must be open from ISE to the switch (ISE sends CoA to the NAS).

---

## Authorization Profile Example — Employee_Compliant

Navigate: **Policy > Policy Elements > Results > Authorization > Authorization Profiles**

```
Name: EMPLOYEE_FULL_ACCESS
Description: Full access for compliant employee endpoints

Common Tasks:
  ✅ DACL Name: PERMIT_ALL_TRAFFIC
  ✅ VLAN: 10
  ✅ Security Group: Employee (SGT 10)
  ☐ Web Redirection: Disabled
  ☐ Auto SmartPort: Disabled

Advanced Attributes:
  Cisco:cisco-av-pair = url-redirect-acl=ACL-REDIRECT    (not used here)
  Cisco:cisco-av-pair = ACS:CiscoSecure-Defined-ACL=#ACSACL#-IP-PERMIT_ALL_TRAFFIC
```

---

## ISE GUI: Creating Authorization Rules

### Step 1: Navigate
**Policy > Policy Sets > Wired_Access > Authorization Policy**

### Step 2: Add Rule — Employee Compliant
1. Click **+** (Insert new rule)
2. **Name**: `Employee_Compliant`
3. **Conditions**:
   - Click **+** in conditions column
   - Add: `AD:ExternalGroups EQUALS lab.local/Users/Employees`
   - AND: `Session:PostureStatus EQUALS Compliant`
4. **Profiles**: Select `EMPLOYEE_FULL_ACCESS`
5. Click **Save**

### Step 3: Add Rule — Contractor
1. **Name**: `Contractor_Access`
2. **Conditions**: `AD:ExternalGroups EQUALS lab.local/Users/Contractors`
3. **Profiles**: `CONTRACTOR_LIMITED_ACCESS`

### Step 4: Default Rule
- Always keep a **Default** rule at the bottom
- Assign to `DenyAccess` or quarantine profile
- This catches anything that doesn't match above rules

### Step 5: Verify Rule Order
- Rules are evaluated top-to-bottom, **first match wins**
- More specific rules (posture + group) must be above general rules (group only)
