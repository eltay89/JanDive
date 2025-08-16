#!/usr/bin/env python3
"""
Verification script to check that all components are working correctly
"""

import os
import logging
from tools.search_tool import SearchTool
from tools.calculator_tool import CalculatorTool

def verify_installation(verbose=False):
    if verbose:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        print("Verifying JanDive installation (verbose mode)...")

    # Check 1: Model file
    model_path = os.getenv('JANDIVE_MODEL_PATH', "models/janhq_Jan-v1-4B-Q4_K_M.gguf")
    if not os.path.exists(model_path):
        print("[FAIL] Model file not found.")
        print(f"  Please run 'python download_model.py' or ensure the model is at {model_path}")
        return False
    if verbose: print("[PASS] Model file found")

    # Test 2: Search tool functionality
    try:
        search_tool = SearchTool()
        results = search_tool.execute("test query", max_results=1)
        if not (isinstance(results, list) and len(results) > 0 and "title" in results[0]):
            print("[FAIL] Search tool basic functionality check failed.")
            if verbose: print(f"  Unexpected result: {results}")
            return False
        if verbose: print("[PASS] Search tool is functional")
    except Exception as e:
        print(f"[FAIL] Search tool failed with an exception: {e}")
        return False

    # Test 3: Calculator tool functionality
    try:
        calc_tool = CalculatorTool()
        if not (calc_tool.execute("2+2").get("result") == 4):
            print("[FAIL] Calculator tool basic calculation failed.")
            return False
        if not ("error" in calc_tool.execute("__import__('os').system('ls')")):
            print("[FAIL] Calculator tool security check failed.")
            return False
        if verbose: print("[PASS] Calculator tool is functional and secure")
    except Exception as e:
        print(f"[FAIL] Calculator tool failed with an exception: {e}")
        return False

    # Test 4: Search tool security
    try:
        search_tool = SearchTool()
        if search_tool._is_safe_url("file:///etc/passwd"):
            print("[FAIL] Search tool URL security check failed.")
            return False
        if verbose: print("[PASS] Search tool URL security is working")
    except Exception as e:
        print(f"[FAIL] Search tool security test failed with an exception: {e}")
        return False

    if not verbose:
        print("Verifying JanDive installation... OK")

    return True

if __name__ == "__main__":
    verify_installation()
