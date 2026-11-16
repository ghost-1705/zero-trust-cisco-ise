"""
test_ise_api.py
===============
Unit tests for Cisco ISE ERS / MnT API client functions in ise_api_check.py.
"""

import sys
import os
import unittest
from unittest.mock import patch

# Add scripts/python to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts", "python")))

import ise_api_check

class TestIseApiClient(unittest.TestCase):
    @patch("ise_api_check._api_get")
    def test_get_all_endpoints(self, mock_get):
        mock_get.return_value = {
            "SearchResult": {
                "total": 2,
                "resources": [
                    {"id": "ep-1", "name": "00:1A:2B:3C:4D:5E"},
                    {"id": "ep-2", "name": "00:2B:3C:4D:5E:6F"}
                ]
            }
        }
        endpoints = ise_api_check.get_all_endpoints(page=1, page_size=10)
        self.assertEqual(len(endpoints), 2)
        self.assertEqual(endpoints[0]["name"], "00:1A:2B:3C:4D:5E")

    @patch("ise_api_check._api_get")
    def test_get_endpoint_posture_compliant(self, mock_get):
        mock_get.return_value = {
            "sessionParameters": {
                "posture_status": "Compliant",
                "posture_timestamp": "2024-03-01T10:00:00Z",
                "operating_system": "Windows 11",
                "user_name": "john.doe@enterprise.local",
                "framed_ip_address": "10.10.10.101"
            }
        }
        res = ise_api_check.get_endpoint_posture("00:1A:2B:3C:4D:5E")
        self.assertEqual(res.get("posture_status"), "Compliant")
        self.assertEqual(res.get("operating_system"), "Windows 11")

    def test_ers_headers_defined(self):
        self.assertIn("Accept", ise_api_check.ERS_HEADERS)
        self.assertEqual(ise_api_check.ERS_HEADERS["Accept"], "application/json")
        self.assertEqual(ise_api_check.ERS_HEADERS["Content-Type"], "application/json")

if __name__ == "__main__":
    unittest.main()
