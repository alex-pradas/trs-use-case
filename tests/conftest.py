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

# Add tools directory to Python path for imports
tools_dir = Path(__file__).parent.parent / "tools"
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

# Load environment variables and configure logfire for the test process
load_dotenv()
logfire.configure(
    token="pylf_v1_eu_QPTnf71y7mj90cKkfwyTDbM9Xg694W2sdkw2cQj3pT5R",
    send_to_logfire=True,
    environment="test",
)
logfire.instrument_pydantic_ai()
