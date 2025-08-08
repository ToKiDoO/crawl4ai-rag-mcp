#!/usr/bin/env python3
"""
Focused Parameter Validation Test
Tests ONLY the parameter consistency fixes without importing problematic modules.

Test DateTime: Thu Aug  7 17:35:50 BST 2025
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_protocol_consistency():
    """Test that all adapters have consistent method signatures"""
    print("=" * 60)
    print("TEST: Protocol Consistency")
    print("=" * 60)
    
    try:
        # Import the base protocol
        from database.base import VectorDatabase
        
        # Get the method signature from protocol
        search_method = getattr(VectorDatabase, 'search_code_examples')
        
        # Check protocol signature
        import inspect
        protocol_sig = inspect.signature(search_method)
        protocol_params = list(protocol_sig.parameters.keys())
        
        print(f"Protocol parameters: {protocol_params}")
        
        # Check if filter_metadata is in the protocol
        if 'filter_metadata' in protocol_params:
            print("✅ PASS: Protocol uses filter_metadata parameter")
            return True
        else:
            print(f"❌ FAIL: Protocol uses wrong parameter name: {protocol_params}")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Error checking protocol: {e}")
        return False

def test_qdrant_adapter_signature():
    """Test QdrantAdapter method signature directly"""
    print("=" * 60)
    print("TEST: QdrantAdapter Signature")
    print("=" * 60)
    
    try:
        from database.qdrant_adapter import QdrantAdapter
        
        # Get the method signature
        import inspect
        search_method = getattr(QdrantAdapter, 'search_code_examples')
        sig = inspect.signature(search_method)
        params = list(sig.parameters.keys())
        
        print(f"QdrantAdapter parameters: {params}")
        
        # Check if filter_metadata is in the signature
        if 'filter_metadata' in params:
            print("✅ PASS: QdrantAdapter uses filter_metadata parameter")
            return True
        else:
            print(f"❌ FAIL: QdrantAdapter uses wrong parameter name: {params}")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Error checking QdrantAdapter: {e}")
        return False

def test_supabase_adapter_signature():
    """Test SupabaseAdapter method signature directly"""
    print("=" * 60)
    print("TEST: SupabaseAdapter Signature")
    print("=" * 60)
    
    try:
        from database.supabase_adapter import SupabaseAdapter
        
        # Get the method signature
        import inspect
        search_method = getattr(SupabaseAdapter, 'search_code_examples')
        sig = inspect.signature(search_method)
        params = list(sig.parameters.keys())
        
        print(f"SupabaseAdapter parameters: {params}")
        
        # Check if filter_metadata is in the signature
        if 'filter_metadata' in params:
            print("✅ PASS: SupabaseAdapter uses filter_metadata parameter")
            return True
        else:
            print(f"❌ FAIL: SupabaseAdapter uses wrong parameter name: {params}")
            return False
            
    except Exception as e:
        print(f"❌ FAIL: Error checking SupabaseAdapter: {e}")
        return False

def run_focused_validation():
    """Run focused parameter validation tests"""
    print("FOCUSED PARAMETER VALIDATION TEST")
    print("Test DateTime: Thu Aug  7 17:35:50 BST 2025")
    print("Environment: Linux 5.15.167.4-microsoft-standard-WSL2")
    print("Branch: fix/ci-failures-qdrant-tests")
    print()
    
    tests = [
        ("Protocol Consistency", test_protocol_consistency),
        ("QdrantAdapter Signature", test_qdrant_adapter_signature),
        ("SupabaseAdapter Signature", test_supabase_adapter_signature),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            print()
        except Exception as e:
            print(f"❌ FAIL: {test_name} - Exception: {e}")
            results.append((test_name, False))
            print()
    
    # Summary
    print("=" * 60)
    print("FOCUSED VALIDATION SUMMARY")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
        else:
            failed += 1
    
    print(f"\nTotal Tests: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    overall_result = "✅ PASS" if failed == 0 else "❌ FAIL"
    print(f"\nOVERALL RESULT: {overall_result}")
    
    return failed == 0

if __name__ == "__main__":
    success = run_focused_validation()
    sys.exit(0 if success else 1)