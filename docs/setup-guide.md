# Lab Setup Guide — Zero Trust Network with Cisco ISE & 802.1X

## Overview

This guide walks through the complete setup of the Zero Trust 802.1X lab from scratch, covering GNS3/EVE-NG topology setup, Cisco ISE VM deployment, Active Directory integration, switch configuration, and supplicant setup on Windows endpoints.

---

## Prerequisites

### Software Required
| Tool | Version | Download |
|---|---|---|
| EVE-NG Community or GNS3 | Latest | https://www.eve-ng.net / https://gns3.com |
| Cisco ISE OVA | 3.2 | Cisco.com (requires CCO account) |
| Windows Server 2022 ISO | Any | Microsoft Evaluation Center |
| Cisco IOS Image | 15.2.4E+ (IOU or VIRL) | Cisco dCloud or DevNet |
| Wireshark | 4.x | https://www.wireshark.org |
| Python | 3.10+ | https://python.org |
| VMware Workstation/ESXi | 17+ | vmware.com (or use EVE-NG built-in KVM) |

### Knowledge Prerequisites
- Basic Cisco IOS CLI (configure terminal, show commands)
- TCP/IP networking (VLANs, trunking, routing)
- RADIUS/AAA concepts
- Basic Active Directory administration

---

## Phase 1: GNS3 / EVE-NG Lab Setup

### Option A: GNS3

#### Step 1: Install GNS3
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y gns3-gui gns3-server

# Or download GNS3 All-in-One for Windows from https://gns3.com/software/download
```

#### Step 2: Import Cisco IOS Images
1. Open GNS3 → **Edit > Preferences > IOS Routers / EtherSwitch Routers**
2. Click **New** → Browse to your Cisco IOS `.bin` file (e.g., `c3750-ipbasek9-mz.122-55.SE12.bin`)
3. Set platform: `c3750` or `c2960`
4. Configure RAM: 256 MB minimum; 512 MB recommended
5. Add 1 Ethernet module (e.g., `NM-16ESW`)
6. Click **Finish**

#### Step 3: Import ISE as a Cloud/External VM
Since ISE runs as a VMware VM, connect it to GNS3 via a Cloud node:
1. In GNS3, add a **Cloud node** to your topology
2. Configure the Cloud to bind to the VMware VMnet adapter where ISE is connected
3. This bridges ISE's VM NIC to the GNS3 topology

#### Step 4: Build the Topology
1. Drag and drop: 1x Core Switch, 2x Access Switches
2. Add Cloud nodes for: ISE, AD Server, test PCs
3. Connect switches:
   - Core Gi0/0 ↔ Access-01 Gi0/23 (trunk)
   - Core Gi0/1 ↔ Access-02 Gi0/23 (trunk)
   - Core Gi0/47 ↔ Cloud (ISE/Server segment)
4. Right-click links → Set link labels for VLAN reference

---

### Option B: EVE-NG Community

#### Step 1: Install EVE-NG
```bash
# Install on Ubuntu 20.04 (bare metal or VM)
wget -O - https://www.eve-ng.net/repo/gpg.key | sudo apt-key add -
echo "deb [arch=amd64] https://www.eve-ng.net/repo focal main" | sudo tee /etc/apt/sources.list.d/eve-ng.list
sudo apt update
sudo apt install -y eve-ng
```

#### Step 2: Upload Cisco IOS Images to EVE-NG
```bash
# SCP your IOS image to EVE-NG
scp c3750-ipbasek9.bin root@eve-ng-ip:/opt/unetlab/addons/iol/bin/

# Fix permissions
/opt/unetlab/wrappers/unl_wrapper -a fixpermissions
```

#### Step 3: Upload ISE OVA to EVE-NG (or run separately in VMware)
ISE is best run in VMware alongside EVE-NG and connected via bridged networking.

#### Step 4: Create New Lab in EVE-NG
1. Open browser: `http://eve-ng-ip` (login: admin/eve)
2. Click **+** → New Lab → Name: `ZeroTrustISE`
3. Add nodes: Core Switch, 2x Access Switches
4. Add Network objects (bridged to host network where ISE runs)
5. Connect all nodes per topology diagram

---

## Phase 2: Windows Server — Active Directory + DNS + CA

### Step 1: Deploy Windows Server VM
- RAM: 4 GB | CPU: 2 vCPU | Disk: 60 GB
- IP: 192.168.200.10/24 | Gateway: 192.168.200.1 | DNS: 127.0.0.1

### Step 2: Promote to Domain Controller
```powershell
# Run PowerShell as Administrator
Install-WindowsFeature -Name AD-Domain-Services -IncludeManagementTools

Import-Module ADDSDeployment
Install-ADDSForest `
    -DomainName "lab.local" `
    -DomainNetBIOSName "LAB" `
    -InstallDNS:$true `
    -DatabasePath "C:\Windows\NTDS" `
    -LogPath "C:\Windows\NTDS" `
    -SysvolPath "C:\Windows\SYSVOL" `
    -SafeModeAdministratorPassword (ConvertTo-SecureString "P@ssw0rd123!" -AsPlainText -Force) `
    -Force:$true
# Server will restart automatically
```

### Step 3: Create AD Users and Groups
```powershell
# Create OUs
New-ADOrganizationalUnit -Name "ZeroTrust" -Path "DC=lab,DC=local"
New-ADOrganizationalUnit -Name "Users" -Path "OU=ZeroTrust,DC=lab,DC=local"
New-ADOrganizationalUnit -Name "Groups" -Path "OU=ZeroTrust,DC=lab,DC=local"
New-ADOrganizationalUnit -Name "Computers" -Path "OU=ZeroTrust,DC=lab,DC=local"

# Create Security Groups
New-ADGroup -Name "Employees" -GroupScope Global -GroupCategory Security -Path "OU=Groups,OU=ZeroTrust,DC=lab,DC=local"
New-ADGroup -Name "Contractors" -GroupScope Global -GroupCategory Security -Path "OU=Groups,OU=ZeroTrust,DC=lab,DC=local"

# Create Users
New-ADUser -Name "John Smith" -SamAccountName "jsmith" -UserPrincipalName "jsmith@lab.local" `
    -AccountPassword (ConvertTo-SecureString "Employee@123" -AsPlainText -Force) `
    -Enabled $true -Path "OU=Users,OU=ZeroTrust,DC=lab,DC=local"
Add-ADGroupMember -Identity "Employees" -Members "jsmith"

New-ADUser -Name "Contractor One" -SamAccountName "contractor01" -UserPrincipalName "contractor01@lab.local" `
    -AccountPassword (ConvertTo-SecureString "Contractor@123" -AsPlainText -Force) `
    -Enabled $true -Path "OU=Users,OU=ZeroTrust,DC=lab,DC=local"
Add-ADGroupMember -Identity "Contractors" -Members "contractor01"
```

### Step 4: Set Up Internal Certificate Authority (for EAP-TLS)
```powershell
# Install Active Directory Certificate Services
Install-WindowsFeature -Name ADCS-Cert-Authority -IncludeManagementTools

# Configure as Enterprise Root CA
Install-AdcsCertificationAuthority `
    -CAType EnterpriseRootCa `
    -CryptoProviderName "RSA#Microsoft Software Key Storage Provider" `
    -KeyLength 2048 `
    -HashAlgorithmName SHA256 `
    -ValidityPeriod Years `
    -ValidityPeriodUnits 10 `
    -CACommonName "Lab-Root-CA" `
    -Force
```

### Step 5: Enable Certificate Auto-Enrollment via GPO
1. Open **Group Policy Management Console (GPMC)**
2. Create GPO: `Certificate_AutoEnroll`
3. Link to `OU=Computers,OU=ZeroTrust,DC=lab,DC=local`
4. Navigate: Computer Configuration → Windows Settings → Security Settings → Public Key Policies
5. Enable **Certificate Services Client — Auto-Enrollment** → Enroll, Renew, Update

---

## Phase 3: Cisco ISE Deployment

### Step 1: Deploy ISE OVA
1. In VMware Workstation/ESXi, **File > Import OVF Template**
2. Select the Cisco ISE `.ova` file
3. Set VM name: `ISE-PRIMARY`
4. CPU: 4 vCPU | RAM: 12 GB (minimum) | Disk: 300 GB
5. Network adapter: Connect to same VMnet as your switches

### Step 2: Initial ISE Boot Setup (Console)
On first boot, ISE runs a setup wizard over the console:
```
Enter hostname: ise
Enter IP address: 192.168.1.100
Enter IP default netmask: 255.255.255.0
Enter IP default gateway: 192.168.1.1
Enter default DNS domain: lab.local
Enter primary nameserver: 192.168.200.10
Enter NTP server: 192.168.200.10
Enter system time zone: America/New_York
Enter username [admin]: admin
Enter password: ISEAdmin@123!
```

Wait 15–20 minutes for ISE services to fully start.

### Step 3: Access ISE Admin GUI
```
URL : https://192.168.1.100/admin
Username: admin
Password: ISEAdmin@123!
```

### Step 4: Accept EULA and Run Setup Wizard
1. Navigate through the setup wizard
2. Set deployment type: **Standalone** (for lab)
3. Upload ISE license (evaluation or prod)

### Step 5: Join ISE to Active Directory

Navigate: **Administration > Identity Management > External Identity Sources > Active Directory**

1. Click **Add**
2. **Join Point Name**: `AD_lab.local`
3. **Active Directory Domain**: `lab.local`
4. Click **Submit**
5. Enter AD admin credentials: `LAB\Administrator` / `P@ssw0rd123!`
6. Click **Join**
7. After joining, go to **Groups** tab → **Add > Select Groups from Directory**
8. Add: `CN=Employees,OU=Groups,OU=ZeroTrust,DC=lab,DC=local`
9. Add: `CN=Contractors,OU=Groups,OU=ZeroTrust,DC=lab,DC=local`
10. Click **Save**

---

## Phase 4: Switch-to-ISE RADIUS Configuration

### Step 1: Add Network Device in ISE

Navigate: **Administration > Network Resources > Network Devices**

1. Click **Add**
2. **Name**: `SW-ACCESS-01`
3. **IP Address**: `192.168.100.11`
4. **Device Profile**: Cisco
5. Under **RADIUS Authentication Settings**:
   - Shared Secret: `ChangeMe_SharedSecret!`
   - CoA Port: 3799 (default)
6. Click **Submit**
7. Repeat for SW-ACCESS-02 (`192.168.100.12`) and SW-CORE-01 (`192.168.100.1`)

### Step 2: Apply Switch Configurations
Copy configs from this repository and apply to each switch:
```
! On switch (via console or SCP):
copy tftp://192.168.100.50/access-switch-01.cfg running-config
! Then:
write memory
```

---

## Phase 5: Supplicant Configuration

### Windows Native Supplicant (EAP-TLS / PEAP)

**For PEAP-MSCHAPv2:**
1. Right-click Network Adapter → **Properties**
2. Go to **Authentication** tab
3. Enable **IEEE 802.1X authentication**
4. Choose EAP type: **Protected EAP (PEAP)**
5. Click **Settings** → Choose **EAP-MSCHAPv2**
6. Credentials: use Windows login (domain credentials)

**Configure via GPO (recommended for domain endpoints):**
1. GPMC → Create GPO `Dot1X_Config`
2. Navigate: Computer Configuration → Windows Settings → Security Settings → Wired Network (IEEE 802.3) Policies
3. Create a new policy:
   - **Network Authentication Method**: PEAP or EAP-TLS
   - **Authentication Mode**: Computer Authentication (for machine certs)

### Cisco AnyConnect Supplicant

1. Install AnyConnect from Cisco.com (requires CCO account)
2. Enable modules: **Network Access Manager (NAM)** and **Posture**
3. Configure NAM profile:
   - Profile editor: **New Connection Profile**
   - Type: Wired
   - EAP Method: EAP-TLS or PEAP
   - Trust ISE certificate: Yes (import ISE cert or trust CA)

---

## Phase 6: Verification and Testing

### Key Verification Commands

```
! On switch — Check 802.1X sessions
SW-ACCESS-01# show authentication sessions
SW-ACCESS-01# show authentication sessions interface Gi0/1
SW-ACCESS-01# show authentication sessions interface Gi0/1 detail
SW-ACCESS-01# show dot1x all

! Test AAA connectivity to ISE
SW-ACCESS-01# test aaa group RADIUS-SERVERS jsmith Employee@123 new-code

! Check RADIUS statistics
SW-ACCESS-01# show radius statistics

! Verify VLAN membership
SW-ACCESS-01# show vlan brief
SW-ACCESS-01# show mac address-table vlan 10

! Verify dACL was downloaded
SW-ACCESS-01# show ip access-lists

! Check ISE reachability
SW-ACCESS-01# ping 192.168.1.100 source Vlan100
```

### On ISE — Monitor Events
- **Operations > RADIUS > Live Logs**: Real-time auth events
- **Operations > RADIUS > Live Sessions**: Active sessions
- **Operations > Troubleshoot > Diagnostic Tools > RADIUS Authentication Troubleshooting**: Step-by-step auth trace
- **Context Visibility > Endpoints**: View all profiled endpoints

---

## Troubleshooting Quick Reference

| Symptom | Likely Cause | Fix |
|---|---|---|
| Switch can't reach ISE | Firewall/routing | Verify UDP 1812/1813 open; `ping 192.168.1.100` from switch |
| `test aaa` returns server timeout | Wrong shared secret or IP | Verify `radius server ISE-PRIMARY` config matches ISE Network Device entry |
| All ports stuck in VLAN 99 | ISE policy misconfigured | Check Live Logs on ISE for failure reason |
| `show authentication sessions` shows no sessions | 802.1X not globally enabled | Verify `dot1x system-auth-control` is in running config |
| EAP-TLS fails with certificate error | Cert not trusted | Import CA cert into ISE Trusted Certificates |
| CoA not working | Port 3799 blocked | Verify `aaa server radius dynamic-author` config on switch |
| Posture always Unknown | AnyConnect NAM/Posture not installed | Install Posture module; check ISE posture policy |
