#!/usr/bin/env python3
"""
Unified Test Runner for QuickStream
Runs ALL test suites in one command with detailed output
"""

import sys
import subprocess
import time
from pathlib import Path

# Color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BOLD}{BLUE}{'=' * 80}{RESET}")
    print(f"{BOLD}{BLUE}  {text}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 80}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✓ {text}{RESET}")

def print_error(text):
    print(f"{RED}✗ {text}{RESET}")

def run_command(description, command, timeout=60):
    """Run a command and return success status."""
    print(f"\n{BOLD}Running: {description}{RESET}")
    print(f"Command: {' '.join(command)}")
    print("-" * 80)

    start_time = time.time()
    try:
        result = subprocess.run(
            command,
            timeout=timeout,
            capture_output=False  # Show output in real-time
        )
        elapsed = time.time() - start_time

        if result.returncode == 0:
            print_success(f"{description} PASSED ({elapsed:.2f}s)")
            return True
        else:
            print_error(f"{description} FAILED with exit code {result.returncode} ({elapsed:.2f}s)")
            return False

    except subprocess.TimeoutExpired:
        print_error(f"{description} TIMEOUT after {timeout}s")
        return False
    except Exception as e:
        print_error(f"{description} ERROR: {e}")
        return False

def main():
    print_header("QuickStream Unified Test Suite Runner")

    # Change to script directory
    script_dir = Path(__file__).parent
    import os
    os.chdir(script_dir)

    results = {}

    # Test 1: Run pytest on test_server.py
    results['test_server'] = run_command(
        "Core Server Tests (test_server.py)",
        ['python3', '-m', 'pytest', 'test_server.py', '-v', '--tb=short']
    )

    # Test 2: Run pytest on test_ffmpeg_capture.py
    results['test_ffmpeg_capture'] = run_command(
        "FFmpeg Capture Tests (test_ffmpeg_capture.py)",
        ['python3', '-m', 'pytest', 'test_ffmpeg_capture.py', '-v', '--tb=short']
    )

    # Test 3: Run pytest on test_server_comprehensive.py if it exists
    if Path('test_server_comprehensive.py').exists():
        results['test_server_comprehensive'] = run_command(
            "Comprehensive Server Tests (test_server_comprehensive.py)",
            ['python3', '-m', 'pytest', 'test_server_comprehensive.py', '-v', '--tb=short']
        )

    # Test 4: Run ALL tests with coverage
    results['all_tests_with_coverage'] = run_command(
        "All Tests with Coverage Report",
        ['python3', '-m', 'pytest', 'test_server.py', 'test_ffmpeg_capture.py',
         '--cov=server', '--cov-report=term', '--cov-report=html', '-v'],
        timeout=120
    )

    # Summary
    print_header("TEST RESULTS SUMMARY")

    total_tests = len(results)
    passed_tests = sum(1 for success in results.values() if success)
    failed_tests = total_tests - passed_tests

    for test_name, success in results.items():
        if success:
            print_success(f"{test_name}")
        else:
            print_error(f"{test_name}")

    print(f"\n{BOLD}Overall Results:{RESET}")
    print(f"  Total test suites: {total_tests}")
    print(f"  Passed: {GREEN}{passed_tests}{RESET}")
    print(f"  Failed: {RED}{failed_tests}{RESET}")

    if failed_tests == 0:
        print(f"\n{GREEN}{BOLD}ALL TESTS PASSED!{RESET}")
        return 0
    else:
        print(f"\n{RED}{BOLD}SOME TESTS FAILED!{RESET}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
