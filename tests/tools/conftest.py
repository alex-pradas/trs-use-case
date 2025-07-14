"""
Pytest configuration file for tools tests.

This file helps pytest and VS Code properly discover tests and resolve imports
from the tools directory for tests in tests/tools/.
"""

import sys
import os
from pathlib import Path
import logfire
from dotenv import load_dotenv

# Add project root directory to Python path for imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Load environment variables and configure logfire for the test process
load_dotenv()
logfire.configure(
    token="***REMOVED***",
    send_to_logfire=True,
    environment="test",
)
logfire.instrument_pydantic_ai()