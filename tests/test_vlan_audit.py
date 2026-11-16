"""
test_vlan_audit.py
==================
Unit tests for the switch authentication session parser in vlan_audit.py.
"""

import sys
import os
import unittest

# Add scripts/python to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts", "python")))

from vlan_audit import parse_auth_sessions, parse_session_detail

SAMPLE_AUTH_SESSIONS = """
Interface    Identifier     Method  Domain  Status          Fg  Session ID
-----------------------------------------------------------------------------
Gi0/1        001a.2b3c.4d5e dot1x   DATA    Authz Success        C0A8640B00000010
Gi0/2        002b.3c4d.5e6f dot1x   DATA    Authz Success        C0A8640B00000011
Gi0/3        0050.6003.0001 mab     VOICE   Authz Success        C0A8640B00000012
Gi0/4        000c.29a1.b2c3 mab     DATA    Authz Success        C0A8640B00000013
"""

SAMPLE_DETAIL_OUTPUT = """
            Interface:  GigabitEthernet0/1
          MAC Address:  001a.2b3c.4d5e
         IPv4 Address:  10.10.10.101
            User-Name:  john.doe@enterprise.local
               Status:  Authorized
               Domain:  DATA
       Oper host mode:  single-host
     Oper control dir:  both
         Session timeout: N/A
    Common Session ID:  C0A8640B00000010
      Acct Session ID:  0x0000001A
               Handle:  0x4A000010
       Current Policy:  POLICY_Gi0/1

Local Policies:

Server Policies:
            Vlan Group:  10
                  dACL:  ACS:inacl#1=permit ip any any

Method status list:
       Method           State
        dot1x           Authc Success
"""

class TestVlanAuditParser(unittest.TestCase):
    def test_parse_auth_sessions(self):
        sessions = parse_auth_sessions(SAMPLE_AUTH_SESSIONS, "SW-ACCESS-01")
        self.assertEqual(len(sessions), 4)
        
        first = sessions[0]
        self.assertEqual(first["interface"], "Gi0/1")
        self.assertEqual(first["mac_address"], "00:1A:2B:3C:4D:5E")
        self.assertEqual(first["auth_method"], "dot1x")
        self.assertEqual(first["auth_domain"], "DATA")
        self.assertEqual(first["auth_status"], "Authz Success")
        self.assertEqual(first["switch_name"], "SW-ACCESS-01")

    def test_parse_session_detail(self):
        detail = parse_session_detail(SAMPLE_DETAIL_OUTPUT)
        self.assertEqual(detail["username"], "john.doe@enterprise.local")
        self.assertEqual(detail["vlan"], "10")
        self.assertIn("acl", detail)
        self.assertIn("permit ip any any", detail["acl"])

if __name__ == "__main__":
    unittest.main()
