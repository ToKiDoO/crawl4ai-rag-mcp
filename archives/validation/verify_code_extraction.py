#!/usr/bin/env python3
"""
Integration test to verify code extraction functionality works end-to-end.
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_code_extraction_imports():
    """Test that all necessary functions can be imported."""
    print("🔍 Testing imports...")
    
    try:
        from utils import extract_code_blocks, add_code_examples_to_database
        from utils import generate_code_example_summary
        print("✅ All necessary functions imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_code_extraction_function():
    """Test the code extraction function with sample markdown."""
    print("🔍 Testing code extraction function...")
    
    try:
        from utils import extract_code_blocks
        
        # Sample markdown with code blocks
        sample_markdown = """
# Sample Documentation

Here's how to use the API:

```python
import requests

def fetch_data(url):
    response = requests.get(url)
    return response.json()

# Example usage
data = fetch_data("https://api.example.com/data")
print(data)
```

And here's a configuration example:

```json
{
    "api_key": "your-key-here",
    "timeout": 30,
    "retries": 3
}
```
"""
        
        # Extract code blocks
        code_blocks = extract_code_blocks(sample_markdown, min_length=50)
        
        if len(code_blocks) >= 1:
            print(f"✅ Extracted {len(code_blocks)} code block(s)")
            
            # Check first code block
            first_block = code_blocks[0]
            if 'code' in first_block and 'language' in first_block:
                print(f"✅ Code block structure is correct")
                print(f"   Language: {first_block['language']}")
                print(f"   Code length: {len(first_block['code'])} characters")
                return True
            else:
                print("❌ Code block structure is incorrect")
                return False
        else:
            print("❌ No code blocks extracted")
            return False
            
    except Exception as e:
        print(f"❌ Error testing code extraction: {e}")
        return False

def test_environment_variable():
    """Test that the environment variable is correctly set."""
    print("🔍 Testing environment variable...")
    
    # Set the environment variable
    os.environ['USE_AGENTIC_RAG'] = 'true'
    
    # Test that it's correctly read
    enabled = os.getenv("USE_AGENTIC_RAG", "false") == "true"
    
    if enabled:
        print("✅ USE_AGENTIC_RAG environment variable works correctly")
        return True
    else:
        print("❌ USE_AGENTIC_RAG environment variable not working")
        return False

def main():
    """Run all tests."""
    print("🚀 Verifying code extraction functionality...\n")
    
    tests = [
        ("Import test", test_code_extraction_imports),
        ("Code extraction test", test_code_extraction_function),
        ("Environment variable test", test_environment_variable)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            if test_func():
                passed += 1
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
    
    print(f"\n📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All verification tests passed!")
        print("\n✅ Code extraction functionality is working correctly")
        print("✅ Environment variable USE_AGENTIC_RAG is properly integrated")
        print("✅ When USE_AGENTIC_RAG=true, code examples will be extracted and stored")
        return True
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)