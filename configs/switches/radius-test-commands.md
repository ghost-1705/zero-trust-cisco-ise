# Cisco IOS — RADIUS & 802.1X Verification and Troubleshooting Commands

## Overview

This document is a reference for verifying, troubleshooting, and debugging Cisco ISE RADIUS integration and 802.1X authentication on Cisco Catalyst switches. Use these commands during lab setup, testing, and production troubleshooting.

---

## 1. Test AAA RADIUS Connectivity

### `test aaa group` — Verify RADIUS reachability and credentials

The `test aaa group radius` command sends a test authentication request directly from the switch to ISE, simulating a user login.

```
SW-ACCESS-01# test aaa group RADIUS-SERVERS jsmith Employee@123 new-code
```

**Parameters:**
- `RADIUS-SERVERS` — the AAA server group name defined in config
- `jsmith` — test username (must exist in AD / ISE Internal Users)
- `Employee@123` — test password
- `new-code` — required keyword; ensures the switch uses the RADIUS group

**Successful Output:**
```
Attempting authentication test to server-group RADIUS-SERVERS using radius
User was successfully authenticated.
```

**Failure Output:**
```
Attempting authentication test to server-group RADIUS-SERVERS using radius
User authentication request was rejected by the server.
```

**If ISE is unreachable:**
```
ERROR: No Server(s) Responding
```

**Common Issues:**
| Output | Cause | Fix |
|---|---|---|
| `No Server(s) Responding` | RADIUS unreachable | Check routing, firewall (UDP 1812), shared secret |
| `Authentication rejected` | Wrong password or no AD user | Verify credentials in AD; check ISE Live Logs |
| `Server timed out` | ISE overloaded or slow | Increase timeout: `radius server ISE-PRIMARY` → `timeout 10` |

---

## 2. show authentication sessions

### `show authentication sessions` — Overview of all active 802.1X sessions

```
SW-ACCESS-01# show authentication sessions
```

**Example Output:**
```
Interface    MAC Address     Method   Domain   Status         Fg  Session ID
Gi0/1        aa11.bb22.cc33  dot1x    DATA     Auth               0A640B0B00000001
Gi0/2        dd44.ee55.ff66  mab      DATA     Auth               0A640B0B00000002
Gi0/3        1122.3344.5566  dot1x    VOICE    Auth               0A640B0B00000003
Gi0/4        —               N/A      —        No Auth            —
```

**Column Explanations:**
| Column | Description |
|---|---|
| `Interface` | Switch port |
| `MAC Address` | Endpoint MAC (Cisco dotted format: xxxx.xxxx.xxxx) |
| `Method` | `dot1x` (EAP) or `mab` (MAC Auth Bypass) |
| `Domain` | `DATA` (data endpoint) or `VOICE` (VoIP phone) |
| `Status` | `Auth` = authorized, `Unauth` = pending/failed, `NoResp` = no 802.1X response |
| `Fg` | Flags: `A`=Authz Success, `F`=Fail |
| `Session ID` | Unique ID for this RADIUS session (useful for CoA) |

---

### `show authentication sessions interface <intf>` — Session detail for one port

```
SW-ACCESS-01# show authentication sessions interface GigabitEthernet0/1 detail
```

**Example Output:**
```
            Interface:  GigabitEthernet0/1
          MAC Address:  aa11.bb22.cc33
         IPv6 Address:  Unknown
         IPv4 Address:  10.10.10.10
           User-Name:  jsmith@lab.local
              Status:  Authorized
              Domain:  DATA
        Oper host mode:  multi-auth
      Oper control dir:  both
       Session timeout:  N/A
    Common Session ID:  0A640B0B00000001
      Acct Session ID:  0x00000001
               Handle:  0xCA000001
       Current Policy:  POLICY_Gi0/1

Local Policies:
       Service Template: DEFAULT_LINKSEC_POLICY_SHOULD_SECURE (priority 150)

Server Policies:
           Vlan Group:  Vlan: 10
           ACS ACL: xACSACLx-IP-PERMIT_ALL_TRAFFIC-5f1e6c33
     Security Group:  Employee

Method status list:
       Method           State
       dot1x            Authc Success
```

**Key Fields:**
| Field | Meaning |
|---|---|
| `User-Name` | Authenticated identity (AD username or MAC for MAB) |
| `Status: Authorized` | Port is open and policy applied |
| `Vlan Group: Vlan: 10` | ISE assigned VLAN 10 |
| `ACS ACL` | The dACL name downloaded from ISE |
| `Security Group` | SGT assigned by ISE (TrustSec) |
| `Method: dot1x / Authc Success` | EAP authentication passed |

---

## 3. show dot1x all

### `show dot1x all` — 802.1X global and per-interface status

```
SW-ACCESS-01# show dot1x all
```

**Example Output:**
```
 Sysauthcontrol                 Enabled
 Dot1x Protocol Version          3

Dot1x Info for GigabitEthernet0/1
-----------------------------------
PAE                       = AUTHENTICATOR
QuietPeriod               = 60
ServerTimeout             = 30
SuppTimeout               = 30
ReAuthMax                 = 2
MaxReq                    = 2
TxPeriod                  = 30

Dot1x Info for GigabitEthernet0/2
-----------------------------------
PAE                       = AUTHENTICATOR
...
```

**Key Fields:**
| Field | Description |
|---|---|
| `Sysauthcontrol: Enabled` | Global 802.1X is enabled (`dot1x system-auth-control`) |
| `PAE = AUTHENTICATOR` | This port acts as the 802.1X authenticator |
| `QuietPeriod` | Seconds to wait before retrying after failure (default: 60) |
| `TxPeriod` | Seconds between EAP-Request/Identity retransmissions (default: 30) |
| `SuppTimeout` | Seconds to wait for supplicant response (default: 30) |
| `ReAuthMax` | Maximum reauthentication attempts |

---

## 4. show radius statistics

```
SW-ACCESS-01# show radius statistics
```

**Example Output:**
```
Auth        Acct
  Requests    :  142       134
  Retransmissions:  0         0
  Timeouts    :  0         0
  Rejects     :  3         0
  Accepts     :  139       0
  Pending     :  0         0
  Response time:  210ms     185ms
```

**What to look for:**
- **High Timeouts**: ISE unreachable or slow → check network path, ISE load
- **High Rejects**: Many auth failures → check credentials, certs, ISE policy
- **High Retransmissions**: RADIUS packets lost → network instability

---

## 5. debug Commands

> ⚠️ **Warning**: Debug commands generate significant log output and can impact switch performance on production devices. Always disable debugging after use.

### `debug dot1x` — Trace 802.1X EAP exchanges

```
SW-ACCESS-01# debug dot1x all
SW-ACCESS-01# debug dot1x events
SW-ACCESS-01# debug dot1x packets
SW-ACCESS-01# debug dot1x errors
```

**Example debug output (EAP-TLS):**
```
*Nov 16 10:00:01.123: DOT1X-5-SUCCESS: Authentication successful for client (aa11.bb22.cc33) on Interface Gi0/1
*Nov 16 10:00:01.456: DOT1X-EV: Received an EAP Success message for the client 0xAA11BB22CC33
```

### `debug radius` — Trace RADIUS messages between switch and ISE

```
SW-ACCESS-01# debug radius
SW-ACCESS-01# debug radius authentication
SW-ACCESS-01# debug radius accounting
```

**Example debug output:**
```
*Nov 16 10:00:00.100: RADIUS: Send Access-Request to 192.168.1.100:1812 id=23
*Nov 16 10:00:00.100: RADIUS: NAS-IP-Address [4] 6 192.168.100.11
*Nov 16 10:00:00.100: RADIUS: NAS-Port-Type [61] 6 Ethernet [15]
*Nov 16 10:00:00.100: RADIUS: Called-Station-Id [30] 19 "GigabitEthernet0/1"
*Nov 16 10:00:00.210: RADIUS: Received from id 23 192.168.1.100:1812, Access-Accept, len 189
*Nov 16 10:00:00.210: RADIUS: Tunnel-Type [64] 6 VLAN [13]
*Nov 16 10:00:00.210: RADIUS: Tunnel-Medium-Type [65] 6 IEEE-802 [6]
*Nov 16 10:00:00.210: RADIUS: Tunnel-Private-Group-Id [81] 4 "10"
```

### Disable all debugs:
```
SW-ACCESS-01# undebug all
! or:
SW-ACCESS-01# no debug all
```

---

## 6. Clear Authentication Session Commands

### Force re-authentication for a specific interface:
```
SW-ACCESS-01# clear authentication sessions interface GigabitEthernet0/1
```

### Force re-authentication for a specific MAC:
```
SW-ACCESS-01# clear authentication sessions mac aa11.bb22.cc33
```

### Clear all authentication sessions:
```
SW-ACCESS-01# clear authentication sessions
```

> **Effect**: Clears the session and forces 802.1X/MAB to restart. The endpoint will re-authenticate. Use this after changing ISE policies to test the new policy without unplugging the cable.

### Restore a port from err-disabled (e.g., after BPDU Guard):
```
SW-ACCESS-01(config)# interface GigabitEthernet0/1
SW-ACCESS-01(config-if)# shutdown
SW-ACCESS-01(config-if)# no shutdown
```

### Auto-recover from err-disabled:
```
SW-ACCESS-01(config)# errdisable recovery cause bpduguard
SW-ACCESS-01(config)# errdisable recovery cause dot1x
SW-ACCESS-01(config)# errdisable recovery interval 300
```

---

## 7. Additional Useful Commands

### Show RADIUS server group configuration:
```
SW-ACCESS-01# show aaa group server radius RADIUS-SERVERS
```

### Show AAA configuration summary:
```
SW-ACCESS-01# show aaa
```

### Show downloaded IP ACLs (including dACLs from ISE):
```
SW-ACCESS-01# show ip access-lists
```

### Show CoA dynamic authorization configuration:
```
SW-ACCESS-01# show aaa server
```

### Verify 802.1X is enabled on a specific interface:
```
SW-ACCESS-01# show running-config interface GigabitEthernet0/1
! Look for: dot1x pae authenticator, authentication port-control auto
```

### Show DHCP snooping binding table (useful to verify VLAN assignment):
```
SW-ACCESS-01# show ip dhcp snooping binding
```

### Show ARP inspection statistics:
```
SW-ACCESS-01# show ip arp inspection vlan 10
```

---

## 8. Common Issues and Fixes

| Symptom | Likely Cause | Fix |
|---|---|---|
| Port stuck in `Unauthorized` | 802.1X supplicant not running on PC | Start Windows 802.1X service; verify "dot1x pae authenticator" on port |
| `show auth sessions` shows no entries | `dot1x system-auth-control` missing | Add `dot1x system-auth-control` to global config |
| dACL not applied (blank in `show ip access-lists`) | ISE not returning Cisco-AVPair or wrong dACL name | Check ISE authz profile; verify dACL name matches; check ISE Live Logs |
| Wrong VLAN assigned | ISE authz rule ordering issue | Check ISE policy rule order; first match wins |
| MAB not triggering after dot1x timeout | `authentication order` misconfigured | Ensure `authentication order dot1x mab` and `authentication priority dot1x mab` on port |
| CoA not received by switch | Port 3799 blocked or `aaa server radius dynamic-author` missing | Add `aaa server radius dynamic-author` block; verify no firewall blocking 3799/UDP from ISE |
| `test aaa` succeeds but port won't auth | NAS IP mismatch in ISE | Ensure ISE Network Device entry uses the switch's `ip radius source-interface` IP |
| EAP-TLS fails | Client cert not trusted by ISE | Import the Root CA into ISE Trusted Certificates; check ISE system cert is trusted by client |
| Ports go to auth-fail VLAN immediately | `aaa authentication dot1x default` using wrong group | Verify `aaa authentication dot1x default group RADIUS-SERVERS` |
