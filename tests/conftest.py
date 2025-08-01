"""
Pytest configuration file for test discovery and import resolution.

This file helps pytest and VS Code properly discover tests and resolve imports
from the tools directory.
"""

import sys
import os
from pathlib import Path
import logfire
from dotenv import load_dotenv

# Add project root directory to Python path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Also add tools directory for clean imports
tools_path = project_root / "tools"
if str(tools_path) not in sys.path:
    sys.path.insert(0, str(tools_path))

# Load environment variables and configure logfire for the test process
load_dotenv()
token = os.getenv("LOGFIRE_TOKEN")
logfire.configure(
    token=token,
    send_to_logfire=True,
    environment="test",
)
logfire.instrument_pydantic_ai()
