#!/usr/bin/env python3
"""
Test file to verify debugging setup works.
"""

import sys
import os

# Add Odoo to path
server_path = os.path.join(os.path.dirname(__file__), '../../')
sys.path.insert(0, server_path)

print("Testing Odoo module import...")
print(f"Python path: {sys.executable}")
print(f"Working directory: {os.getcwd()}")

try:
    from odoo import models, fields
    print("✓ Successfully imported Odoo modules!")
    print("✓ Debugging is working correctly!")
except ImportError as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)
