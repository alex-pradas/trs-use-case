#!/usr/bin/env python3
"""
Unified MCP Server Startup Script

This script starts multiple MCP servers concurrently using multiprocessing.
By default, it starts all available servers, but can be configured to start
only specific servers using the --only flag.

Usage:
    # Start all servers (default)
    uv run python tools/mcps/start_servers.py
    uv run python tools/mcps/start_servers.py --all

    # Start specific servers only
    uv run python tools/mcps/start_servers.py --only loads
    uv run python tools/mcps/start_servers.py --only loads,python
    uv run python tools/mcps/start_servers.py --only script

    # Choose transport
    uv run python tools/mcps/start_servers.py --transport http
    uv run python tools/mcps/start_servers.py --transport stdio
"""

import sys
import argparse
import multiprocessing
import signal
import time
import logging
from pathlib import Path
from typing import Callable, Any
from dataclasses import dataclass

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("MCP_Starter")

# Add the tools directory to Python path
tools_dir = Path(__file__).parent.parent
if str(tools_dir) not in sys.path:
    sys.path.insert(0, str(tools_dir))

# Import the MCP server creation function
from mcps.loads_mcp_server import create_mcp_server as create_loads_server  # noqa: E402


@dataclass
class ServerConfig:
    """Configuration for an MCP server."""

    name: str
    key: str
    create_func: Callable
    default_port: int
    description: str
    startup_args: dict[str, Any] = None


# Server configurations
SERVER_CONFIGS = {
    "loads": ServerConfig(
        name="LoadSet MCP Server",
        key="loads",
        create_func=create_loads_server,
        default_port=8000,
        description="LoadSet operations and comparisons",
    ),
}


def run_server(
    server_config: ServerConfig, transport: str = "http", port: int | None = None
) -> None:
    """
    Run a single MCP server in a separate process.

    Args:
        server_config: Configuration for the server to run
        transport: Transport type ("http" or "stdio")
        port: Port to run on (uses default if None)
    """
    try:
        # Use provided port or default
        server_port = port if port is not None else server_config.default_port

        # Create the server
        if server_config.startup_args:
            server = server_config.create_func(**server_config.startup_args)
        else:
            server = server_config.create_func()

        # Start the server
        logger.info(f"Starting {server_config.name} on port {server_port}")

        if transport == "http":
            server.run(transport="http", port=server_port)
        else:
            server.run(transport="stdio")

    except Exception as e:
        logger.error(f"Failed to start {server_config.name}: {e}")
        sys.exit(1)


class MCPServerManager:
    """Manages multiple MCP servers using multiprocessing."""

    def __init__(self, transport: str = "http"):
        self.transport = transport
        self.processes: dict[str, multiprocessing.Process] = {}
        self.running = False

        # Set up signal handling
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info("Received shutdown signal, stopping all servers...")
        self.stop_all_servers()
        sys.exit(0)

    def start_server(self, server_key: str, port: int | None = None) -> bool:
        """
        Start a single server.

        Args:
            server_key: Key identifying the server to start
            port: Port to run on (uses default if None)

        Returns:
            bool: True if server started successfully
        """
        if server_key not in SERVER_CONFIGS:
            logger.error(f"Unknown server: {server_key}")
            return False

        if server_key in self.processes:
            logger.warning(f"Server {server_key} is already running")
            return True

        config = SERVER_CONFIGS[server_key]
        server_port = port if port is not None else config.default_port

        # Create and start the process
        process = multiprocessing.Process(
            target=run_server,
            args=(config, self.transport, server_port),
            name=f"mcp-{server_key}",
        )

        try:
            process.start()
            self.processes[server_key] = process

            # Give the server a moment to start
            time.sleep(0.5)

            if process.is_alive():
                logger.info(
                    f"✓ {config.name} started successfully (PID: {process.pid}, Port: {server_port})"
                )
                return True
            else:
                logger.error(f"✗ {config.name} failed to start")
                return False

        except Exception as e:
            logger.error(f"Failed to start {config.name}: {e}")
            return False

    def stop_server(self, server_key: str) -> bool:
        """
        Stop a single server.

        Args:
            server_key: Key identifying the server to stop

        Returns:
            bool: True if server stopped successfully
        """
        if server_key not in self.processes:
            logger.warning(f"Server {server_key} is not running")
            return True

        process = self.processes[server_key]
        config = SERVER_CONFIGS[server_key]

        try:
            logger.info(f"Stopping {config.name}...")
            process.terminate()
            process.join(timeout=5)

            if process.is_alive():
                logger.warning(f"Force killing {config.name}...")
                process.kill()
                process.join(timeout=2)

            del self.processes[server_key]
            logger.info(f"✓ {config.name} stopped")
            return True

        except Exception as e:
            logger.error(f"Error stopping {config.name}: {e}")
            return False

    def start_servers(self, server_keys: list[str]) -> bool:
        """
        Start multiple servers.

        Args:
            server_keys: List of server keys to start

        Returns:
            bool: True if all servers started successfully
        """
        logger.info(f"Starting {len(server_keys)} MCP server(s)...")

        success_count = 0
        for server_key in server_keys:
            if self.start_server(server_key):
                success_count += 1

        if success_count == len(server_keys):
            logger.info(f"✓ All {len(server_keys)} servers started successfully")
            return True
        else:
            logger.error(
                f"✗ Only {success_count}/{len(server_keys)} servers started successfully"
            )
            return False

    def stop_all_servers(self) -> None:
        """Stop all running servers."""
        if not self.processes:
            logger.info("No servers are running")
            return

        logger.info("Stopping all servers...")

        for server_key in list(self.processes.keys()):
            self.stop_server(server_key)

    def wait_for_servers(self) -> None:
        """Wait for all servers to finish (blocks until shutdown)."""
        if not self.processes:
            logger.info("No servers are running")
            return

        self.running = True
        logger.info("All servers are running. Press Ctrl+C to stop all servers.")

        try:
            while self.running and self.processes:
                time.sleep(1)

                # Check if any processes have died
                dead_processes = []
                for server_key, process in self.processes.items():
                    if not process.is_alive():
                        dead_processes.append(server_key)

                # Clean up dead processes
                for server_key in dead_processes:
                    config = SERVER_CONFIGS[server_key]
                    logger.error(f"✗ {config.name} has stopped unexpectedly")
                    del self.processes[server_key]

                # Stop if all processes are dead
                if not self.processes:
                    logger.error("All servers have stopped")
                    break

        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
        finally:
            self.stop_all_servers()


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Start MCP servers for load data processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Server Options:
  loads    - LoadSet MCP Server (port 8000)

Examples:
  %(prog)s                           # Start LoadSet server
  %(prog)s --only loads              # Start LoadSet server (explicit)
  %(prog)s --transport stdio         # Use stdio transport
        """,
    )

    # Server selection (mutually exclusive)
    server_group = parser.add_mutually_exclusive_group()
    server_group.add_argument(
        "--all", action="store_true", help="Start all MCP servers (default behavior)"
    )
    server_group.add_argument(
        "--only",
        type=str,
        help="Start only specific servers (currently only: loads)",
    )

    # Transport selection
    parser.add_argument(
        "--transport",
        choices=["http", "stdio"],
        default="http",
        help="Transport type (default: http)",
    )

    # Verbose logging
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    return parser.parse_args()


def validate_server_keys(server_keys: list[str]) -> list[str]:
    """
    Validate and return valid server keys.

    Args:
        server_keys: List of server keys to validate

    Returns:
        List of valid server keys
    """
    valid_keys = []
    invalid_keys = []

    for key in server_keys:
        key = key.strip()
        if key in SERVER_CONFIGS:
            valid_keys.append(key)
        else:
            invalid_keys.append(key)

    if invalid_keys:
        logger.error(f"Invalid server keys: {', '.join(invalid_keys)}")
        logger.info(f"Valid server keys: {', '.join(SERVER_CONFIGS.keys())}")
        sys.exit(1)

    return valid_keys


def main():
    """Main entry point."""
    args = parse_arguments()

    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Determine which servers to start
    if args.only:
        server_keys = args.only.split(",")
        server_keys = validate_server_keys(server_keys)
    else:
        # Default: start all servers
        server_keys = list(SERVER_CONFIGS.keys())

    # Print server information
    logger.info("MCP Server Startup Configuration:")
    logger.info(f"Transport: {args.transport}")
    logger.info(f"Servers to start: {', '.join(server_keys)}")

    for key in server_keys:
        config = SERVER_CONFIGS[key]
        logger.info(
            f"  - {config.name} (port {config.default_port}): {config.description}"
        )

    # Create and start the server manager
    manager = MCPServerManager(transport=args.transport)

    try:
        # Start the servers
        if manager.start_servers(server_keys):
            # Wait for servers to run
            manager.wait_for_servers()
        else:
            logger.error("Failed to start some servers")
            sys.exit(1)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        manager.stop_all_servers()
        sys.exit(1)


if __name__ == "__main__":
    # Support multiprocessing on macOS
    multiprocessing.set_start_method("spawn", force=True)
    main()
