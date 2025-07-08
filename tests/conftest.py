"""
Pytest configuration file for test discovery and import resolution.

This file helps pytest and VS Code properly discover tests and resolve imports
from the tools directory.
"""

import sys
import os
from pathlib import Path

# Add tools directory to Python path for imports
tools_dir = Path(__file__).parent.parent / "tools"
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))