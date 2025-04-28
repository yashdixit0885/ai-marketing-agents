#!/usr/bin/env python3
"""
Test Runner

A script to run all tests and verify that the content pipeline is working correctly.
"""

import os
import sys
import subprocess
import argparse
import time
from typing import List, Tuple

def run_command(command: List[str]) -> Tuple[int, str, str]:
    """Run a shell command and return the exit code, stdout, and stderr."""
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True
    )
    stdout, stderr = process.communicate()
    return process.returncode, stdout, stderr

def run_pytest(test_path: str, verbose: bool = False) -> bool:
    """Run pytest on the specified path."""
    command = ["pytest", test_path]
    
    if verbose:
        command.append("-v")
    
    print(f"Running: {' '.join(command)}")
    print("-" * 80)
    
    start_time = time.time()
    returncode, stdout, stderr = run_command(command)
    elapsed_time = time.time() - start_time
    
    print(stdout)
    if stderr:
        print(stderr)
    
    print(f"Completed in {elapsed_time:.2f} seconds with return code {returncode}")
    print("=" * 80)
    
    return returncode == 0

def run_all_tests(verbose: bool = False) -> bool:
    """Run all tests."""
    test_groups = [
        ("Unit Tests: Research Agent", "tests/test_agents/test_research_agent.py"),
        ("Unit Tests: Content Agent", "tests/test_agents/test_content_agent.py"),
        ("Unit Tests: Visual Agent", "tests/test_agents/test_visual_agent.py"),
        ("Unit Tests: Atomization Agent", "tests/test_agents/test_atomization_agent.py"),
        ("Unit Tests: Distribution Agent", "tests/test_agents/test_distribution_agent.py"),
        ("Integration Tests: Content Pipeline", "tests/test_integration/test_content_pipeline.py")
    ]
    
    all_passed = True
    
    for name, path in test_groups:
        print(f"\n📋 {name}")
        passed = run_pytest(path, verbose)
        
        if passed:
            print(f"✅ {name} PASSED")
        else:
            print(f"❌ {name} FAILED")
            all_passed = False
    
    return all_passed

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Run AI Content Automation tests")
    
    parser.add_argument("--unit", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration", action="store_true", help="Run only integration tests")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose output")
    
    return parser.parse_args()

def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Add project root to Python path
    project_root = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, project_root)
    
    start_time = time.time()
    
    if args.unit:
        print("🧪 Running unit tests...")
        passed = run_pytest("tests/test_agents/", args.verbose)
    elif args.integration:
        print("🧩 Running integration tests...")
        passed = run_pytest("tests/test_integration/", args.verbose)
    else:
        print("🧪 Running all tests...")
        passed = run_all_tests(args.verbose)
    
    elapsed_time = time.time() - start_time
    
    print(f"\n⏱️ Total test time: {elapsed_time:.2f} seconds")
    
    if passed:
        print("\n✅ All tests PASSED!")
        return 0
    else:
        print("\n❌ Some tests FAILED!")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)