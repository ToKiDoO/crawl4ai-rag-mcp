#!/usr/bin/env python3
"""
Qdrant Integration Test Runner
Runs comprehensive Qdrant tests with environment detection and proper setup.
"""

import argparse
import os
import subprocess
import sys
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from test_qdrant_config import QdrantTestConfig


def run_command(cmd: str, shell: bool = True) -> tuple:
    """Run a command and return the result"""
    try:
        result = subprocess.run(
            cmd,
            check=False,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out after 120 seconds"
    except Exception as e:
        return -1, "", str(e)


def check_dependencies():
    """Check if required dependencies are available"""
    print("Checking dependencies...")

    # Check Python packages
    required_packages = ["pytest", "pytest-asyncio", "qdrant-client", "requests"]

    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            print(f"✓ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"✗ {package}")

    if missing_packages:
        print(f"\nMissing packages: {', '.join(missing_packages)}")
        print("Install with: pip install " + " ".join(missing_packages))
        return False

    return True


def setup_qdrant_docker():
    """Setup Qdrant using Docker if not already running"""
    print("Setting up Qdrant with Docker...")

    # Check if Qdrant is already running
    config = QdrantTestConfig()
    if config.is_healthy:
        print("✓ Qdrant is already running")
        return True

    # Try to start Qdrant container
    print("Starting Qdrant container...")

    cmd = "docker run -d --name qdrant-test -p 6333:6333 qdrant/qdrant"
    returncode, stdout, stderr = run_command(cmd)

    if returncode != 0:
        # Container might already exist, try to start it
        print("Container might exist, trying to start...")
        start_cmd = "docker start qdrant-test"
        returncode, stdout, stderr = run_command(start_cmd)

        if returncode != 0:
            print(f"Failed to start Qdrant: {stderr}")
            return False

    # Wait for Qdrant to be ready
    print("Waiting for Qdrant to be ready...")
    for i in range(30):
        config = QdrantTestConfig()
        if config.is_healthy:
            print("✓ Qdrant is ready")
            return True
        time.sleep(1)
        print(f"Waiting... ({i + 1}/30)")

    print("✗ Qdrant failed to start within 30 seconds")
    return False


def cleanup_qdrant_docker():
    """Cleanup Qdrant Docker container"""
    print("Cleaning up Qdrant container...")

    # Stop and remove container
    commands = ["docker stop qdrant-test", "docker rm qdrant-test"]

    for cmd in commands:
        returncode, stdout, stderr = run_command(cmd)
        if returncode == 0:
            print(f"✓ {cmd}")
        else:
            print(f"- {cmd} (already stopped/removed)")


def run_test_suite(test_files: list, verbose: bool = False, markers: str = None):
    """Run the specified test files"""
    print("\nRunning Qdrant test suite...")
    print(f"Test files: {test_files}")

    # Build pytest command
    cmd_parts = ["python", "-m", "pytest"]

    if verbose:
        cmd_parts.append("-v")

    if markers:
        cmd_parts.extend(["-m", markers])

    # Add asyncio mode
    cmd_parts.extend(["--asyncio-mode=auto"])

    # Add test files
    cmd_parts.extend(test_files)

    cmd = " ".join(cmd_parts)
    print(f"Command: {cmd}")

    # Run tests
    print("\n" + "=" * 60)
    print("RUNNING TESTS")
    print("=" * 60)

    returncode, stdout, stderr = run_command(cmd)

    print(stdout)
    if stderr:
        print("STDERR:", stderr)

    print("\n" + "=" * 60)
    print(f"TESTS COMPLETED (exit code: {returncode})")
    print("=" * 60)

    return returncode == 0


def main():
    """Main test runner function"""
    parser = argparse.ArgumentParser(description="Run Qdrant integration tests")
    parser.add_argument(
        "--env",
        choices=["auto", "docker", "localhost"],
        default="auto",
        help="Environment to run tests in",
    )
    parser.add_argument(
        "--setup-docker",
        action="store_true",
        help="Setup Qdrant using Docker before running tests",
    )
    parser.add_argument(
        "--cleanup-docker",
        action="store_true",
        help="Cleanup Qdrant Docker container after tests",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Run tests in verbose mode",
    )
    parser.add_argument(
        "--markers",
        "-m",
        type=str,
        help="Run tests with specific markers (e.g., 'qdrant and not docker_env')",
    )
    parser.add_argument(
        "--test-files",
        nargs="*",
        default=[
            "test_qdrant_integration_comprehensive.py",
            "test_qdrant_error_handling.py",
        ],
        help="Test files to run",
    )
    parser.add_argument(
        "--check-deps",
        action="store_true",
        help="Only check dependencies and exit",
    )

    args = parser.parse_args()

    print("QDRANT INTEGRATION TEST RUNNER")
    print("=" * 60)

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    if args.check_deps:
        print("✓ All dependencies available")
        sys.exit(0)

    # Detect environment
    config = QdrantTestConfig()
    print(f"\nEnvironment detected: {config.environment}")
    print(f"Qdrant URL: {config.qdrant_url}")
    print(f"Qdrant healthy: {config.is_healthy}")

    # Setup Docker if requested
    if args.setup_docker:
        if not setup_qdrant_docker():
            print("Failed to setup Qdrant with Docker")
            sys.exit(1)

    # Check if Qdrant is available
    if not config.is_healthy:
        print("\n⚠️ Qdrant is not available!")
        print(config.get_skip_reason())

        if not args.setup_docker:
            print("\nTry running with --setup-docker to automatically start Qdrant")

        sys.exit(1)

    # Setup environment variables
    config.setup_environment_variables()

    try:
        # Run tests
        success = run_test_suite(
            test_files=args.test_files,
            verbose=args.verbose,
            markers=args.markers,
        )

        if success:
            print("\n✅ All tests passed!")
            exit_code = 0
        else:
            print("\n❌ Some tests failed!")
            exit_code = 1

    except KeyboardInterrupt:
        print("\n\nTest run interrupted by user")
        exit_code = 1

    except Exception as e:
        print(f"\n\nTest run failed with error: {e}")
        exit_code = 1

    finally:
        # Cleanup Docker if requested
        if args.cleanup_docker:
            cleanup_qdrant_docker()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
