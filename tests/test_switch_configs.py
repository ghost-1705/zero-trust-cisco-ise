"""
test_switch_configs.py
======================
Unit tests validating that all Cisco switch configurations implement
essential Zero Trust, AAA, and 802.1X security baselines.
"""

import os
import unittest

CONFIGS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "configs", "switches"))

def read_config(filename):
    path = os.path.join(CONFIGS_DIR, filename)
    assert os.path.exists(path), f"Config file missing: {path}"
    with open(path, "r") as f:
        return f.read()

class TestSwitchConfigurations(unittest.TestCase):
    def test_access_switch_01_aaa_baseline(self):
        cfg = read_config("access-switch-01.cfg")
        self.assertIn("aaa new-model", cfg, "aaa new-model must be enabled")
        self.assertIn("dot1x system-auth-control", cfg, "dot1x system-auth-control must be enabled")
        self.assertIn("aaa authentication dot1x default group", cfg, "802.1X AAA authentication group must be defined")
        self.assertIn("aaa authorization network default group", cfg, "AAA network authorization group must be defined")

    def test_access_switch_01_dynamic_author_coa(self):
        cfg = read_config("access-switch-01.cfg")
        self.assertIn("aaa server radius dynamic-author", cfg, "RFC 5176 dynamic authorization (CoA) must be enabled")
        self.assertTrue("port 3799" in cfg or "client" in cfg, "CoA client/port configuration must exist")

    def test_access_switch_01_port_security_controls(self):
        cfg = read_config("access-switch-01.cfg")
        self.assertTrue("spanning-tree portfast" in cfg or "spanning-tree bpduguard enable" in cfg)
        self.assertIn("authentication port-control auto", cfg)
        self.assertIn("dot1x pae authenticator", cfg)

    def test_core_switch_routing_and_dhcp(self):
        cfg = read_config("core-switch.cfg")
        self.assertIn("ip routing", cfg, "Core switch must enable IP routing")
        self.assertIn("interface Vlan10", cfg, "VLAN 10 Employee SVI must exist on Core")
        self.assertIn("interface Vlan99", cfg, "VLAN 99 Quarantine SVI must exist on Core")

if __name__ == "__main__":
    unittest.main()
