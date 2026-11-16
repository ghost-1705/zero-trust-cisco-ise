#!/usr/bin/env python3
"""
vlan_audit.py
=============
802.1X Authentication Session Auditor for Cisco Switches

Uses Netmiko (SSH) to connect to multiple Cisco Catalyst switches,
runs 'show authentication sessions' and 'show dot1x all', parses
the output, builds a structured session table, and saves to CSV.

Usage:
    python vlan_audit.py                   # Uses default switches.json
    python vlan_audit.py --config my.json  # Specify custom switch config file
    python vlan_audit.py --switch 192.168.100.11  # Audit a single switch

Output:
    - Console table (via tabulate)
    - audit_report_YYYYMMDD_HHMMSS.csv

Requirements:
    pip install netmiko tabulate pandas

Author : Network Lab Team
Date   : 2024
"""

import argparse
import csv
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import pandas as pd
    from netmiko import ConnectHandler, NetmikoTimeoutException, NetmikoAuthenticationException
    from tabulate import tabulate
except ImportError as e:
    print(f"[ERROR] Missing dependency: {e}")
    print("Install with: pip install netmiko tabulate pandas")
    sys.exit(1)

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
DEFAULT_CONFIG_FILE = "switches.json"
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "ChangeMe123!"
DEFAULT_ENABLE_SECRET = "ChangeMe123!"
SSH_TIMEOUT = 30         # seconds
COMMAND_TIMEOUT = 60     # seconds for 'show' commands

# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("vlan_audit.log")
    ]
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DEFAULT SWITCH CONFIG (used if no JSON file provided)
# ---------------------------------------------------------------------------
DEFAULT_SWITCHES = [
    {
        "device_type": "cisco_ios",
        "host": "192.168.100.11",
        "username": DEFAULT_USERNAME,
        "password": DEFAULT_PASSWORD,
        "secret": DEFAULT_ENABLE_SECRET,
        "port": 22,
        "name": "SW-ACCESS-01",
        "location": "Building A, Floor 1"
    },
    {
        "device_type": "cisco_ios",
        "host": "192.168.100.12",
        "username": DEFAULT_USERNAME,
        "password": DEFAULT_PASSWORD,
        "secret": DEFAULT_ENABLE_SECRET,
        "port": 22,
        "name": "SW-ACCESS-02",
        "location": "Building A, Floor 2"
    }
]


# ---------------------------------------------------------------------------
# PARSER: show authentication sessions
# ---------------------------------------------------------------------------
def parse_auth_sessions(raw_output: str, switch_name: str) -> list:
    """
    Parse output of 'show authentication sessions' into structured records.

    Example output line:
    Gi0/1    AA:BB:CC:DD:EE:FF    dot1x    Auth    jsmith    10

    Returns:
        list of dicts with keys:
          interface, mac_address, method, status, username, vlan,
          switch_name, auth_domain, session_id
    """
    sessions = []

    # Regex for 'show authentication sessions' tabular output
    # Matches: Interface | MAC | Method | Domain | Status | Fg | Session ID
    # Example: Gi0/1  aa:bb:cc:dd:ee:ff  dot1x  DATA  Auth
    session_pattern = re.compile(
        r"(?P<interface>Gi\S+|Fa\S+|Te\S+|Gi\d+/\d+)\s+"
        r"(?P<mac>[0-9a-fA-F]{4}\.[0-9a-fA-F]{4}\.[0-9a-fA-F]{4}|"
        r"[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2}:[0-9a-fA-F]{2})\s+"
        r"(?P<method>\S+)\s+"
        r"(?P<domain>\S+)\s+"
        r"(?P<status>Auth|Unauth|Running|Failed|NoResp|Authz\s+Success|Authz\s+Failed)\s*"
        r"(?P<fg>\S*)\s*",
        re.IGNORECASE
    )

    # Regex to extract VLAN from 'show authentication sessions interface Gi0/1' detail
    vlan_pattern = re.compile(r"Authorized\s+By\s*:\s*(\S+)", re.IGNORECASE)
    vlan_local_pattern = re.compile(r"Vlan\s+Policy\s*:\s*(\d+)", re.IGNORECASE)
    username_pattern = re.compile(r"User-Name\s*:\s*(\S+)", re.IGNORECASE)

    for match in session_pattern.finditer(raw_output):
        interface = match.group("interface")
        mac = match.group("mac")
        method = match.group("method")
        domain = match.group("domain")
        status = match.group("status").strip()

        # Normalize MAC to colon format
        if "." in mac:
            # Cisco dotted format: aabb.ccdd.eeff → AA:BB:CC:DD:EE:FF
            mac_clean = mac.replace(".", "")
            mac = ":".join(mac_clean[i:i+2] for i in range(0, 12, 2)).upper()
        else:
            mac = mac.upper()

        sessions.append({
            "switch_name": switch_name,
            "interface": interface,
            "mac_address": mac,
            "auth_method": method,
            "auth_domain": domain,
            "auth_status": status,
            "username": "",       # Will be filled from detailed output
            "vlan": "",           # Will be filled from detailed output
            "ip_address": "",     # Will be filled from ARP/DHCP binding
        })

    # Also try to extract username from inline session listing (newer IOS)
    # Pattern: Username field in tabular output
    username_inline = re.compile(
        r"(?P<user>[a-zA-Z0-9_@.\-]+)\s+(?:Auth)\s*$",
        re.MULTILINE
    )

    return sessions


# ---------------------------------------------------------------------------
# PARSER: show authentication sessions interface <intf> detail
# ---------------------------------------------------------------------------
def parse_session_detail(detail_output: str) -> dict:
    """
    Parse detailed output from 'show authentication sessions interface X detail'.

    Returns dict with username, vlan, ip_address, posture_status, etc.
    """
    detail = {}

    patterns = {
        "username": r"User-Name\s*:\s*(.+)",
        "ipv4_address": r"IPv4\s+Address\s*:\s*(\d+\.\d+\.\d+\.\d+)",
        "vlan": r"Vlan\s+Policy\s*:\s*(\d+)",
        "auth_method": r"Method\s*:\s*(\w+)",
        "acl": r"ACS\s+ACL\s*:\s*(\S+)",
        "url_redirect": r"URL\s+Redirect\s*:\s*(\S+)",
        "posture_status": r"Posture\s+Status\s*:\s*(\S+)",
        "session_id": r"Audit\s+Session\s+ID\s*:\s*(\S+)",
        "handle": r"Handle\s*:\s*(\S+)",
        "current_policy": r"Current\s+Policy\s*:\s*(.+)",
        "domain": r"Domain\s*:\s*(\S+)"
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, detail_output, re.IGNORECASE)
        detail[key] = match.group(1).strip() if match else ""

    return detail


# ---------------------------------------------------------------------------
# PARSER: show dot1x all
# ---------------------------------------------------------------------------
def parse_dot1x_all(raw_output: str, switch_name: str) -> list:
    """
    Parse 'show dot1x all' to get per-port dot1x configuration state.

    Returns list of dicts with:
      interface, pae_role, client_mac, eap_method, auth_sm_state, switch_name
    """
    records = []
    current_interface = None

    for line in raw_output.splitlines():
        line = line.strip()

        iface_match = re.match(r"^Dot1x\s+Info\s+for\s+(\S+)", line, re.IGNORECASE)
        if iface_match:
            current_interface = iface_match.group(1)
            continue

        if current_interface:
            if re.match(r"^PAE", line, re.IGNORECASE):
                pae = re.search(r"=\s*(\w+)", line)
                records.append({
                    "switch_name": switch_name,
                    "interface": current_interface,
                    "pae_role": pae.group(1) if pae else "",
                    "eap_method": "",
                    "auth_sm_state": "",
                    "client_mac": ""
                })

            if records and records[-1]["interface"] == current_interface:
                if "AuthSM" in line or "Authenticator" in line:
                    state = re.search(r"State\s*=\s*(\S+)", line)
                    if state:
                        records[-1]["auth_sm_state"] = state.group(1)

                eap_match = re.search(r"EAP\s+Method\s*=\s*(\S+)", line, re.IGNORECASE)
                if eap_match:
                    records[-1]["eap_method"] = eap_match.group(1)

    return records


# ---------------------------------------------------------------------------
# SSH CONNECTION: Connect to switch and run commands
# ---------------------------------------------------------------------------
def audit_switch(switch_config: dict) -> list:
    """
    SSH into a Cisco switch and collect authentication session data.

    Args:
        switch_config (dict): Netmiko connection parameters + 'name' and 'location'.

    Returns:
        list: Combined session records for all ports on this switch.
    """
    switch_name = switch_config.get("name", switch_config.get("host", "Unknown"))
    host = switch_config.get("host")
    location = switch_config.get("location", "")

    log.info(f"Connecting to {switch_name} ({host}) [{location}]...")

    # Build Netmiko connection dict (remove custom keys)
    conn_params = {k: v for k, v in switch_config.items()
                   if k not in ("name", "location")}

    try:
        with ConnectHandler(**conn_params, conn_timeout=SSH_TIMEOUT) as net_connect:
            # Enter enable mode
            if net_connect.check_enable_mode():
                log.debug(f"{switch_name}: Already in enable mode.")
            else:
                net_connect.enable()
                log.debug(f"{switch_name}: Entered enable mode.")

            # Command 1: show authentication sessions
            log.info(f"{switch_name}: Running 'show authentication sessions'...")
            auth_output = net_connect.send_command(
                "show authentication sessions",
                read_timeout=COMMAND_TIMEOUT
            )
            sessions = parse_auth_sessions(auth_output, switch_name)
            log.info(f"{switch_name}: Found {len(sessions)} session(s).")

            # Command 2: Enrich each session with detailed info
            for sess in sessions:
                iface = sess["interface"]
                log.debug(f"{switch_name}: Fetching detail for interface {iface}...")
                detail_output = net_connect.send_command(
                    f"show authentication sessions interface {iface} detail",
                    read_timeout=COMMAND_TIMEOUT
                )
                detail = parse_session_detail(detail_output)
                sess.update({
                    "username": detail.get("username", ""),
                    "vlan": detail.get("vlan", ""),
                    "ip_address": detail.get("ipv4_address", ""),
                    "posture_status": detail.get("posture_status", ""),
                    "acl_applied": detail.get("acl", ""),
                    "session_id": detail.get("session_id", ""),
                    "current_policy": detail.get("current_policy", ""),
                    "switch_location": location
                })

            # Command 3: show dot1x all
            log.info(f"{switch_name}: Running 'show dot1x all'...")
            dot1x_output = net_connect.send_command(
                "show dot1x all",
                read_timeout=COMMAND_TIMEOUT
            )
            dot1x_records = parse_dot1x_all(dot1x_output, switch_name)

            # Merge dot1x data into sessions (match by interface)
            dot1x_map = {r["interface"]: r for r in dot1x_records}
            for sess in sessions:
                iface = sess["interface"]
                if iface in dot1x_map:
                    sess["pae_role"] = dot1x_map[iface].get("pae_role", "")
                    sess["eap_method"] = dot1x_map[iface].get("eap_method", "")
                    sess["dot1x_state"] = dot1x_map[iface].get("auth_sm_state", "")
                else:
                    sess.setdefault("pae_role", "")
                    sess.setdefault("eap_method", "")
                    sess.setdefault("dot1x_state", "")

            log.info(f"✅ {switch_name}: Audit complete. {len(sessions)} sessions collected.")
            return sessions

    except NetmikoTimeoutException:
        log.error(f"❌ {switch_name} ({host}): Connection timed out. Check SSH, firewall, or VTY config.")
        return []
    except NetmikoAuthenticationException:
        log.error(f"❌ {switch_name} ({host}): Authentication failed. Check username/password/enable secret.")
        return []
    except Exception as e:
        log.error(f"❌ {switch_name} ({host}): Unexpected error: {type(e).__name__}: {e}")
        return []


# ---------------------------------------------------------------------------
# REPORT: Print table and save CSV
# ---------------------------------------------------------------------------
def generate_report(all_sessions: list, output_dir: str = ".") -> str:
    """
    Generate console table and save CSV report.

    Args:
        all_sessions (list): Combined sessions from all switches.
        output_dir (str): Directory to save CSV.

    Returns:
        str: Path to the saved CSV file.
    """
    if not all_sessions:
        log.warning("No sessions to report.")
        return ""

    # Define columns for display and CSV
    columns = [
        "switch_name", "switch_location", "interface", "mac_address",
        "username", "ip_address", "vlan", "auth_method", "eap_method",
        "auth_status", "posture_status", "acl_applied", "current_policy", "session_id"
    ]

    # Ensure all columns exist in every record
    for sess in all_sessions:
        for col in columns:
            sess.setdefault(col, "")

    # Build DataFrame
    df = pd.DataFrame(all_sessions, columns=columns)

    # --- Console Table (abbreviated columns) ---
    display_cols = ["switch_name", "interface", "mac_address", "username",
                    "ip_address", "vlan", "auth_method", "auth_status", "posture_status"]
    print("\n" + "=" * 120)
    print("  802.1X AUTHENTICATION SESSION AUDIT REPORT")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 120)
    print(tabulate(df[display_cols].fillna(""), headers="keys", tablefmt="grid", showindex=False))
    print(f"\n  Total Sessions: {len(all_sessions)}")

    # Summary by status
    status_counts = df["auth_status"].value_counts()
    print("\n  Auth Status Summary:")
    for status, count in status_counts.items():
        print(f"    {status}: {count}")

    # Summary by VLAN
    vlan_counts = df["vlan"].value_counts()
    print("\n  VLAN Distribution:")
    for vlan, count in vlan_counts.items():
        label = {
            "10": "EMPLOYEES", "20": "CONTRACTORS", "30": "IOT_DEVICES",
            "40": "GUEST", "50": "VOIP", "99": "QUARANTINE"
        }.get(str(vlan), "UNKNOWN")
        print(f"    VLAN {vlan} ({label}): {count} session(s)")

    # --- Save to CSV ---
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"audit_report_{timestamp}.csv"
    csv_path = os.path.join(output_dir, csv_filename)
    df.to_csv(csv_path, index=False)
    log.info(f"✅ Report saved to: {csv_path}")
    print(f"\n  CSV Report saved: {csv_path}")
    print("=" * 120)

    return csv_path


# ---------------------------------------------------------------------------
# LOAD SWITCHES FROM CONFIG FILE
# ---------------------------------------------------------------------------
def load_switches_from_file(config_file: str) -> list:
    """
    Load switch configurations from a JSON file.

    Expected JSON format:
    [
      {
        "name": "SW-ACCESS-01",
        "host": "192.168.100.11",
        "username": "admin",
        "password": "secret",
        "secret": "enable_secret",
        "device_type": "cisco_ios",
        "port": 22,
        "location": "Floor 1"
      },
      ...
    ]
    """
    path = Path(config_file)
    if not path.exists():
        log.warning(f"Config file '{config_file}' not found. Using built-in default switches.")
        return DEFAULT_SWITCHES

    try:
        with open(path) as f:
            switches = json.load(f)
        log.info(f"Loaded {len(switches)} switch(es) from {config_file}")
        return switches
    except json.JSONDecodeError as e:
        log.error(f"Invalid JSON in {config_file}: {e}")
        return DEFAULT_SWITCHES


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="802.1X VLAN Audit Tool — Cisco ISE / 802.1X Network"
    )
    parser.add_argument(
        "--config", "-c",
        default=DEFAULT_CONFIG_FILE,
        help=f"Path to switches JSON config file (default: {DEFAULT_CONFIG_FILE})"
    )
    parser.add_argument(
        "--switch", "-s",
        help="Audit a single switch by IP address (overrides --config)"
    )
    parser.add_argument(
        "--username", "-u",
        default=DEFAULT_USERNAME,
        help="SSH username (used only with --switch)"
    )
    parser.add_argument(
        "--password", "-p",
        default=DEFAULT_PASSWORD,
        help="SSH password (used only with --switch)"
    )
    parser.add_argument(
        "--output", "-o",
        default=".",
        help="Directory for CSV output (default: current directory)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose/debug logging"
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    print("=" * 60)
    print("  Cisco 802.1X VLAN Audit Tool")
    print("  Zero Trust Network Lab")
    print("=" * 60)

    # Build switch list
    if args.switch:
        switches = [{
            "device_type": "cisco_ios",
            "host": args.switch,
            "username": args.username,
            "password": args.password,
            "secret": args.password,
            "port": 22,
            "name": args.switch,
            "location": "Single-switch audit"
        }]
        log.info(f"Single-switch mode: {args.switch}")
    else:
        switches = load_switches_from_file(args.config)

    log.info(f"Auditing {len(switches)} switch(es)...")

    # Collect all sessions from all switches
    all_sessions = []
    for switch in switches:
        sessions = audit_switch(switch)
        all_sessions.extend(sessions)

    # Generate report
    generate_report(all_sessions, output_dir=args.output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
