#!/usr/bin/env python3
"""
L3 Decision Matrix - Complete Test Suite
"""

from .arbiter import run_all_tests as run_arbiter_tests
from .actuation_dispatcher import run_all_tests as run_actuation_tests
from .mute_slm import run_all_tests as run_mute_slm_tests


def run_all_l3_tests():
    print("\n" + "="*70)
    print(" " * 15 + "L3 DECISION MATRIX - COMPLETE TEST SUITE")
    print("="*70)
    total_passed = 0
    total_tests = 0
    
    print("\n[1/3] Running Arbitration Logic Tests...")
    print("-" * 70)
    if run_arbiter_tests():
        total_passed += 5
    total_tests += 5
    
    print("\n[2/3] Running Actuation Dispatcher Tests...")
    print("-" * 70)
    if run_actuation_tests():
        total_passed += 5
    total_tests += 5
    
    print("\n[3/3] Running MuteSLM Logic Tests...")
    print("-" * 70)
    if run_mute_slm_tests():
        total_passed += 5
    total_tests += 5
    
    print("\n" + "="*70)
    print(" " * 20 + "TEST SUMMARY")
    print("="*70)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_tests - total_passed}")
    success_rate = total_passed / total_tests * 100 if total_tests > 0 else 0
    print(f"Success Rate: {success_rate:.1f}%")
    print("="*70)
    
    if total_tests - total_passed == 0:
        print("\nALL TESTS PASSED! L3 Decision Matrix is ready for deployment!")
        return True
    else:
        print("\nSome tests failed. Please review the output above.")
        return False


def run_demo():
    from .main import demo_basic_scenario, demo_cooldown_scenario
    print("\n" + "="*70)
    print(" " * 20 + "DEMONSTRATION")
    print("="*70)
    demo_basic_scenario()
    demo_cooldown_scenario()


if __name__ == "__main__":
    import sys
    import argparse
    parser = argparse.ArgumentParser(description="L3 Decision Matrix Test Suite")
    parser.add_argument("--test", action="store_true", help="Run all test cases")
    parser.add_argument("--demo", action="store_true", help="Run demonstration scenarios")
    parser.add_argument("--all", action="store_true", help="Run tests and demo")
    args = parser.parse_args()
    
    if args.all or (not args.test and not args.demo):
        success = run_all_l3_tests()
        run_demo()
        sys.exit(0 if success else 1)
    elif args.test:
        success = run_all_l3_tests()
        sys.exit(0 if success else 1)
    elif args.demo:
        run_demo()
        sys.exit(0)
