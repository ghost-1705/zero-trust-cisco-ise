# Test Plan — Zero Trust 802.1X Network with Cisco ISE

## Document Information

| Field | Value |
|---|---|
| **Project** | Zero Trust Network with Cisco ISE & 802.1X |
| **Version** | 1.0 |
| **Date** | 2024 |
| **Tester** | Network Lab Team |
| **Environment** | GNS3/EVE-NG Lab or Physical Lab |
| **ISE Version** | 3.2 |
| **Switch Platform** | Cisco Catalyst 2960-X / 3850 (IOS 15.2.4E+) |

---

## Test Environment Setup

Before executing tests, verify the following baseline conditions:
- [ ] ISE is reachable from all switches (ping 192.168.1.100 from switch)
- [ ] RADIUS test passes from switch: `test aaa group RADIUS-SERVERS testuser testpass new-code`
- [ ] All switches are time-synchronized with NTP (< 5 min skew)
- [ ] AD users exist: `jsmith` (Employees group), `contractor01` (Contractors group)
- [ ] Machine certificates issued to test PCs via GPO
- [ ] Wireshark or SPAN port configured for packet captures (TC-10)

---

## Test Cases

### TC-01: Valid Employee — 802.1X with EAP-TLS (Certificate-Based)

| Field | Detail |
|---|---|
| **Test ID** | TC-01 |
| **Category** | Authentication — 802.1X |
| **Priority** | P1 — Critical |
| **Prerequisite** | Machine certificate installed on PC; PC joined to `lab.local` domain |

**Steps:**
1. Plug a domain-joined Windows PC into SW-ACCESS-01 port Gi0/1
2. PC attempts 802.1X using Windows native supplicant (EAP-TLS, machine cert)
3. Wait up to 30 seconds for authentication to complete
4. On the switch, run: `show authentication sessions interface Gi0/1`
5. On ISE, check: **Operations > RADIUS > Live Logs** for the event

**Expected Result:**
- Switch shows: `Status: Authz Success`, `Method: dot1x`, `Vlan Policy: 10`
- ISE Live Logs show: `Authentication Succeeded`, `Authorization Profile: EMPLOYEE_FULL_ACCESS`
- PC receives IP from VLAN 10 subnet (10.10.10.x)
- PC can ping 10.10.10.1 and access internal servers (VLAN 10 ACL allows)

**Verification Commands:**
```
SW-ACCESS-01# show authentication sessions interface Gi0/1
SW-ACCESS-01# show authentication sessions interface Gi0/1 detail
SW-ACCESS-01# show ip access-lists    ! Should show dACL PERMIT_ALL_TRAFFIC applied
```

**Pass/Fail:** ___________  
**Notes:** _______________________________________________

---

### TC-02: Invalid Password — PEAP-MSCHAPv2 Authentication Failure

| Field | Detail |
|---|---|
| **Test ID** | TC-02 |
| **Category** | Authentication Failure |
| **Priority** | P1 — Critical |
| **Prerequisite** | Windows supplicant configured with PEAP-MSCHAPv2 |

**Steps:**
1. Configure Windows supplicant with username `jsmith` and **wrong password** `WrongPass!`
2. Plug into SW-ACCESS-01 port Gi0/2
3. Wait for authentication attempt and failure
4. Check ISE Live Logs
5. Check switch authentication state

**Expected Result:**
- ISE returns `Access-Reject` to the switch
- Switch shows `Status: Authz Failed` or `NoResp`, then places port in VLAN 99 (Quarantine)
- PC receives IP from 10.10.99.x (Quarantine VLAN)
- PC cannot reach internal resources; can only reach ISE remediation portal
- ISE Live Logs show: `Authentication Failed`, `Failure Reason: 24408 — User authentication against Active Directory failed`

**Verification Commands:**
```
SW-ACCESS-01# show authentication sessions interface Gi0/2
SW-ACCESS-01# show authentication sessions interface Gi0/2 detail
! Expect: Vlan Policy = 99, Status = Authz Failed
```

**Pass/Fail:** ___________  
**Notes:** _______________________________________________

---

### TC-03: Non-Compliant Device — Failed Posture Assessment

| Field | Detail |
|---|---|
| **Test ID** | TC-03 |
| **Category** | Posture |
| **Priority** | P1 — Critical |
| **Prerequisite** | AnyConnect with Posture module installed; Windows Defender disabled intentionally |

**Steps:**
1. Disable Windows Defender on the test PC (`jsmith` account)
2. Connect the PC to SW-ACCESS-01 Gi0/1; authenticate with valid credentials (EAP-TLS)
3. AnyConnect Posture module runs the AV check
4. ISE posture policy fails (AV not running)
5. ISE sends CoA to switch to change session to NonCompliant profile
6. Verify VLAN and ACL change

**Expected Result:**
- Initial auth succeeds (posture status: Unknown) → PC gets PERMIT_REMEDIATION dACL
- Posture agent runs → AV check fails
- ISE sends CoA `reauthenticate` → switch re-authenticates the session
- New authorization: `Employee_NonCompliant` → VLAN 99 + DENY_ALL dACL
- PC receives notification: "Your device does not meet security requirements"
- ISE Live Logs show posture status changed to `NonCompliant`

**Verification Commands:**
```
SW-ACCESS-01# show authentication sessions interface Gi0/1 detail
! Expect: Vlan Policy=99, ACS ACL=DENY_ALL after CoA

ISE: Operations > RADIUS > Live Logs
! Look for two events: initial auth + CoA reauthentication
```

**Pass/Fail:** ___________  
**Notes:** _______________________________________________

---

### TC-04: Unknown Device — MAB Fallback

| Field | Detail |
|---|---|
| **Test ID** | TC-04 |
| **Category** | MAB Authentication |
| **Priority** | P2 — High |
| **Prerequisite** | An IP camera or printer connected; MAC registered in ISE Endpoints as IoT profile |

**Steps:**
1. Connect an IoT camera (MAC: `AA:BB:CC:11:22:33`) to SW-ACCESS-01 Gi0/4
2. Device sends no EAP-Start (no 802.1X supplicant)
3. Switch waits 30 seconds for 802.1X, then initiates MAB
4. Switch sends RADIUS Access-Request with MAC as username/password
5. ISE matches MAC against Internal Endpoints, finds profile = IP-Camera → matches `IoT_Profiled` authz rule
6. ISE returns Access-Accept with VLAN 30 + PERMIT_IOT_ISOLATED dACL

**Expected Result:**
- Switch shows: `Method: mab`, `Status: Authz Success`, `Vlan Policy: 30`
- PC/server cannot reach the camera on VLAN 10 (inter-VLAN blocked by SGT policy)
- Camera can reach IoT server at 192.168.200.20 on port 1883 (MQTT)
- Camera cannot reach internet or other internal segments

**Verification Commands:**
```
SW-ACCESS-01# show authentication sessions interface Gi0/4
SW-ACCESS-01# show mac address-table interface Gi0/4
ISE: Operations > RADIUS > Live Logs
! Look for: Method=MAB, Identity=AA:BB:CC:11:22:33
```

**Pass/Fail:** ___________  
**Notes:** _______________________________________________

---

### TC-05: Guest Portal Login — Self-Registration Flow

| Field | Detail |
|---|---|
| **Test ID** | TC-05 |
| **Category** | Guest Access |
| **Priority** | P2 — High |
| **Prerequisite** | Guest portal configured in ISE; SW-ACCESS-02 Gi0/3 is a guest port |

**Steps:**
1. Connect a laptop (no corporate account) to SW-ACCESS-02 Gi0/3
2. Device has no 802.1X supplicant configured; MAB is used
3. MAC is unknown → ISE authz rule `Guest_Unregistered` matches → VLAN 40 + redirect ACL
4. User opens browser → redirected to ISE Guest Portal (https://ise.lab.local:8443/guestportal)
5. User self-registers with name, email, mobile number
6. User submits → sponsor receives approval email (or auto-approval if configured)
7. ISE sends CoA port-bounce to the switch
8. Device re-authenticates → `Guest_Registered` rule matches → VLAN 40 + PERMIT_INTERNET_ONLY dACL (without redirect)

**Expected Result:**
- Before registration: browser shows ISE guest portal
- After registration: internet access works (can reach google.com)
- Internal resources are blocked (cannot ping 10.10.10.1)
- ISE Live Logs show: initial MAB + redirect, then CoA, then second MAB with Guest_Registered result

**Pass/Fail:** ___________  
**Notes:** _______________________________________________

---

### TC-06: CoA Test — Posture Changes Mid-Session

| Field | Detail |
|---|---|
| **Test ID** | TC-06 |
| **Category** | CoA (Change of Authorization) |
| **Priority** | P1 — Critical |
| **Prerequisite** | PC connected and in Compliant state (VLAN 10) |

**Steps:**
1. Connect a compliant PC to SW-ACCESS-01 Gi0/1; verify VLAN 10 assignment
2. Record the session's `Audit-Session-ID` from `show authentication sessions detail`
3. On the test PC: **stop Windows Defender service** mid-session
4. Wait for posture re-assessment interval (or trigger manually from AnyConnect)
5. Observe ISE sending CoA to switch

**Expected Result:**
- Posture transitions: Compliant → NonCompliant
- ISE initiates CoA `Reauthenticate`
- Switch re-authenticates without disconnecting (seamless for user)
- New authz profile: `Employee_NonCompliant` → VLAN 99 + DENY_ALL
- User connectivity changes: internal access is lost

**Verification Commands:**
```
SW-ACCESS-01# debug radius
SW-ACCESS-01# debug dot1x
! Watch for CoA messages arriving from ISE on port 3799

ISE: Operations > RADIUS > Live Logs
! Expect two auth events with same user, second triggered by CoA
```

**Pass/Fail:** ___________  
**Notes:** _______________________________________________

---

### TC-07: Port Security / BPDU Guard Test

| Field | Detail |
|---|---|
| **Test ID** | TC-07 |
| **Category** | Layer 2 Security |
| **Priority** | P2 — High |
| **Prerequisite** | Access ports have `spanning-tree bpduguard enable` |

**Steps:**
1. Connect an unmanaged switch (or hub) to SW-ACCESS-01 Gi0/1 (an access port with PortFast + BPDUGuard)
2. The unmanaged switch will send BPDU frames
3. Observe SW-ACCESS-01 behavior

**Expected Result:**
- Gi0/1 enters `err-disabled` state immediately
- Log message: `%SPANTREE-2-BLOCK_BPDUGUARD: Received BPDU on port GigabitEthernet0/1 with BPDU Guard enabled`
- Port stays down until manually re-enabled
- Automatic recovery (if configured): `errdisable recovery cause bpduguard` after timer expires

**Recovery Command:**
```
SW-ACCESS-01# errdisable recovery cause bpduguard
SW-ACCESS-01# errdisable recovery interval 60
! Or manually:
SW-ACCESS-01# interface Gi0/1
SW-ACCESS-01(config-if)# shutdown
SW-ACCESS-01(config-if)# no shutdown
```

**Pass/Fail:** ___________  
**Notes:** _______________________________________________

---

### TC-08: VLAN Assignment Verification

| Field | Detail |
|---|---|
| **Test ID** | TC-08 |
| **Category** | Authorization |
| **Priority** | P1 — Critical |
| **Prerequisite** | Multiple users from different groups ready to test |

**Steps:**
1. Connect `jsmith` (Employee) → verify VLAN 10 assignment
2. Connect `contractor01` (Contractor) → verify VLAN 20 assignment
3. Connect IoT camera (MAB profiled) → verify VLAN 30 assignment
4. Connect guest (unregistered MAB) → verify VLAN 40 assignment
5. Connect non-compliant device → verify VLAN 99 assignment

**Expected Results Table:**

| User / Device | Expected VLAN | Expected dACL | Expected VLAN Name |
|---|---|---|---|
| jsmith (Employee, Compliant) | 10 | PERMIT_ALL_TRAFFIC | EMPLOYEES |
| contractor01 (Contractor) | 20 | PERMIT_INTERNET_ONLY | CONTRACTORS |
| IP Camera (IoT, MAB) | 30 | PERMIT_IOT_ISOLATED | IOT_DEVICES |
| Guest laptop (unregistered) | 40 (redirect) | redirect ACL | GUEST |
| NonCompliant employee | 99 | DENY_ALL | QUARANTINE |

**Verification Commands:**
```
SW-ACCESS-01# show authentication sessions
! Check Vlan column for each connected port
SW-CORE-01# show vlan brief
! Verify VLAN membership
```

**Pass/Fail:** ___________  
**Notes:** _______________________________________________

---

### TC-09: dACL Enforcement Test

| Field | Detail |
|---|---|
| **Test ID** | TC-09 |
| **Category** | Authorization / ACL |
| **Priority** | P1 — Critical |
| **Prerequisite** | Guest device on VLAN 40 with PERMIT_INTERNET_ONLY dACL applied |

**Steps:**
1. Connect guest device to SW-ACCESS-02 Gi0/3; complete portal registration
2. From guest device, attempt:
   a. `ping 10.10.10.1` (Employee gateway — DENY expected)
   b. `ping 192.168.200.10` (AD Server — DENY expected)
   c. `curl http://google.com` (Internet — PERMIT expected)
   d. `curl https://google.com` (HTTPS — PERMIT expected)
   e. `nslookup google.com` (DNS — PERMIT expected)
3. On the switch, verify dACL is applied: `show ip access-lists`

**Expected Results:**
- Pings to internal resources: **fail** (timeout)
- HTTP/HTTPS to internet: **succeed** (200 OK)
- DNS: **succeed**
- Switch ACL hit counters show denies for RFC 1918 destinations

**Verification Commands:**
```
SW-ACCESS-02# show ip access-lists
! Look for the dynamically applied dACL with hit counts

SW-ACCESS-02# show authentication sessions interface Gi0/3 detail
! Confirm: ACS ACL = PERMIT_INTERNET_ONLY
```

**Pass/Fail:** ___________  
**Notes:** _______________________________________________

---

### TC-10: Wireshark Capture — EAP Packet Analysis

| Field | Detail |
|---|---|
| **Test ID** | TC-10 |
| **Category** | Protocol Verification |
| **Priority** | P3 — Medium |
| **Prerequisite** | SPAN port configured on SW-ACCESS-01; Wireshark running on capture PC |

**Steps:**

**Configure SPAN on switch:**
```
SW-ACCESS-01(config)# monitor session 1 source interface Gi0/1 both
SW-ACCESS-01(config)# monitor session 1 destination interface Gi0/23
! Connect Wireshark PC to Gi0/23
```

**Wireshark Filter to use:**
```
eap or eapol or radius
```

**Capture procedure:**
1. Start Wireshark on capture interface with filter `eap or eapol`
2. Plug 802.1X client into Gi0/1
3. Observe the full EAP exchange
4. Stop capture after authentication completes

**What to observe:**
| Packet | Description |
|---|---|
| EAPOL-Start | Client initiates 802.1X (Type 1) |
| EAP-Request/Identity | Switch asks "who are you?" |
| EAP-Response/Identity | Client provides username or machine identity |
| EAP-Request/TLS (if EAP-TLS) | Server sends TLS Server Hello + Certificate |
| EAP-Response/TLS | Client verifies cert, sends its own certificate |
| EAP-Success | Authentication passed |
| EAPOL-Logoff | Client disconnects |
| RADIUS Access-Request | Switch → ISE (see RADIUS attrs like NAS-Port-Type, Called-Station-ID) |
| RADIUS Access-Accept | ISE → Switch (see Tunnel-Type=VLAN, Cisco-AVPair=inacl) |
| RADIUS Accounting-Request | Switch → ISE (session start event) |

**Expected Result:**
- Wireshark shows complete EAP exchange ending with EAP-Success
- RADIUS Access-Accept contains VLAN attributes: Tunnel-Type=VLAN(13), Tunnel-Medium-Type=802(6), Tunnel-Private-Group-ID=10
- No EAP packets visible from other ports (SPAN is port-specific)

**Save capture as:** `tc10_eap_capture_YYYYMMDD.pcap`

**Pass/Fail:** ___________  
**Notes:** _______________________________________________

---

## Summary Tracking Sheet

| Test ID | Test Name | Executed By | Date | Result | Notes |
|---|---|---|---|---|---|
| TC-01 | Valid Employee EAP-TLS | | | Pass / Fail | |
| TC-02 | Invalid Password PEAP Failure | | | Pass / Fail | |
| TC-03 | Non-Compliant Posture Failure | | | Pass / Fail | |
| TC-04 | Unknown Device MAB Fallback | | | Pass / Fail | |
| TC-05 | Guest Portal Self-Registration | | | Pass / Fail | |
| TC-06 | CoA Mid-Session Posture Change | | | Pass / Fail | |
| TC-07 | BPDU Guard Enforcement | | | Pass / Fail | |
| TC-08 | VLAN Assignment Verification | | | Pass / Fail | |
| TC-09 | dACL Enforcement | | | Pass / Fail | |
| TC-10 | Wireshark EAP Capture | | | Pass / Fail | |

---

## Defect Log

| ID | Test Case | Description | Severity | Status | Resolution |
|---|---|---|---|---|---|
| BUG-001 | | | Critical / High / Medium / Low | Open / Closed | |
| BUG-002 | | | | | |

---

## References

- Cisco ISE 3.2 Admin Guide — Authentication Policies
- IEEE 802.1X-2020 Standard
- RFC 3579 — RADIUS Support for EAP
- RFC 5216 — The EAP-TLS Authentication Protocol
- RFC 5176 — Dynamic Authorization Extensions to RADIUS (CoA)
