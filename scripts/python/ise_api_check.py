#!/usr/bin/env python3
"""
ise_api_check.py
================
Cisco ISE ERS (External RESTful Services) API Client

Provides functions to interact with Cisco ISE via its REST API:
  - List all profiled endpoints
  - Get active RADIUS sessions
  - Quarantine an endpoint by MAC address
  - Check posture status of an endpoint

Requirements:
  pip install requests

Author : Network Lab Team
Date   : 2024
ISE API Docs: https://developer.cisco.com/docs/identity-services-engine/
"""

import json
import sys
import logging
import requests
from requests.auth import HTTPBasicAuth

# ---------------------------------------------------------------------------
# CONFIGURATION — Edit these values before running
# ---------------------------------------------------------------------------
ISE_HOST = "192.168.1.100"          # ISE PAN (Primary Admin Node) IP or FQDN
USERNAME = "admin"                   # ISE admin username
PASSWORD = "ChangeMe123!"            # ISE admin password
VERIFY_SSL = False                   # Set True in production with valid certificate
ERS_PORT = 9060                      # ISE ERS API port (9060 for ISE < 3.1, 443 for ISE 3.1+)
MNT_PORT = 443                       # ISE MnT (Monitoring) port for session data

# Base URLs
ERS_BASE_URL = f"https://{ISE_HOST}:{ERS_PORT}/ers/config"
MNT_BASE_URL = f"https://{ISE_HOST}:{MNT_PORT}/admin/API/mnt"

# Common headers for ERS API
ERS_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "ERS-Media-Type": "ers.config.endpoint.1.0"
}

# ---------------------------------------------------------------------------
# LOGGING SETUP
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("ise_api.log")
    ]
)
log = logging.getLogger(__name__)

# Suppress InsecureRequestWarning when VERIFY_SSL=False
if not VERIFY_SSL:
    requests.packages.urllib3.disable_warnings(
        requests.packages.urllib3.exceptions.InsecureRequestWarning
    )


# ---------------------------------------------------------------------------
# HELPER: Generic API Request
# ---------------------------------------------------------------------------
def _api_get(url: str, params: dict = None, use_mnt: bool = False) -> dict | None:
    """
    Perform a GET request to the ISE API.

    Args:
        url (str): Full URL to request.
        params (dict): Optional query parameters.
        use_mnt (bool): Use MnT credentials/headers instead of ERS.

    Returns:
        dict: Parsed JSON response, or None on failure.
    """
    headers = ERS_HEADERS if not use_mnt else {"Accept": "application/json"}
    try:
        response = requests.get(
            url,
            auth=HTTPBasicAuth(USERNAME, PASSWORD),
            headers=headers,
            params=params,
            verify=VERIFY_SSL,
            timeout=15
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        log.error(f"Connection error: Cannot reach ISE at {ISE_HOST}. Check network/firewall.")
        return None
    except requests.exceptions.Timeout:
        log.error(f"Request timed out connecting to {url}")
        return None
    except requests.exceptions.HTTPError as e:
        log.error(f"HTTP error {response.status_code}: {response.text}")
        return None
    except json.JSONDecodeError:
        log.error(f"Failed to parse JSON response from {url}")
        return None


def _api_put(url: str, payload: dict) -> dict | None:
    """
    Perform a PUT request to update a resource in ISE ERS API.

    Args:
        url (str): Full resource URL.
        payload (dict): JSON body.

    Returns:
        dict: Parsed JSON response or None.
    """
    try:
        response = requests.put(
            url,
            auth=HTTPBasicAuth(USERNAME, PASSWORD),
            headers=ERS_HEADERS,
            json=payload,
            verify=VERIFY_SSL,
            timeout=15
        )
        response.raise_for_status()
        # PUT may return 200 OK with body, or 204 No Content
        if response.status_code == 204 or not response.text:
            return {"status": "success", "code": 204}
        return response.json()
    except requests.exceptions.HTTPError as e:
        log.error(f"HTTP error on PUT {url}: {response.status_code} - {response.text}")
        return None
    except Exception as e:
        log.error(f"Unexpected error on PUT {url}: {e}")
        return None


# ---------------------------------------------------------------------------
# FUNCTION 1: Get All Profiled Endpoints
# ---------------------------------------------------------------------------
def get_all_endpoints(page: int = 1, page_size: int = 100) -> list:
    """
    Retrieve all endpoints registered/profiled in ISE.

    Uses the ERS /endpoint endpoint with pagination support.

    Args:
        page (int): Page number to retrieve (default: 1).
        page_size (int): Number of results per page (default: 100, max: 100).

    Returns:
        list: List of endpoint dicts with id, name (MAC), description, etc.
    """
    log.info(f"Fetching all endpoints from ISE (page {page}, size {page_size})...")
    url = f"{ERS_BASE_URL}/endpoint"
    params = {"page": page, "size": page_size}

    result = _api_get(url, params=params)
    if not result:
        log.warning("No endpoints returned or request failed.")
        return []

    endpoints = result.get("SearchResult", {}).get("resources", [])
    total = result.get("SearchResult", {}).get("total", 0)
    log.info(f"Total endpoints in ISE: {total} | Retrieved: {len(endpoints)}")

    # Auto-paginate if there are more pages
    all_endpoints = list(endpoints)
    while len(all_endpoints) < total:
        page += 1
        params["page"] = page
        result = _api_get(url, params=params)
        if not result:
            break
        more = result.get("SearchResult", {}).get("resources", [])
        if not more:
            break
        all_endpoints.extend(more)
        log.info(f"  Paginating... retrieved {len(all_endpoints)}/{total}")

    # Optionally, fetch detailed info for each endpoint
    detailed_endpoints = []
    for ep in all_endpoints[:10]:  # Limit detail fetch to first 10 for demo
        detail_url = f"{ERS_BASE_URL}/endpoint/{ep['id']}"
        detail = _api_get(detail_url)
        if detail:
            detailed_endpoints.append(detail.get("ERSEndPoint", ep))
        else:
            detailed_endpoints.append(ep)

    return detailed_endpoints


# ---------------------------------------------------------------------------
# FUNCTION 2: Get Active RADIUS Sessions
# ---------------------------------------------------------------------------
def get_active_sessions() -> list:
    """
    Retrieve all currently active RADIUS authentication sessions from ISE MnT API.

    Uses the ISE Monitoring and Troubleshooting (MnT) REST API.
    Endpoint: /admin/API/mnt/Session/ActiveCount and /Session/ActiveList

    Returns:
        list: List of active session dicts containing:
              - calling_station_id (MAC address)
              - user_name
              - nas_ip_address (switch IP)
              - nas_port_id (switch port, e.g. GigabitEthernet0/1)
              - acct_session_id
              - framed_ip_address
              - audit_session_id
    """
    log.info("Fetching active RADIUS sessions from ISE MnT API...")
    url = f"{MNT_BASE_URL}/Session/ActiveList"

    result = _api_get(url, use_mnt=True)
    if not result:
        log.warning("No active sessions returned or request failed.")
        return []

    # MnT returns XML by default; with Accept: application/json it returns JSON
    # The structure varies; adjust key names based on your ISE version
    sessions = result.get("activeList", {}).get("activeSession", [])

    # Handle case where only one session returns as dict (not list)
    if isinstance(sessions, dict):
        sessions = [sessions]

    log.info(f"Active sessions found: {len(sessions)}")

    for sess in sessions[:5]:  # Print first 5 for demo
        mac = sess.get("calling_station_id", "N/A")
        user = sess.get("user_name", "N/A")
        nas = sess.get("nas_ip_address", "N/A")
        port = sess.get("nas_port_id", "N/A")
        ip = sess.get("framed_ip_address", "N/A")
        log.info(f"  Session: MAC={mac} | User={user} | NAS={nas} | Port={port} | IP={ip}")

    return sessions


# ---------------------------------------------------------------------------
# FUNCTION 3: Quarantine Endpoint by MAC Address
# ---------------------------------------------------------------------------
def quarantine_endpoint(mac_address: str) -> bool:
    """
    Move an endpoint to the quarantine state in ISE.

    This works by:
    1. Looking up the endpoint by MAC address
    2. Retrieving its current group assignment and attributes
    3. Updating the endpoint's group to the 'Quarantine' endpoint group
    4. (Optionally) triggering CoA via the MnT API to bounce the session

    Args:
        mac_address (str): MAC address in format "AA:BB:CC:DD:EE:FF" or "AA-BB-CC-DD-EE-FF"

    Returns:
        bool: True if quarantine succeeded, False otherwise.
    """
    # Normalize MAC address format (ISE typically uses colon-separated uppercase)
    mac = mac_address.upper().replace("-", ":").replace(".", ":")
    log.info(f"Quarantining endpoint: {mac}")

    # Step 1: Find endpoint by MAC
    search_url = f"{ERS_BASE_URL}/endpoint"
    params = {"filter": f"mac.EQ.{mac}"}
    search_result = _api_get(search_url, params=params)

    if not search_result:
        log.error(f"Failed to search for endpoint {mac}")
        return False

    resources = search_result.get("SearchResult", {}).get("resources", [])
    if not resources:
        log.warning(f"Endpoint {mac} not found in ISE. Ensure it has connected and been profiled.")
        return False

    endpoint_id = resources[0]["id"]
    log.info(f"Found endpoint {mac} with ID: {endpoint_id}")

    # Step 2: Fetch full endpoint details
    detail_url = f"{ERS_BASE_URL}/endpoint/{endpoint_id}"
    detail = _api_get(detail_url)
    if not detail:
        log.error(f"Failed to fetch endpoint details for ID {endpoint_id}")
        return False

    endpoint_data = detail.get("ERSEndPoint", {})

    # Step 3: Find the Quarantine Identity Group ID
    # ISE has predefined endpoint identity groups: Blacklist, GuestEndpoints, Profiled, Registered, etc.
    # We look for one named "Quarantine" or "Blacklist"
    group_url = f"{ERS_BASE_URL}/endpointgroup"
    group_params = {"filter": "name.EQ.Quarantine"}
    group_result = _api_get(group_url, params=group_params)

    quarantine_group_id = None
    if group_result:
        groups = group_result.get("SearchResult", {}).get("resources", [])
        if groups:
            quarantine_group_id = groups[0]["id"]
            log.info(f"Found Quarantine group ID: {quarantine_group_id}")

    if not quarantine_group_id:
        # Try Blacklist as fallback
        group_params["filter"] = "name.EQ.Blacklist"
        group_result = _api_get(group_url, params=group_params)
        if group_result:
            groups = group_result.get("SearchResult", {}).get("resources", [])
            if groups:
                quarantine_group_id = groups[0]["id"]
                log.info(f"Using Blacklist group as quarantine. ID: {quarantine_group_id}")

    if not quarantine_group_id:
        log.error("Could not find Quarantine or Blacklist endpoint group in ISE.")
        return False

    # Step 4: Update endpoint to quarantine group
    update_payload = {
        "ERSEndPoint": {
            "id": endpoint_id,
            "mac": mac,
            "groupId": quarantine_group_id,
            "staticGroupAssignment": True,
            "customAttributes": {
                "customAttributes": {
                    "QuarantineReason": "Automated quarantine via API",
                    "QuarantineTime": "2024-01-01T00:00:00"
                }
            }
        }
    }

    update_url = f"{ERS_BASE_URL}/endpoint/{endpoint_id}"
    result = _api_put(update_url, update_payload)

    if result:
        log.info(f"✅ Endpoint {mac} successfully moved to Quarantine group.")

        # Step 5: Trigger CoA to immediately apply the new policy (optional)
        coa_url = f"{MNT_BASE_URL}/CoA/Disconnect/{mac}/1"
        # CoA type 1 = port-bounce (re-authenticate)
        coa_result = _api_get(coa_url, use_mnt=True)
        if coa_result:
            log.info(f"✅ CoA triggered for {mac} — session will be re-authenticated with quarantine policy.")
        else:
            log.warning(f"CoA trigger failed or not supported. Endpoint group updated but current session unchanged until re-auth.")

        return True
    else:
        log.error(f"Failed to update endpoint {mac} to quarantine group.")
        return False


# ---------------------------------------------------------------------------
# FUNCTION 4: Get Endpoint Posture Status
# ---------------------------------------------------------------------------
def get_endpoint_posture(mac_address: str) -> dict:
    """
    Check the posture assessment status of an endpoint.

    Uses the ISE MnT API to look up the latest RADIUS session for the
    endpoint and extract posture-related attributes.

    Args:
        mac_address (str): MAC address in format "AA:BB:CC:DD:EE:FF"

    Returns:
        dict: Posture information including:
              - posture_status: Compliant / NonCompliant / Unknown / Pending
              - posture_timestamp: When posture was last assessed
              - posture_policy: Which policy was applied
              - failure_reason: If non-compliant, why
              - operating_system: Detected OS
    """
    mac = mac_address.upper().replace("-", ":").replace(".", ":")
    log.info(f"Checking posture status for endpoint: {mac}")

    # Query MnT for the endpoint's latest session detail
    # ISE MnT API: /Session/MACAddress/{mac}
    mac_url_format = mac.replace(":", "-")  # MnT URL uses dash format
    url = f"{MNT_BASE_URL}/Session/MACAddress/{mac_url_format}"

    result = _api_get(url, use_mnt=True)
    if not result:
        log.warning(f"No session data found for {mac}. Device may not be connected.")
        return {
            "mac": mac,
            "posture_status": "Unknown",
            "reason": "No active session found in ISE"
        }

    # Parse out posture-related fields from the session
    session = result.get("sessionParameters", {})

    posture_status = session.get("posture_status", "Unknown")
    posture_timestamp = session.get("posture_timestamp", "N/A")
    operating_system = session.get("operating_system", "Unknown")
    failure_reason = session.get("failure_reason", "")
    username = session.get("user_name", "N/A")
    nas_ip = session.get("nas_ip_address", "N/A")
    framed_ip = session.get("framed_ip_address", "N/A")

    posture_info = {
        "mac": mac,
        "username": username,
        "framed_ip": framed_ip,
        "nas_ip": nas_ip,
        "posture_status": posture_status,
        "posture_timestamp": posture_timestamp,
        "operating_system": operating_system,
        "failure_reason": failure_reason
    }

    # Log a human-readable summary
    status_emoji = {
        "Compliant": "✅",
        "NonCompliant": "❌",
        "Unknown": "❓",
        "Pending": "⏳"
    }.get(posture_status, "❔")

    log.info(f"{status_emoji} Posture for {mac} ({username} @ {framed_ip}): {posture_status}")
    if posture_status == "NonCompliant" and failure_reason:
        log.info(f"   Failure Reason: {failure_reason}")

    return posture_info


# ---------------------------------------------------------------------------
# FUNCTION 5: List Endpoint Groups
# ---------------------------------------------------------------------------
def list_endpoint_groups() -> list:
    """
    List all endpoint identity groups defined in ISE.

    Returns:
        list: List of groups with id and name.
    """
    log.info("Fetching endpoint identity groups...")
    url = f"{ERS_BASE_URL}/endpointgroup"
    result = _api_get(url)
    if not result:
        return []
    groups = result.get("SearchResult", {}).get("resources", [])
    for g in groups:
        log.info(f"  Group: {g.get('name')} (ID: {g.get('id')})")
    return groups


# ---------------------------------------------------------------------------
# MAIN — Example usage
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print("  Cisco ISE ERS API Client — Zero Trust Lab")
    print("=" * 60)
    print(f"  ISE Host : {ISE_HOST}")
    print(f"  Username : {USERNAME}")
    print(f"  SSL Verify: {VERIFY_SSL}")
    print("=" * 60)

    # --- 1. List Endpoint Groups ---
    print("\n[1] ENDPOINT IDENTITY GROUPS")
    print("-" * 40)
    groups = list_endpoint_groups()
    print(f"    Total Groups: {len(groups)}")

    # --- 2. Get All Endpoints ---
    print("\n[2] PROFILED ENDPOINTS")
    print("-" * 40)
    endpoints = get_all_endpoints(page=1, page_size=10)
    print(f"    Total Endpoints Retrieved: {len(endpoints)}")
    for ep in endpoints[:5]:
        mac = ep.get("mac", ep.get("name", "N/A"))
        profile = ep.get("profileId", ep.get("endpointProfileId", "N/A"))
        group = ep.get("groupId", "N/A")
        print(f"    MAC: {mac} | Profile: {profile} | Group: {group}")

    # --- 3. Get Active Sessions ---
    print("\n[3] ACTIVE RADIUS SESSIONS")
    print("-" * 40)
    sessions = get_active_sessions()
    print(f"    Active Sessions: {len(sessions)}")

    # --- 4. Check Posture for a Known Device ---
    print("\n[4] POSTURE STATUS CHECK")
    print("-" * 40)
    test_mac = "AA:BB:CC:DD:EE:FF"  # Replace with real MAC from your environment
    posture = get_endpoint_posture(test_mac)
    print(f"    Result: {json.dumps(posture, indent=4)}")

    # --- 5. Quarantine a Device (commented out for safety) ---
    print("\n[5] QUARANTINE ENDPOINT (Dry Run — uncomment to execute)")
    print("-" * 40)
    quarantine_mac = "11:22:33:44:55:66"  # Replace with the MAC to quarantine
    # result = quarantine_endpoint(quarantine_mac)
    # print(f"    Quarantine Result: {result}")
    print(f"    Would quarantine: {quarantine_mac} (line commented out for safety)")

    print("\n" + "=" * 60)
    print("  ISE API Check Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
