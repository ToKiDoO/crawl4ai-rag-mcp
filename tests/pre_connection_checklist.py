#!/usr/bin/env python
"""
Pre-connection checklist for MCP server.
Validates environment, dependencies, and basic functionality before client connection.
"""

import asyncio
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path


class Colors:
    """Terminal colors for output"""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


class PreConnectionChecklist:
    """Validates MCP server readiness before client connection"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.results = []
        self.has_errors = False
        self.has_warnings = False

    def print_header(self, text: str):
        """Print section header"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")

    def print_result(self, name: str, status: str, message: str = ""):
        """Print test result with color coding"""
        if status == "PASS":
            color = Colors.GREEN
            symbol = "✓"
        elif status == "FAIL":
            color = Colors.RED
            symbol = "✗"
            self.has_errors = True
        else:  # WARN
            color = Colors.YELLOW
            symbol = "!"
            self.has_warnings = True

        print(f"{color}{symbol} {name}{Colors.RESET}", end="")
        if message:
            print(f" - {message}")
        else:
            print()

        self.results.append((name, status, message))

    def check_python_version(self) -> tuple[str, str]:
        """Check if Python version meets requirements"""
        required_version = (3, 12)
        current_version = sys.version_info[:2]

        if current_version >= required_version:
            return "PASS", f"Python {'.'.join(map(str, current_version))}"
        return (
            "FAIL",
            f"Python {'.'.join(map(str, current_version))} < {'.'.join(map(str, required_version))}",
        )

    def check_environment_file(self) -> tuple[str, str]:
        """Check if .env file exists and is configured"""
        env_path = self.project_root / ".env"

        if not env_path.exists():
            return "FAIL", ".env file not found"

        # Check for required variables
        required_vars = ["OPENAI_API_KEY", "VECTOR_DATABASE"]
        missing_vars = []

        with open(env_path) as f:
            env_content = f.read()
            for var in required_vars:
                if (
                    f"{var}=" not in env_content
                    or f"{var}=\n" in env_content
                    or f"{var}= \n" in env_content
                ):
                    missing_vars.append(var)

        if missing_vars:
            return "WARN", f"Missing or empty: {', '.join(missing_vars)}"

        return "PASS", "All required variables present"

    def check_vector_database_config(self) -> tuple[str, str]:
        """Check vector database configuration"""
        from dotenv import load_dotenv

        env_path = self.project_root / ".env"
        load_dotenv(env_path)

        vector_db = os.getenv("VECTOR_DATABASE", "supabase")

        if vector_db == "qdrant":
            qdrant_url = os.getenv("QDRANT_URL")
            if not qdrant_url:
                return "FAIL", "QDRANT_URL not configured"

            # Check if Qdrant is accessible
            try:
                import requests

                response = requests.get(f"{qdrant_url}", timeout=2)
                if response.status_code == 200:
                    return "PASS", f"Qdrant accessible at {qdrant_url}"
                return "WARN", f"Qdrant returned status {response.status_code}"
            except Exception as e:
                return "WARN", f"Cannot reach Qdrant: {e!s}"

        elif vector_db == "supabase":
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_KEY")

            if not supabase_url or not supabase_key:
                return "FAIL", "Supabase credentials not configured"

            return "PASS", "Supabase configured"

        else:
            return "FAIL", f"Unknown vector database: {vector_db}"

    def check_dependencies(self) -> tuple[str, str]:
        """Check if all required dependencies are installed"""
        try:
            # Check critical imports
            critical_modules = [
                ("mcp.server.fastmcp", "FastMCP"),
                ("crawl4ai", "AsyncWebCrawler"),
                ("sentence_transformers", "CrossEncoder"),
                ("qdrant_client", "QdrantClient")
                if os.getenv("VECTOR_DATABASE") == "qdrant"
                else None,
                ("supabase", "create_client")
                if os.getenv("VECTOR_DATABASE") == "supabase"
                else None,
            ]

            failed_imports = []
            for module_info in critical_modules:
                if module_info is None:
                    continue

                module_name, attr_name = module_info
                try:
                    module = importlib.import_module(module_name)
                    if attr_name and not hasattr(module, attr_name):
                        failed_imports.append(f"{module_name}.{attr_name}")
                except ImportError:
                    failed_imports.append(module_name)

            if failed_imports:
                return "FAIL", f"Missing: {', '.join(failed_imports)}"

            return "PASS", "All critical dependencies available"

        except Exception as e:
            return "FAIL", f"Error checking dependencies: {e!s}"

    def check_playwright_browsers(self) -> tuple[str, str]:
        """Check if Playwright browsers are installed"""
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as p:
                # Check if chromium is available
                try:
                    browser = p.chromium.launch(headless=True)
                    browser.close()
                    return "PASS", "Chromium browser available"
                except Exception:
                    return (
                        "WARN",
                        "Chromium not installed - run: uv run playwright install chromium",
                    )

        except ImportError:
            return "WARN", "Playwright not available"
        except Exception as e:
            return "WARN", f"Cannot check browsers: {e!s}"

    async def check_mcp_server_startup(self) -> tuple[str, str]:
        """Check if MCP server can start without errors"""
        try:
            # Import and create MCP server
            from crawl4ai_mcp import mcp

            # Check if server initialized
            if mcp is None:
                return "FAIL", "MCP server failed to initialize"

            # Check tool registration
            if not hasattr(mcp, "_tool_manager"):
                return "FAIL", "No tool manager found"

            # Try to list tools
            try:
                tools = mcp.list_tools()
                tool_count = len(tools)
                return "PASS", f"{tool_count} tools registered"
            except:
                tool_count = 0
                return (
                    "PASS",
                    f"{tool_count} tools registered (list_tools not available)",
                )

        except Exception as e:
            return "FAIL", f"Server startup error: {e!s}"

    async def check_database_initialization(self) -> tuple[str, str]:
        """Check if database can be initialized"""
        try:
            from database.factory import create_and_initialize_database

            # Try to create and initialize database
            db = await create_and_initialize_database()

            if db is None:
                return "FAIL", "Database initialization failed"

            # Check adapter type
            adapter_type = type(db).__name__
            return "PASS", f"{adapter_type} initialized successfully"

        except Exception as e:
            return "FAIL", f"Database error: {e!s}"

    def check_docker_compose(self) -> tuple[str, str]:
        """Check if Docker Compose services are running"""
        try:
            # Check for docker-compose.test.yml
            compose_file = self.project_root / "docker-compose.test.yml"
            if not compose_file.exists():
                return "WARN", "docker-compose.test.yml not found"

            # Check if services are running
            result = subprocess.run(
                [
                    "docker",
                    "compose",
                    "-f",
                    str(compose_file),
                    "ps",
                    "--format",
                    "json",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            if result.returncode != 0:
                return "WARN", "Docker Compose not running"

            # Parse service status
            services = json.loads(result.stdout) if result.stdout else []
            running_services = [s for s in services if s.get("State") == "running"]

            if not running_services:
                return "WARN", "No services running"

            service_names = [s.get("Service", "unknown") for s in running_services]
            return "PASS", f"Running: {', '.join(service_names)}"

        except Exception as e:
            return "WARN", f"Cannot check Docker: {e!s}"

    async def run_all_checks(self):
        """Run all pre-connection checks"""
        self.print_header("MCP Server Pre-Connection Checklist")

        # Environment checks
        print(f"\n{Colors.BOLD}Environment Checks:{Colors.RESET}")
        status, msg = self.check_python_version()
        self.print_result("Python Version", status, msg)

        status, msg = self.check_environment_file()
        self.print_result("Environment File", status, msg)

        status, msg = self.check_dependencies()
        self.print_result("Dependencies", status, msg)

        status, msg = self.check_playwright_browsers()
        self.print_result("Playwright Browsers", status, msg)

        # Database checks
        print(f"\n{Colors.BOLD}Database Checks:{Colors.RESET}")
        status, msg = self.check_vector_database_config()
        self.print_result("Vector Database Config", status, msg)

        status, msg = await self.check_database_initialization()
        self.print_result("Database Initialization", status, msg)

        # MCP Server checks
        print(f"\n{Colors.BOLD}MCP Server Checks:{Colors.RESET}")
        status, msg = await self.check_mcp_server_startup()
        self.print_result("MCP Server Startup", status, msg)

        # Docker checks
        print(f"\n{Colors.BOLD}Infrastructure Checks:{Colors.RESET}")
        status, msg = self.check_docker_compose()
        self.print_result("Docker Compose", status, msg)

        # Summary
        self.print_summary()

    def print_summary(self):
        """Print summary of all checks"""
        self.print_header("Summary")

        total = len(self.results)
        passed = sum(1 for _, status, _ in self.results if status == "PASS")
        failed = sum(1 for _, status, _ in self.results if status == "FAIL")
        warnings = sum(1 for _, status, _ in self.results if status == "WARN")

        print(f"\nTotal Checks: {total}")
        print(f"{Colors.GREEN}Passed: {passed}{Colors.RESET}")
        print(f"{Colors.YELLOW}Warnings: {warnings}{Colors.RESET}")
        print(f"{Colors.RED}Failed: {failed}{Colors.RESET}")

        if self.has_errors:
            print(
                f"\n{Colors.RED}{Colors.BOLD}❌ FAILED: Fix errors before connecting MCP client{Colors.RESET}",
            )
            sys.exit(1)
        elif self.has_warnings:
            print(
                f"\n{Colors.YELLOW}{Colors.BOLD}⚠️  WARNING: Some checks failed but not critical{Colors.RESET}",
            )
            print("You can proceed but may encounter issues")
        else:
            print(
                f"\n{Colors.GREEN}{Colors.BOLD}✅ READY: MCP server is ready for client connection{Colors.RESET}",
            )

        # Print next steps
        print(f"\n{Colors.BOLD}Next Steps:{Colors.RESET}")
        if self.has_errors:
            print("1. Fix the failed checks above")
            print("2. Run this checklist again")
        else:
            print("1. Configure Claude Desktop with the MCP server")
            print("2. Run: ./scripts/validate_mcp_server.sh")
            print("3. Connect Claude Desktop and test")


async def main():
    """Run the pre-connection checklist"""
    checklist = PreConnectionChecklist()
    await checklist.run_all_checks()


if __name__ == "__main__":
    asyncio.run(main())
